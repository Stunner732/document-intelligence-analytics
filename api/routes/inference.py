"""Router for Live Single-Application ML Inference Endpoints."""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException, status

from api.schemas import ApplicationRiskPredictionResponse
from src.analytics import predictive_queries

router = APIRouter(prefix="/api/v1/predict", tags=["Live Inference"])


@router.get(
    "/risk/{application_id}",
    response_model=ApplicationRiskPredictionResponse,
    summary="Get Live SLA Risk Prediction for an Application",
)
def predict_application_risk_endpoint(
    application_id: str,
) -> dict[str, Any]:
    """Predict SLA breach risk class, breach probability, and cycle time for a single application."""
    if not isinstance(application_id, str) or not application_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="application_id must be a non-empty string",
        )

    try:
        return predictive_queries.predict_application_risk(application_id=application_id.strip())
    except ValueError as err:
        err_msg = str(err)
        if "not found" in err_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=err_msg,
            ) from err
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=err_msg,
        ) from err
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference error for application {application_id!r}: {err}",
        ) from err
