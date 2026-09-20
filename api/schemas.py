"""Pydantic schemas for Document Intelligence & Predictive Analytics API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class HealthCheckResponse(BaseModel):
    """API health status and component readiness."""

    status: str = Field(..., description="Overall health status ('ok' or 'degraded')")
    app_name: str = Field(..., description="Application name")
    app_env: str = Field(..., description="Application execution environment")
    database_connected: bool = Field(..., description="PostgreSQL database reachability status")
    model_artifact_present: bool = Field(..., description="Trained model artifact existence status")

    model_config = ConfigDict(extra="ignore")


class PredictionCoverageResponse(BaseModel):
    """Prediction coverage metrics relative to total applications."""

    total_applications: int = Field(..., description="Total applications count in applications table")
    applications_with_predictions: int = Field(..., description="Count of distinct applications with predictions")
    applications_without_predictions: int = Field(..., description="Count of applications lacking predictions")
    coverage_percentage: float = Field(..., description="Percentage of total applications scored (0.0 to 100.0)")
    model_version: str | None = Field(None, description="Applied model version filter or None")

    model_config = ConfigDict(extra="ignore")


class RiskDistributionItem(BaseModel):
    """Risk class distribution metric entry."""

    predicted_risk_class: int = Field(..., description="0 for Low Risk, 1 for High Risk")
    predicted_risk_label: str = Field(..., description="'Low Risk' or 'High Risk'")
    count: int = Field(..., description="Number of applications in this risk class")
    percentage: float = Field(..., description="Percentage of total predictions")
    model_version: str | None = Field(None, description="Applied model version filter or None")

    model_config = ConfigDict(extra="ignore")


class RiskDistributionResponse(BaseModel):
    """List of risk class distribution items."""

    items: list[RiskDistributionItem] = Field(..., description="Risk distribution entries")
    model_version: str | None = Field(None, description="Applied model version filter or None")

    model_config = ConfigDict(extra="ignore")


class RiskProbabilityBandItem(BaseModel):
    """Risk probability band distribution metric entry."""

    probability_band: str = Field(..., description="Probability band string (e.g. '0.4 - 0.6')")
    count: int = Field(..., description="Number of applications in this probability band")
    percentage: float = Field(..., description="Percentage of total predictions")
    model_version: str | None = Field(None, description="Applied model version filter or None")

    model_config = ConfigDict(extra="ignore")


class RiskProbabilityBandsResponse(BaseModel):
    """List of risk probability band items."""

    items: list[RiskProbabilityBandItem] = Field(..., description="Probability band entries")
    model_version: str | None = Field(None, description="Applied model version filter or None")

    model_config = ConfigDict(extra="ignore")


class PredictedProcessingTimeSummaryResponse(BaseModel):
    """Summary statistics for predicted processing days."""

    count: int = Field(..., description="Total evaluated predictions count")
    mean_days: float = Field(..., description="Average predicted processing days")
    median_days: float = Field(..., description="Median predicted processing days (50th percentile)")
    min_days: float = Field(..., description="Minimum predicted processing days")
    max_days: float = Field(..., description="Maximum predicted processing days")
    model_version: str | None = Field(None, description="Applied model version filter or None")

    model_config = ConfigDict(extra="ignore")


class PredictionErrorSummaryResponse(BaseModel):
    """Retrospective prediction error metrics on completed applications."""

    evaluated_count: int = Field(..., description="Count of completed applications evaluated")
    mae_days: float = Field(..., description="Mean Absolute Error in days")
    rmse_days: float = Field(..., description="Root Mean Squared Error in days")
    mean_error_days: float = Field(..., description="Signed Mean Error in days")
    model_version: str | None = Field(None, description="Applied model version filter or None")

    model_config = ConfigDict(extra="ignore")


class HighRiskApplicationItem(BaseModel):
    """High-risk application detailed entry."""

    application_id: str = Field(..., description="Application identifier")
    application_type: str | None = Field(None, description="Application type")
    loan_goal: str | None = Field(None, description="Loan goal description")
    requested_amount: float = Field(..., description="Requested loan amount")
    application_status: str | None = Field(None, description="Application status")
    predicted_risk_class: int = Field(..., description="0 for Low Risk, 1 for High Risk")
    predicted_risk_label: str = Field(..., description="'Low Risk' or 'High Risk'")
    predicted_risk_probability: float = Field(..., description="Predicted risk probability value")
    predicted_processing_days: float = Field(..., description="Predicted processing days duration")
    model_version: str = Field(..., description="Model version identifier")
    scored_at: str = Field(..., description="Scoring timestamp ISO string")

    model_config = ConfigDict(extra="ignore")


class HighRiskApplicationsResponse(BaseModel):
    """List of high-risk applications meeting probability threshold."""

    items: list[HighRiskApplicationItem] = Field(..., description="High risk application entries")
    total_returned: int = Field(..., description="Count of returned applications")
    min_probability: float = Field(..., description="Applied minimum risk probability threshold")
    model_version: str | None = Field(None, description="Applied model version filter or None")

    model_config = ConfigDict(extra="ignore")


class ApplicationRiskPredictionResponse(BaseModel):
    """Live SLA risk prediction response for a single application."""

    application_id: str = Field(..., description="Application identifier")
    sla_risk_class: int = Field(..., description="0 for Low Risk, 1 for High Risk")
    sla_risk_label: str = Field(..., description="'Low Risk' or 'High Risk'")
    sla_breach_probability: float = Field(..., description="SLA breach risk probability (0.0 to 1.0)")
    predicted_processing_days: float = Field(..., description="Predicted processing cycle duration in days")
    model_type: str = Field(..., description="Model architecture type")

    model_config = ConfigDict(extra="ignore")
