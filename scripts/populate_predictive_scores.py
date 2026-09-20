#!/usr/bin/env python3
"""Batch Prediction Materialization Script for SLA Risk & Cycle Time Models.

Loads a fitted ML model artifact, queries application features from PostgreSQL,
validates prediction outputs, and populates application_predictions via transactional batch UPSERT.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

import pandas as pd

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database import check_database_connection, get_cursor
from src.ml.feature_engineering import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    REAL_SOURCE_FEATURES,
)
from src.ml.sla_predictor import SLARiskPredictor


@dataclass
class PredictionRecord:
    """Validated prediction payload for database insertion."""

    application_id: str
    model_version: str
    model_type: str
    risk_class: int
    risk_probability: float
    predicted_processing_days: float

    def validate(self) -> None:
        """Validate record fields against database schema check constraints."""
        if not isinstance(self.application_id, str) or not self.application_id.strip():
            raise ValueError(f"Invalid application_id: {self.application_id!r}")

        if not isinstance(self.model_version, str) or not self.model_version.strip():
            raise ValueError("model_version cannot be empty or missing.")

        if self.risk_class not in (0, 1):
            raise ValueError(f"risk_class must be 0 or 1, got {self.risk_class}")

        if not (0.0 <= self.risk_probability <= 1.0):
            raise ValueError(f"risk_probability must be between 0.0 and 1.0, got {self.risk_probability}")

        if self.predicted_processing_days < 0.0:
            raise ValueError(f"predicted_processing_days must be nonnegative, got {self.predicted_processing_days}")


def fetch_application_features(limit: int | None = None) -> pd.DataFrame:
    """Fetch at-start features for applications from database.

    Args:
        limit: Optional integer limit for subset fetching.

    Returns:
        DataFrame containing application_id and feature columns.
    """
    limit_clause = f"LIMIT {limit}" if limit and limit > 0 else ""
    query = f"""
        SELECT
            m.application_id,
            m.application_type,
            m.loan_goal,
            COALESCE(m.requested_amount, 0.0) AS requested_amount,
            m.first_event_time,
            s.document_type,
            s.page_count,
            s.branch,
            s.operator_team,
            s.priority,
            s.sla_target_hours,
            s.region,
            s.channel,
            s.quality_score
        FROM view_application_metrics m
        LEFT JOIN synthetic_extensions s ON m.application_id = s.application_id
        ORDER BY m.application_id
        {limit_clause};
    """
    with get_cursor() as cur:
        cur.execute(query)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()

    if not rows:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(rows, columns=columns)

    # Derived submission time components
    first_dt = pd.to_datetime(df["first_event_time"], utc=True)
    df["submission_hour"] = first_dt.dt.hour
    df["submission_day_of_week"] = first_dt.dt.dayofweek
    df["submission_month"] = first_dt.dt.month
    df["is_weekend"] = (first_dt.dt.dayofweek >= 5).astype(int)

    # Data type coercions
    df["requested_amount"] = df["requested_amount"].astype(float)
    df["page_count"] = df["page_count"].fillna(1).astype(int)
    df["quality_score"] = df["quality_score"].fillna(85.0).astype(float)
    df["sla_target_hours"] = df["sla_target_hours"].fillna(48).astype(int)

    return df


def generate_validated_predictions(
    df: pd.DataFrame,
    predictor: SLARiskPredictor,
    model_version: str,
) -> tuple[list[PredictionRecord], list[dict[str, Any]]]:
    """Execute model inference over feature DataFrame and produce validated PredictionRecords.

    Args:
        df: Input DataFrame containing features.
        predictor: Loaded SLARiskPredictor instance.
        model_version: Explicit model version string.

    Returns:
        Tuple of (valid_records, skipped_records).
    """
    if not isinstance(model_version, str) or not model_version.strip():
        raise ValueError("model_version is required and cannot be empty.")

    if df.empty:
        return [], []

    seen_ids: set[str] = set()
    valid_records: list[PredictionRecord] = []
    skipped_records: list[dict[str, Any]] = []

    feature_subset = getattr(predictor, "feature_subset", "full")
    if feature_subset == "real":
        required_cols = REAL_SOURCE_FEATURES
    else:
        required_cols = NUMERIC_FEATURES + CATEGORICAL_FEATURES

    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Feature DataFrame missing required columns: {missing_cols}")

    features_df = df[required_cols].copy()

    risk_classes = predictor.predict_risk(features_df)
    risk_probas = predictor.predict_risk_proba(features_df)
    cycle_times = predictor.predict_cycle_time(features_df)

    model_type = getattr(predictor, "model_type", "HistGradientBoosting")

    for idx, row in df.reset_index(drop=True).iterrows():
        app_id = str(row["application_id"]).strip()

        if app_id in seen_ids:
            skipped_records.append({"application_id": app_id, "reason": "Duplicate application ID in input batch"})
            continue
        seen_ids.add(app_id)

        try:
            r_cls = int(risk_classes[idx])
            r_prob = round(float(risk_probas[idx]), 4)
            p_days = round(float(cycle_times[idx]), 2)

            record = PredictionRecord(
                application_id=app_id,
                model_version=model_version,
                model_type=model_type,
                risk_class=r_cls,
                risk_probability=r_prob,
                predicted_processing_days=p_days,
            )
            record.validate()
            valid_records.append(record)
        except Exception as err:
            skipped_records.append({"application_id": app_id, "reason": str(err)})

    return valid_records, skipped_records


def populate_predictive_scores(
    model_version: str,
    model_path: str | Path = Path("models/sla_predictor.joblib"),
    batch_size: int = 1000,
    limit: int | None = None,
    dry_run: bool = False,
) -> int:
    """Load trained model, run batch inference, and persist predictions into PostgreSQL.

    Args:
        model_version: Explicit version string (REQUIRED).
        model_path: Path to serialized model joblib artifact.
        batch_size: Transactional batch size for SQL UPSERTs.
        limit: Optional integer limit on applications scored.
        dry_run: If True, run prediction & validation without database writes.

    Returns:
        0 on success, 1 on error.
    """
    if not isinstance(model_version, str) or not model_version.strip():
        print("Error: --model-version argument is required and cannot be empty.", file=sys.stderr)
        return 1

    model_file = Path(model_path)
    if not model_file.exists():
        print(f"Error: Model artifact not found at {model_file}", file=sys.stderr)
        return 1

    if not check_database_connection():
        print("Error: Could not connect to PostgreSQL database.", file=sys.stderr)
        return 1

    print(f"Loading model artifact from {model_file}...")
    predictor = SLARiskPredictor.load(model_file)

    print("Fetching application features from PostgreSQL...")
    df = fetch_application_features(limit=limit)
    total_apps = len(df)
    print(f"Fetched {total_apps:,} application feature records.")

    print(f"Generating predictions (model_version={model_version!r})...")
    valid_records, skipped_records = generate_validated_predictions(
        df=df,
        predictor=predictor,
        model_version=model_version,
    )

    print(f"Generated {len(valid_records):,} valid predictions. Skipped {len(skipped_records):,} invalid/duplicate records.")

    if dry_run:
        print("\n[DRY RUN SUMMARY]")
        print(f"  Model Artifact: {model_file}")
        print(f"  Model Version: {model_version}")
        print(f"  Applications Considered: {total_apps:,}")
        print(f"  Valid Predictions: {len(valid_records):,}")
        print(f"  Records Skipped: {len(skipped_records):,}")
        if valid_records:
            sample = valid_records[0]
            print(f"  Sample Prediction Payload:")
            print(f"    Application ID: {sample.application_id}")
            print(f"    Risk Class: {sample.risk_class}")
            print(f"    Risk Probability: {sample.risk_probability}")
            print(f"    Predicted Days: {sample.predicted_processing_days}")
        print("\nDry run completed cleanly. Zero database rows modified.")
        return 0

    upsert_query = """
    INSERT INTO application_predictions (
        application_id, model_version, model_type, risk_class, risk_probability,
        predicted_processing_days, scored_at, created_at, updated_at
    ) VALUES (
        %s, %s, %s, %s, %s, %s, NOW(), NOW(), NOW()
    )
    ON CONFLICT (application_id, model_version) DO UPDATE SET
        model_type = EXCLUDED.model_type,
        risk_class = EXCLUDED.risk_class,
        risk_probability = EXCLUDED.risk_probability,
        predicted_processing_days = EXCLUDED.predicted_processing_days,
        scored_at = EXCLUDED.scored_at,
        updated_at = NOW();
    """

    print(f"Executing batch UPSERT into application_predictions (batch_size={batch_size})...")
    with get_cursor() as cur:
        for i in range(0, len(valid_records), batch_size):
            batch = valid_records[i : i + batch_size]
            batch_params = [
                (
                    r.application_id,
                    r.model_version,
                    r.model_type,
                    r.risk_class,
                    r.risk_probability,
                    r.predicted_processing_days,
                )
                for r in batch
            ]
            cur.executemany(upsert_query, batch_params)

        cur.connection.commit()

    print("\nBatch Scoring Complete:")
    print(f"  Model Version: {model_version}")
    print(f"  Applications Considered: {total_apps:,}")
    print(f"  Predictions Persisted: {len(valid_records):,}")
    print(f"  Records Skipped: {len(skipped_records):,}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Batch prediction materialization script for SLA Risk ML models.")
    parser.add_argument("--model-version", type=str, required=True, help="Explicit model version string (e.g. v1.0). REQUIRED.")
    parser.add_argument("--model-path", type=Path, default=Path("models/sla_predictor.joblib"), help="Path to fitted model joblib artifact.")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for UPSERT queries (default: 1000).")
    parser.add_argument("--limit", type=int, default=None, help="Optional limit on applications scored.")
    parser.add_argument("--dry-run", action="store_true", help="Validate predictions without inserting into database.")

    args = parser.parse_args()
    return populate_predictive_scores(
        model_version=args.model_version,
        model_path=args.model_path,
        batch_size=args.batch_size,
        limit=args.limit,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
