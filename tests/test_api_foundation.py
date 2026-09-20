"""Unit tests for FastAPI application foundation and health check endpoints."""

from __future__ import annotations

from unittest.mock import patch
from fastapi.testclient import TestClient

from api.main import app
from api.schemas import (
    HealthCheckResponse,
    PredictionCoverageResponse,
    RiskDistributionItem,
    RiskDistributionResponse,
    RiskProbabilityBandItem,
    RiskProbabilityBandsResponse,
    PredictedProcessingTimeSummaryResponse,
    PredictionErrorSummaryResponse,
    HighRiskApplicationItem,
    HighRiskApplicationsResponse,
    ApplicationRiskPredictionResponse,
)

client = TestClient(app)


class TestAPIHealthEndpoint:
    """Tests for GET /health and GET /api/v1/health endpoints."""

    def test_health_endpoint_healthy_state(self) -> None:
        with patch("api.main.check_database_connection", return_value=True), \
             patch("pathlib.Path.exists", return_value=True):
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["database_connected"] is True
            assert data["model_artifact_present"] is True

            # Verify schema instantiation
            validated = HealthCheckResponse(**data)
            assert validated.status == "ok"

    def test_api_v1_health_alias(self) -> None:
        with patch("api.main.check_database_connection", return_value=True), \
             patch("pathlib.Path.exists", return_value=True):
            response = client.get("/api/v1/health")
            assert response.status_code == 200
            assert response.json()["status"] == "ok"

    def test_health_endpoint_database_disconnected(self) -> None:
        with patch("api.main.check_database_connection", return_value=False), \
             patch("pathlib.Path.exists", return_value=True):
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert data["database_connected"] is False
            assert data["model_artifact_present"] is True

    def test_health_endpoint_model_missing(self) -> None:
        with patch("api.main.check_database_connection", return_value=True), \
             patch("pathlib.Path.exists", return_value=False):
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert data["database_connected"] is True
            assert data["model_artifact_present"] is False

    def test_health_endpoint_graceful_exception_handling(self) -> None:
        with patch("api.main.check_database_connection", side_effect=RuntimeError("DB Error")), \
             patch("pathlib.Path.exists", return_value=True):
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert data["database_connected"] is False


class TestAPISchemasValidation:
    """Tests validating instantiation of defined Pydantic API response schemas."""

    def test_prediction_coverage_schema(self) -> None:
        cov = PredictionCoverageResponse(
            total_applications=100,
            applications_with_predictions=80,
            applications_without_predictions=20,
            coverage_percentage=80.0,
            model_version="v1.0",
        )
        assert cov.total_applications == 100
        assert cov.coverage_percentage == 80.0

    def test_risk_distribution_schema(self) -> None:
        item = RiskDistributionItem(
            predicted_risk_class=0,
            predicted_risk_label="Low Risk",
            count=60,
            percentage=60.0,
            model_version="v1.0",
        )
        resp = RiskDistributionResponse(items=[item], model_version="v1.0")
        assert len(resp.items) == 1
        assert resp.items[0].predicted_risk_label == "Low Risk"

    def test_risk_probability_bands_schema(self) -> None:
        item = RiskProbabilityBandItem(
            probability_band="0.4 - 0.6",
            count=50,
            percentage=50.0,
            model_version="v1.0",
        )
        resp = RiskProbabilityBandsResponse(items=[item], model_version="v1.0")
        assert resp.items[0].probability_band == "0.4 - 0.6"

    def test_predicted_processing_time_summary_schema(self) -> None:
        summary = PredictedProcessingTimeSummaryResponse(
            count=100,
            mean_days=18.5,
            median_days=18.0,
            min_days=12.0,
            max_days=25.0,
            model_version="v1.0",
        )
        assert summary.mean_days == 18.5

    def test_prediction_error_summary_schema(self) -> None:
        err = PredictionErrorSummaryResponse(
            evaluated_count=100,
            mae_days=9.5,
            rmse_days=12.0,
            mean_error_days=-3.5,
            model_version="v1.0",
        )
        assert err.mae_days == 9.5

    def test_high_risk_applications_schema(self) -> None:
        item = HighRiskApplicationItem(
            application_id="App_100",
            application_type="New credit",
            loan_goal="Car",
            requested_amount=15000.0,
            application_status="None",
            predicted_risk_class=1,
            predicted_risk_label="High Risk",
            predicted_risk_probability=0.85,
            predicted_processing_days=22.5,
            model_version="v1.0",
            scored_at="2026-09-20T14:53:53+00:00",
        )
        resp = HighRiskApplicationsResponse(
            items=[item],
            total_returned=1,
            min_probability=0.5,
            model_version="v1.0",
        )
        assert resp.total_returned == 1
        assert resp.items[0].application_id == "App_100"

    def test_application_risk_prediction_schema(self) -> None:
        pred = ApplicationRiskPredictionResponse(
            application_id="App_100",
            sla_risk_class=1,
            sla_risk_label="High Risk",
            sla_breach_probability=0.85,
            predicted_processing_days=22.5,
            model_type="HistGradientBoosting",
        )
        assert pred.sla_breach_probability == 0.85
