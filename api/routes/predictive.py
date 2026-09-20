"""Router for Predictive Analytics Query Endpoints."""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException, Query, status

from api.schemas import (
    HighRiskApplicationsResponse,
    PredictedProcessingTimeSummaryResponse,
    PredictionCoverageResponse,
    PredictionErrorSummaryResponse,
    RiskDistributionResponse,
    RiskProbabilityBandsResponse,
)
from src.analytics import predictive_analytics

router = APIRouter(prefix="/api/v1/predictive", tags=["Predictive Analytics"])


@router.get(
    "/coverage",
    response_model=PredictionCoverageResponse,
    summary="Get Prediction Coverage Metrics",
)
def get_prediction_coverage_endpoint(
    model_version: str | None = Query(None, description="Optional model version filter (e.g. 'v1.0')"),
) -> dict[str, Any]:
    """Calculate prediction coverage statistics relative to total applications."""
    try:
        return predictive_analytics.get_prediction_coverage(model_version=model_version)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)) from err
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch prediction coverage: {err}",
        ) from err


@router.get(
    "/risk-distribution",
    response_model=RiskDistributionResponse,
    summary="Get Risk Class Distribution",
)
def get_risk_distribution_endpoint(
    model_version: str | None = Query(None, description="Optional model version filter (e.g. 'v1.0')"),
) -> dict[str, Any]:
    """Get prediction counts and percentages grouped by risk class and label."""
    try:
        items = predictive_analytics.get_risk_distribution(model_version=model_version)
        return {"items": items, "model_version": model_version}
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)) from err
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch risk distribution: {err}",
        ) from err


@router.get(
    "/probability-bands",
    response_model=RiskProbabilityBandsResponse,
    summary="Get Risk Probability Bands Distribution",
)
def get_risk_probability_bands_endpoint(
    model_version: str | None = Query(None, description="Optional model version filter (e.g. 'v1.0')"),
) -> dict[str, Any]:
    """Group predicted risk probabilities into 5 defined, non-overlapping bands."""
    try:
        items = predictive_analytics.get_risk_probability_bands(model_version=model_version)
        return {"items": items, "model_version": model_version}
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)) from err
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch risk probability bands: {err}",
        ) from err


@router.get(
    "/processing-time-summary",
    response_model=PredictedProcessingTimeSummaryResponse,
    summary="Get Predicted Processing Duration Summary",
)
def get_predicted_processing_time_summary_endpoint(
    model_version: str | None = Query(None, description="Optional model version filter (e.g. 'v1.0')"),
) -> dict[str, Any]:
    """Calculate summary statistics (mean, median, min, max) for predicted processing days."""
    try:
        return predictive_analytics.get_predicted_processing_time_summary(model_version=model_version)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)) from err
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch processing time summary: {err}",
        ) from err


@router.get(
    "/prediction-error-summary",
    response_model=PredictionErrorSummaryResponse,
    summary="Get Retrospective Prediction Error Summary",
)
def get_prediction_error_summary_endpoint(
    model_version: str | None = Query(None, description="Optional model version filter (e.g. 'v1.0')"),
) -> dict[str, Any]:
    """Calculate retrospective prediction error metrics (MAE, RMSE, Mean Error) on completed cases."""
    try:
        return predictive_analytics.get_prediction_error_summary(model_version=model_version)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)) from err
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch prediction error summary: {err}",
        ) from err


@router.get(
    "/high-risk",
    response_model=HighRiskApplicationsResponse,
    summary="Get High-Risk Applications List",
)
def get_high_risk_applications_endpoint(
    min_probability: float = Query(0.5, ge=0.0, le=1.0, description="Minimum risk probability threshold (0.0 to 1.0)"),
    limit: int = Query(50, gt=0, description="Maximum number of applications to return"),
    model_version: str | None = Query(None, description="Optional model version filter (e.g. 'v1.0')"),
) -> dict[str, Any]:
    """Retrieve applications meeting or exceeding a target risk probability threshold."""
    try:
        items = predictive_analytics.get_high_risk_applications(
            min_probability=min_probability,
            limit=limit,
            model_version=model_version,
        )
        return {
            "items": items,
            "total_returned": len(items),
            "min_probability": min_probability,
            "model_version": model_version,
        }
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(err)) from err
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch high-risk applications: {err}",
        ) from err
