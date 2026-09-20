"""Feature Engineering Pipeline for SLA Risk Classification & Cycle Time Prediction.

Extracts at-start predictor features from application metrics and synthetic extensions,
enforces strict target leakage guardrails, and builds scikit-learn preprocessing pipelines.
"""

from __future__ import annotations

from typing import Any, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.database import get_cursor

# Real source at-start features
REAL_SOURCE_NUMERIC_FEATURES = [
    "requested_amount",
    "submission_hour",
    "submission_day_of_week",
    "submission_month",
]

REAL_SOURCE_CATEGORICAL_FEATURES = [
    "application_type",
    "loan_goal",
]

REAL_SOURCE_FEATURES = REAL_SOURCE_NUMERIC_FEATURES + REAL_SOURCE_CATEGORICAL_FEATURES

# Synthetic extension features
SYNTHETIC_NUMERIC_FEATURES = [
    "page_count",
    "quality_score",
    "sla_target_hours",
]

SYNTHETIC_CATEGORICAL_FEATURES = [
    "document_type",
    "branch",
    "operator_team",
    "priority",
    "region",
    "channel",
]

SYNTHETIC_FEATURES = SYNTHETIC_NUMERIC_FEATURES + SYNTHETIC_CATEGORICAL_FEATURES

# Full feature lists
NUMERIC_FEATURES = REAL_SOURCE_NUMERIC_FEATURES + SYNTHETIC_NUMERIC_FEATURES
CATEGORICAL_FEATURES = REAL_SOURCE_CATEGORICAL_FEATURES + SYNTHETIC_CATEGORICAL_FEATURES
FULL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES

# Explicit Leakage Guardrail: Post-start features that MUST NOT be used for predictions at submission time
LEAKAGE_FEATURES = [
    "event_count",
    "last_event_time",
    "processing_hours",
    "processing_days",
    "complete_count",
    "suspend_count",
    "withdraw_count",
    "workflow_activity_count",
    "offer_activity_count",
    "application_activity_count",
    "status",
    "error_flag",
    "rejection_flag",
]


def load_dataset_from_db() -> pd.DataFrame:
    """Fetch combined application metrics and synthetic extension metadata from PostgreSQL.

    Returns:
        DataFrame containing all trace attributes and synthetic extension fields for 31,509 cases.
    """
    query = """
        SELECT
            m.application_id,
            m.application_type,
            m.loan_goal,
            COALESCE(m.requested_amount, 0.0) AS requested_amount,
            m.first_event_time,
            m.last_event_time,
            m.processing_hours,
            m.processing_days,
            s.document_type,
            s.page_count,
            s.branch,
            s.operator_team,
            s.priority,
            s.sla_target_hours,
            s.region,
            s.channel,
            s.quality_score,
            s.error_flag,
            s.rejection_flag
        FROM view_application_metrics m
        JOIN synthetic_extensions s ON m.application_id = s.application_id
        ORDER BY m.application_id;
    """
    with get_cursor() as cur:
        cur.execute(query)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()

    df = pd.DataFrame(rows, columns=columns)
    return df


def build_preprocessor(feature_subset: str = "full") -> ColumnTransformer:
    """Construct Scikit-Learn ColumnTransformer for feature preprocessing.

    Args:
        feature_subset: "full" for real + synthetic features, or "real" for real source features only.

    Returns:
        Configured ColumnTransformer instance.
    """
    if feature_subset == "real":
        num_cols = REAL_SOURCE_NUMERIC_FEATURES
        cat_cols = REAL_SOURCE_CATEGORICAL_FEATURES
    elif feature_subset == "full":
        num_cols = NUMERIC_FEATURES
        cat_cols = CATEGORICAL_FEATURES
    else:
        raise ValueError(f"Invalid feature_subset {feature_subset!r}. Must be 'real' or 'full'.")

    numeric_transformer = StandardScaler()
    categorical_transformer = OneHotEncoder(handle_unknown="ignore", sparse_output=False)

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, num_cols),
            ("cat", categorical_transformer, cat_cols),
        ],
        remainder="drop",
    )
    return preprocessor


def compute_training_threshold(y_days_train: pd.Series | np.ndarray, strategy: str = "median") -> float:
    """Compute threshold strictly on training set processing duration to eliminate threshold leakage.

    Args:
        y_days_train: Processing duration in days for training split only.
        strategy: 'median' (default: balanced 50/50 split) or 'mean' (upper-tail split).

    Returns:
        Computed float threshold value.
    """
    arr = np.asarray(y_days_train, dtype=float)
    if strategy == "median":
        return float(np.median(arr))
    elif strategy == "mean":
        return float(np.mean(arr))
    else:
        raise ValueError(f"Invalid threshold strategy {strategy!r}. Must be 'median' or 'mean'.")


def prepare_features_and_targets(
    df: pd.DataFrame,
    threshold: float | None = None,
) -> tuple[pd.DataFrame, dict[str, pd.Series]]:
    """Extract at-start predictor features and target variables from raw DataFrame.

    Guarantees strict exclusion of leakage fields.

    Args:
        df: Raw DataFrame returned by load_dataset_from_db().
        threshold: Optional float threshold for operational SLA breach. If None, computes dataset mean.

    Returns:
        Tuple of (features_df, targets_dict).
    """
    clean_df = df.copy()

    # Derived time components from first_event_time (submission time)
    first_dt = pd.to_datetime(clean_df["first_event_time"], utc=True)
    clean_df["submission_hour"] = first_dt.dt.hour
    clean_df["submission_day_of_week"] = first_dt.dt.dayofweek
    clean_df["submission_month"] = first_dt.dt.month
    clean_df["is_weekend"] = (first_dt.dt.dayofweek >= 5).astype(int)

    # Ensure numeric columns are properly typed
    clean_df["requested_amount"] = clean_df["requested_amount"].astype(float)
    clean_df["page_count"] = clean_df["page_count"].astype(int)
    clean_df["quality_score"] = clean_df["quality_score"].astype(float)
    clean_df["sla_target_hours"] = clean_df["sla_target_hours"].astype(int)

    # Features DataFrame (At-start predictors only)
    feature_cols = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    features_df = clean_df[feature_cols].copy()

    # Targets dictionary
    proc_days = clean_df["processing_days"].astype(float)
    proc_hours = clean_df["processing_hours"].astype(float)
    sla_hours = clean_df["sla_target_hours"].astype(float)

    # Mean and median thresholds
    dataset_mean_thresh = float(proc_days.mean())
    dataset_median_thresh = float(proc_days.median())

    chosen_thresh = threshold if threshold is not None else dataset_mean_thresh

    targets = {
        "processing_days": proc_days,
        "log_processing_days": np.log1p(np.maximum(0.0, proc_days)),
        "is_sla_breach_operational": (proc_days > chosen_thresh).astype(int),
        "is_sla_breach_median": (proc_days > dataset_median_thresh).astype(int),
        "is_sla_breach_strict": (proc_hours > sla_hours).astype(int),
    }

    return features_df, targets
