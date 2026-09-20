"""Predictive Query Layer for SLA Risk Classification & Cycle Time Inference.

Provides typed query functions that interface with PostgreSQL and trained ML models
to return SLA risk probabilities and predicted processing durations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from src.database import get_cursor
from src.ml.feature_engineering import (
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
)
from src.ml.sla_predictor import SLARiskPredictor

DEFAULT_MODEL_PATH = Path("models/sla_predictor.joblib")


def get_application_features_for_inference(application_id: str) -> pd.DataFrame:
    """Fetch at-start predictor features for a single application from PostgreSQL.

    Args:
        application_id: Application trace identifier.

    Returns:
        Single-row DataFrame containing at-start feature columns.
    """
    if not isinstance(application_id, str) or not application_id.strip():
        raise ValueError(f"Invalid application_id: {application_id!r}")

    query = """
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
        JOIN synthetic_extensions s ON m.application_id = s.application_id
        WHERE m.application_id = %s;
    """
    with get_cursor() as cur:
        cur.execute(query, (application_id.strip(),))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Application ID {application_id!r} not found in database.")
        columns = [desc[0] for desc in cur.description]

    df = pd.DataFrame([row], columns=columns)

    # Derived time components
    first_dt = pd.to_datetime(df["first_event_time"], utc=True)
    df["submission_hour"] = first_dt.dt.hour
    df["submission_day_of_week"] = first_dt.dt.dayofweek
    df["submission_month"] = first_dt.dt.month
    df["is_weekend"] = (first_dt.dt.dayofweek >= 5).astype(int)

    df["requested_amount"] = df["requested_amount"].astype(float)
    df["page_count"] = df["page_count"].astype(int)
    df["quality_score"] = df["quality_score"].astype(float)
    df["sla_target_hours"] = df["sla_target_hours"].astype(int)

    feature_cols = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    return df[feature_cols].copy()


def predict_application_risk(
    application_id: str,
    model_path: str | Path = DEFAULT_MODEL_PATH,
) -> dict[str, Any]:
    """Predict SLA risk class, breach probability, and cycle time for an application.

    Args:
        application_id: Application trace identifier.
        model_path: Path to serialized SLARiskPredictor model joblib artifact.

    Returns:
        Dictionary containing prediction results, probabilities, and metadata.
    """
    features_df = get_application_features_for_inference(application_id)
    predictor = SLARiskPredictor.load(model_path)

    risk_class = int(predictor.predict_risk(features_df)[0])
    risk_proba = float(predictor.predict_risk_proba(features_df)[0])
    cycle_time_days = float(predictor.predict_cycle_time(features_df)[0])

    return {
        "application_id": application_id,
        "sla_risk_class": risk_class,
        "sla_risk_label": "High Risk" if risk_class == 1 else "Low Risk",
        "sla_breach_probability": round(risk_proba, 4),
        "predicted_processing_days": round(cycle_time_days, 2),
        "model_type": "HistGradientBoosting",
    }


def predict_batch_risk(
    application_ids: Iterable[str],
    model_path: str | Path = DEFAULT_MODEL_PATH,
) -> list[dict[str, Any]]:
    """Predict SLA risk metrics for a batch of application IDs.

    Args:
        application_ids: Sequence of application trace identifiers.
        model_path: Path to serialized SLARiskPredictor model joblib artifact.

    Returns:
        List of prediction result dictionaries.
    """
    if application_ids is None:
        raise ValueError("application_ids cannot be None")

    predictor = SLARiskPredictor.load(model_path)
    results = []
    for app_id in application_ids:
        try:
            features_df = get_application_features_for_inference(app_id)
            risk_class = int(predictor.predict_risk(features_df)[0])
            risk_proba = float(predictor.predict_risk_proba(features_df)[0])
            cycle_time_days = float(predictor.predict_cycle_time(features_df)[0])

            results.append(
                {
                    "application_id": app_id,
                    "sla_risk_class": risk_class,
                    "sla_risk_label": "High Risk" if risk_class == 1 else "Low Risk",
                    "sla_breach_probability": round(risk_proba, 4),
                    "predicted_processing_days": round(cycle_time_days, 2),
                    "status": "SUCCESS",
                }
            )
        except Exception as err:
            results.append(
                {
                    "application_id": app_id,
                    "error": str(err),
                    "status": "ERROR",
                }
            )

    return results
