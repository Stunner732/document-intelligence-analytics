"""Python Predictive Analytics Layer for SLA Risk & Cycle Time Predictions.

Provides reusable analytical query functions interfacing with PostgreSQL
predictive views (`view_predictive_sla_risk` and `view_predictive_sla_risk_latest`)
and the `application_predictions` table.

Functions:
- get_prediction_coverage: Coverage metrics relative to total applications.
- get_risk_distribution: Risk class and label counts and percentages.
- get_risk_probability_bands: Probability distribution across 5 non-overlapping bands.
- get_predicted_processing_time_summary: Summary stats (mean, median, min, max) of predicted days.
- get_prediction_error_summary: Retrospective error metrics (MAE, RMSE, mean error) for completed apps.
- get_high_risk_applications: Parameterized listing of applications exceeding a risk threshold.
"""

from __future__ import annotations

from typing import Any

from src.database import get_cursor


def _validate_model_version(model_version: str | None) -> str | None:
    """Validate and sanitize optional model_version parameter.

    Args:
        model_version: Optional model version identifier string.

    Returns:
        Stripped string or None.

    Raises:
        ValueError: If model_version is provided but is not a non-empty string.
    """
    if model_version is None:
        return None
    if not isinstance(model_version, str) or not model_version.strip():
        raise ValueError(f"model_version must be a non-empty string or None, got: {model_version!r}")
    return model_version.strip()


def get_prediction_coverage(model_version: str | None = None) -> dict[str, Any]:
    """Calculate prediction coverage statistics relative to total applications.

    Args:
        model_version: Optional filter for a specific model version string (e.g. 'v1.0').

    Returns:
        Dictionary containing:
        - total_applications: Total applications count in applications table.
        - applications_with_predictions: Count of distinct applications with predictions.
        - applications_without_predictions: Count of applications lacking predictions.
        - coverage_percentage: Percentage of total applications scored (0.0 to 100.0).
        - model_version: The model version filter applied (or None).
    """
    version = _validate_model_version(model_version)

    with get_cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM applications;")
        total_apps = cur.fetchone()[0]

        if version is None:
            cur.execute("SELECT COUNT(DISTINCT application_id) FROM application_predictions;")
        else:
            cur.execute(
                "SELECT COUNT(DISTINCT application_id) FROM application_predictions WHERE model_version = %s;",
                (version,),
            )
        scored_apps = cur.fetchone()[0]

    unscored_apps = max(0, total_apps - scored_apps)
    coverage_pct = round((scored_apps / total_apps) * 100.0, 2) if total_apps > 0 else 0.0

    return {
        "total_applications": total_apps,
        "applications_with_predictions": scored_apps,
        "applications_without_predictions": unscored_apps,
        "coverage_percentage": coverage_pct,
        "model_version": version,
    }


def get_risk_distribution(model_version: str | None = None) -> list[dict[str, Any]]:
    """Get prediction counts and percentages grouped by risk class and label.

    Uses `view_predictive_sla_risk_latest` when model_version is None to ensure a single
    prediction per application, or `view_predictive_sla_risk` filtered by model_version.

    Args:
        model_version: Optional filter for a specific model version string (e.g. 'v1.0').

    Returns:
        List of dicts, each containing:
        - predicted_risk_class: 0 (Low Risk) or 1 (High Risk).
        - predicted_risk_label: 'Low Risk' or 'High Risk'.
        - count: Total applications in this risk class.
        - percentage: Percentage of total predictions.
        - model_version: Model version filter applied (or None).
    """
    version = _validate_model_version(model_version)

    if version is None:
        query = """
            SELECT
                predicted_risk_class,
                predicted_risk_label,
                COUNT(*) AS count
            FROM view_predictive_sla_risk_latest
            GROUP BY predicted_risk_class, predicted_risk_label
            ORDER BY predicted_risk_class ASC;
        """
        params: tuple[Any, ...] = ()
    else:
        query = """
            SELECT
                predicted_risk_class,
                predicted_risk_label,
                COUNT(*) AS count
            FROM view_predictive_sla_risk
            WHERE model_version = %s
            GROUP BY predicted_risk_class, predicted_risk_label
            ORDER BY predicted_risk_class ASC;
        """
        params = (version,)

    with get_cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    total_count = sum(row[2] for row in rows)

    return [
        {
            "predicted_risk_class": int(row[0]),
            "predicted_risk_label": str(row[1]),
            "count": int(row[2]),
            "percentage": round((row[2] / total_count) * 100.0, 2) if total_count > 0 else 0.0,
            "model_version": version,
        }
        for row in rows
    ]


def get_risk_probability_bands(model_version: str | None = None) -> list[dict[str, Any]]:
    """Group predicted risk probabilities into 5 defined, non-overlapping bands.

    Band Boundary Behavior:
    - '0.0 - 0.2': 0.0 <= risk_probability < 0.2
    - '0.2 - 0.4': 0.2 <= risk_probability < 0.4
    - '0.4 - 0.6': 0.4 <= risk_probability < 0.6
    - '0.6 - 0.8': 0.6 <= risk_probability < 0.8
    - '0.8 - 1.0': 0.8 <= risk_probability <= 1.0 (upper bound 1.0 is inclusive)

    Args:
        model_version: Optional filter for a specific model version string (e.g. 'v1.0').

    Returns:
        List of 5 dicts (one per band in ascending order), each containing:
        - probability_band: Band label string (e.g. '0.0 - 0.2').
        - count: Number of applications in the band.
        - percentage: Percentage of total predictions in the band.
        - model_version: Model version filter applied (or None).
    """
    version = _validate_model_version(model_version)

    bands_order = ["0.0 - 0.2", "0.2 - 0.4", "0.4 - 0.6", "0.6 - 0.8", "0.8 - 1.0"]

    if version is None:
        query = """
            SELECT
                CASE
                    WHEN predicted_risk_probability >= 0.0 AND predicted_risk_probability < 0.2 THEN '0.0 - 0.2'
                    WHEN predicted_risk_probability >= 0.2 AND predicted_risk_probability < 0.4 THEN '0.2 - 0.4'
                    WHEN predicted_risk_probability >= 0.4 AND predicted_risk_probability < 0.6 THEN '0.4 - 0.6'
                    WHEN predicted_risk_probability >= 0.6 AND predicted_risk_probability < 0.8 THEN '0.6 - 0.8'
                    WHEN predicted_risk_probability >= 0.8 AND predicted_risk_probability <= 1.0 THEN '0.8 - 1.0'
                END AS probability_band,
                COUNT(*) AS count
            FROM view_predictive_sla_risk_latest
            GROUP BY 1;
        """
        params: tuple[Any, ...] = ()
    else:
        query = """
            SELECT
                CASE
                    WHEN predicted_risk_probability >= 0.0 AND predicted_risk_probability < 0.2 THEN '0.0 - 0.2'
                    WHEN predicted_risk_probability >= 0.2 AND predicted_risk_probability < 0.4 THEN '0.2 - 0.4'
                    WHEN predicted_risk_probability >= 0.4 AND predicted_risk_probability < 0.6 THEN '0.4 - 0.6'
                    WHEN predicted_risk_probability >= 0.6 AND predicted_risk_probability < 0.8 THEN '0.6 - 0.8'
                    WHEN predicted_risk_probability >= 0.8 AND predicted_risk_probability <= 1.0 THEN '0.8 - 1.0'
                END AS probability_band,
                COUNT(*) AS count
            FROM view_predictive_sla_risk
            WHERE model_version = %s
            GROUP BY 1;
        """
        params = (version,)

    with get_cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    counts_by_band = {row[0]: row[1] for row in rows if row[0] is not None}
    total_count = sum(counts_by_band.values())

    result = []
    for band in bands_order:
        cnt = counts_by_band.get(band, 0)
        pct = round((cnt / total_count) * 100.0, 2) if total_count > 0 else 0.0
        result.append(
            {
                "probability_band": band,
                "count": cnt,
                "percentage": pct,
                "model_version": version,
            }
        )

    return result


def get_predicted_processing_time_summary(model_version: str | None = None) -> dict[str, Any]:
    """Calculate summary statistics for predicted processing days.

    Computes count, mean, median (50th percentile), min, and max values.

    Args:
        model_version: Optional filter for a specific model version string (e.g. 'v1.0').

    Returns:
        Dictionary containing:
        - count: Total evaluated predictions count.
        - mean_days: Average predicted processing days (rounded to 2 decimal places).
        - median_days: Median predicted processing days (rounded to 2 decimal places).
        - min_days: Minimum predicted processing days.
        - max_days: Maximum predicted processing days.
        - model_version: Model version filter applied (or None).
    """
    version = _validate_model_version(model_version)

    if version is None:
        query = """
            SELECT
                COUNT(*) AS count,
                AVG(predicted_processing_days) AS mean_days,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY predicted_processing_days) AS median_days,
                MIN(predicted_processing_days) AS min_days,
                MAX(predicted_processing_days) AS max_days
            FROM view_predictive_sla_risk_latest;
        """
        params: tuple[Any, ...] = ()
    else:
        query = """
            SELECT
                COUNT(*) AS count,
                AVG(predicted_processing_days) AS mean_days,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY predicted_processing_days) AS median_days,
                MIN(predicted_processing_days) AS min_days,
                MAX(predicted_processing_days) AS max_days
            FROM view_predictive_sla_risk
            WHERE model_version = %s;
        """
        params = (version,)

    with get_cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone()

    cnt = row[0] if row and row[0] is not None else 0
    if cnt == 0 or row[1] is None:
        return {
            "count": 0,
            "mean_days": 0.0,
            "median_days": 0.0,
            "min_days": 0.0,
            "max_days": 0.0,
            "model_version": version,
        }

    return {
        "count": int(cnt),
        "mean_days": round(float(row[1]), 2),
        "median_days": round(float(row[2]), 2),
        "min_days": round(float(row[3]), 2),
        "max_days": round(float(row[4]), 2),
        "model_version": version,
    }


def get_prediction_error_summary(model_version: str | None = None) -> dict[str, Any]:
    """Calculate retrospective prediction error metrics on completed applications.

    Note: This measures retrospective performance on completed applications within the
    historical dataset where actual_processing_days and processing_days_error are non-NULL.

    Calculates:
    - MAE: Mean Absolute Error (AVG(|actual_days - predicted_days|)).
    - RMSE: Root Mean Squared Error (SQRT(AVG((actual_days - predicted_days)^2))).
    - Mean Error: Signed mean error (AVG(actual_days - predicted_days)). Positive indicates
      underprediction (actual > predicted), negative indicates overprediction.

    Args:
        model_version: Optional filter for a specific model version string (e.g. 'v1.0').

    Returns:
        Dictionary containing:
        - evaluated_count: Count of completed applications with non-NULL actual processing days.
        - mae_days: Mean Absolute Error in days.
        - rmse_days: Root Mean Squared Error in days.
        - mean_error_days: Signed Mean Error in days.
        - model_version: Model version filter applied (or None).
    """
    version = _validate_model_version(model_version)

    if version is None:
        query = """
            SELECT
                COUNT(processing_days_error) AS evaluated_count,
                AVG(ABS(processing_days_error)) AS mae_days,
                SQRT(AVG(POWER(processing_days_error, 2))) AS rmse_days,
                AVG(processing_days_error) AS mean_error_days
            FROM view_predictive_sla_risk_latest
            WHERE actual_processing_days IS NOT NULL
              AND processing_days_error IS NOT NULL;
        """
        params: tuple[Any, ...] = ()
    else:
        query = """
            SELECT
                COUNT(processing_days_error) AS evaluated_count,
                AVG(ABS(processing_days_error)) AS mae_days,
                SQRT(AVG(POWER(processing_days_error, 2))) AS rmse_days,
                AVG(processing_days_error) AS mean_error_days
            FROM view_predictive_sla_risk
            WHERE model_version = %s
              AND actual_processing_days IS NOT NULL
              AND processing_days_error IS NOT NULL;
        """
        params = (version,)

    with get_cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone()

    cnt = row[0] if row and row[0] is not None else 0
    if cnt == 0 or row[1] is None:
        return {
            "evaluated_count": 0,
            "mae_days": 0.0,
            "rmse_days": 0.0,
            "mean_error_days": 0.0,
            "model_version": version,
        }

    return {
        "evaluated_count": int(cnt),
        "mae_days": round(float(row[1]), 2),
        "rmse_days": round(float(row[2]), 2),
        "mean_error_days": round(float(row[3]), 2),
        "model_version": version,
    }


def get_high_risk_applications(
    min_probability: float = 0.5,
    limit: int = 50,
    model_version: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieve applications meeting or exceeding a target risk probability threshold.

    Ordered deterministically by predicted_risk_probability DESC, then application_id ASC.

    Args:
        min_probability: Minimum risk probability threshold (float between 0.0 and 1.0).
        limit: Maximum number of rows to return (positive integer).
        model_version: Optional filter for a specific model version string (e.g. 'v1.0').

    Returns:
        List of dicts, each containing:
        - application_id: Application identifier.
        - application_type: New credit / Limit raise.
        - loan_goal: Purpose of loan.
        - requested_amount: Requested loan amount.
        - application_status: Status label.
        - predicted_risk_class: 0 or 1.
        - predicted_risk_label: 'Low Risk' or 'High Risk'.
        - predicted_risk_probability: Risk probability value.
        - predicted_processing_days: Predicted cycle time duration.
        - model_version: Model version identifier.
        - scored_at: ISO format timestamp string.

    Raises:
        ValueError: If min_probability is not in [0.0, 1.0], limit <= 0, or model_version invalid.
    """
    version = _validate_model_version(model_version)

    if isinstance(min_probability, bool) or not isinstance(min_probability, (int, float)):
        raise ValueError(f"min_probability must be a float between 0.0 and 1.0, got: {min_probability!r}")
    prob = float(min_probability)
    if prob < 0.0 or prob > 1.0:
        raise ValueError(f"min_probability must be between 0.0 and 1.0, got: {min_probability!r}")

    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError(f"limit must be a positive integer, got: {limit!r}")

    if version is None:
        query = """
            SELECT
                application_id,
                application_type,
                loan_goal,
                requested_amount,
                application_status,
                predicted_risk_class,
                predicted_risk_label,
                predicted_risk_probability,
                predicted_processing_days,
                model_version,
                scored_at
            FROM view_predictive_sla_risk_latest
            WHERE predicted_risk_probability >= %s
            ORDER BY predicted_risk_probability DESC, application_id ASC
            LIMIT %s;
        """
        params: tuple[Any, ...] = (prob, limit)
    else:
        query = """
            SELECT
                application_id,
                application_type,
                loan_goal,
                requested_amount,
                application_status,
                predicted_risk_class,
                predicted_risk_label,
                predicted_risk_probability,
                predicted_processing_days,
                model_version,
                scored_at
            FROM view_predictive_sla_risk
            WHERE predicted_risk_probability >= %s
              AND model_version = %s
            ORDER BY predicted_risk_probability DESC, application_id ASC
            LIMIT %s;
        """
        params = (prob, version, limit)

    with get_cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    return [
        {
            "application_id": str(row[0]),
            "application_type": str(row[1]) if row[1] is not None else None,
            "loan_goal": str(row[2]) if row[2] is not None else None,
            "requested_amount": float(row[3]) if row[3] is not None else 0.0,
            "application_status": str(row[4]) if row[4] is not None else None,
            "predicted_risk_class": int(row[5]),
            "predicted_risk_label": str(row[6]),
            "predicted_risk_probability": float(row[7]),
            "predicted_processing_days": float(row[8]),
            "model_version": str(row[9]),
            "scored_at": row[10].isoformat() if hasattr(row[10], "isoformat") else str(row[10]),
        }
        for row in rows
    ]
