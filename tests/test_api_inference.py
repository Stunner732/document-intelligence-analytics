"""Unit and integration tests for Live Single-Application Inference API endpoint."""

from __future__ import annotations

from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.schemas import ApplicationRiskPredictionResponse
from src.database import check_database_connection

client = TestClient(app)


@pytest.fixture(scope="module")
def db_available() -> bool:
    """Fixture indicating if live PostgreSQL database is reachable."""
    return check_database_connection()


class TestAPILiveInferenceEndpoint:
    """Tests for GET /api/v1/predict/risk/{application_id}."""

    @patch("src.analytics.predictive_queries.predict_application_risk")
    def test_predict_risk_success_mocked(self, mock_predict) -> None:
        mock_predict.return_value = {
            "application_id": "Application_1000086665",
            "sla_risk_class": 0,
            "sla_risk_label": "Low Risk",
            "sla_breach_probability": 0.4749,
            "predicted_processing_days": 19.47,
            "model_type": "HistGradientBoosting",
        }
        response = client.get("/api/v1/predict/risk/Application_1000086665")
        assert response.status_code == 200
        data = response.json()
        assert data["application_id"] == "Application_1000086665"
        assert data["sla_risk_class"] in (0, 1)
        assert data["sla_risk_label"] in ("Low Risk", "High Risk")
        assert 0.0 <= data["sla_breach_probability"] <= 1.0
        assert data["predicted_processing_days"] >= 0.0
        assert data["model_type"] == "HistGradientBoosting"

        # Pydantic schema validation
        validated = ApplicationRiskPredictionResponse(**data)
        assert validated.application_id == "Application_1000086665"

    @patch("src.analytics.predictive_queries.predict_application_risk", side_effect=ValueError("Application ID 'INVALID_ID_999' not found in database."))
    def test_predict_risk_nonexistent_application_id_returns_404(self, mock_predict) -> None:
        response = client.get("/api/v1/predict/risk/INVALID_ID_999")
        assert response.status_code == 404
        assert "not found in database" in response.json()["detail"]

    @patch("src.analytics.predictive_queries.predict_application_risk", side_effect=FileNotFoundError("models/sla_predictor.joblib not found"))
    def test_predict_risk_missing_model_artifact_returns_500(self, mock_predict) -> None:
        response = client.get("/api/v1/predict/risk/Application_1000086665")
        assert response.status_code == 500
        assert "Inference error" in response.json()["detail"]

    @patch("src.analytics.predictive_queries.predict_application_risk", side_effect=RuntimeError("Database connection dropped"))
    def test_predict_risk_db_failure_returns_500(self, mock_predict) -> None:
        response = client.get("/api/v1/predict/risk/Application_1000086665")
        assert response.status_code == 500
        assert "Inference error" in response.json()["detail"]

    def test_predict_risk_empty_application_id_returns_422(self) -> None:
        response = client.get("/api/v1/predict/risk/%20")
        assert response.status_code == 422
        assert "non-empty string" in response.json()["detail"]


class TestAPILiveInferenceLiveIntegration:
    """Integration test executing live model inference against PostgreSQL database."""

    def test_live_database_inference_call(self, db_available: bool) -> None:
        if not db_available:
            pytest.skip("PostgreSQL database not available")

        response = client.get("/api/v1/predict/risk/Application_1000086665")
        assert response.status_code == 200
        data = response.json()
        assert data["application_id"] == "Application_1000086665"
        assert data["sla_risk_class"] in (0, 1)
        assert data["sla_risk_label"] in ("Low Risk", "High Risk")
        assert 0.0 <= data["sla_breach_probability"] <= 1.0
        assert data["predicted_processing_days"] >= 0.0
        assert data["model_type"] == "HistGradientBoosting"
