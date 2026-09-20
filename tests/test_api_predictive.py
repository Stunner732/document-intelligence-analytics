"""Unit and integration tests for Predictive Analytics API Endpoints."""

from __future__ import annotations

from unittest.mock import patch
from fastapi.testclient import TestClient

from api.main import app
from api.schemas import (
    HighRiskApplicationsResponse,
    PredictedProcessingTimeSummaryResponse,
    PredictionCoverageResponse,
    PredictionErrorSummaryResponse,
    RiskDistributionResponse,
    RiskProbabilityBandsResponse,
)

client = TestClient(app)


class TestAPIPredictiveCoverageEndpoint:
    """Tests for GET /api/v1/predictive/coverage."""

    @patch("src.analytics.predictive_analytics.get_prediction_coverage")
    def test_coverage_endpoint_success(self, mock_func) -> None:
        mock_func.return_value = {
            "total_applications": 100,
            "applications_with_predictions": 80,
            "applications_without_predictions": 20,
            "coverage_percentage": 80.0,
            "model_version": None,
        }
        response = client.get("/api/v1/predictive/coverage")
        assert response.status_code == 200
        data = response.json()
        assert data["total_applications"] == 100
        assert data["coverage_percentage"] == 80.0
        # Schema validation
        validated = PredictionCoverageResponse(**data)
        assert validated.applications_with_predictions == 80

    @patch("src.analytics.predictive_analytics.get_prediction_coverage")
    def test_coverage_endpoint_with_model_version(self, mock_func) -> None:
        mock_func.return_value = {
            "total_applications": 100,
            "applications_with_predictions": 100,
            "applications_without_predictions": 0,
            "coverage_percentage": 100.0,
            "model_version": "v1.0",
        }
        response = client.get("/api/v1/predictive/coverage?model_version=v1.0")
        assert response.status_code == 200
        mock_func.assert_called_once_with(model_version="v1.0")
        assert response.json()["model_version"] == "v1.0"

    @patch("src.analytics.predictive_analytics.get_prediction_coverage", side_effect=ValueError("Invalid version"))
    def test_coverage_endpoint_value_error_handling(self, mock_func) -> None:
        response = client.get("/api/v1/predictive/coverage?model_version=")
        assert response.status_code == 422
        assert "Invalid version" in response.json()["detail"]

    @patch("src.analytics.predictive_analytics.get_prediction_coverage", side_effect=RuntimeError("DB error"))
    def test_coverage_endpoint_db_failure_handling(self, mock_func) -> None:
        response = client.get("/api/v1/predictive/coverage")
        assert response.status_code == 500
        assert "Failed to fetch prediction coverage" in response.json()["detail"]


class TestAPIPredictiveRiskDistributionEndpoint:
    """Tests for GET /api/v1/predictive/risk-distribution."""

    @patch("src.analytics.predictive_analytics.get_risk_distribution")
    def test_risk_distribution_success(self, mock_func) -> None:
        mock_func.return_value = [
            {
                "predicted_risk_class": 0,
                "predicted_risk_label": "Low Risk",
                "count": 60,
                "percentage": 60.0,
                "model_version": None,
            },
            {
                "predicted_risk_class": 1,
                "predicted_risk_label": "High Risk",
                "count": 40,
                "percentage": 40.0,
                "model_version": None,
            },
        ]
        response = client.get("/api/v1/predictive/risk-distribution")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        validated = RiskDistributionResponse(**data)
        assert validated.items[0].predicted_risk_label == "Low Risk"


class TestAPIPredictiveProbabilityBandsEndpoint:
    """Tests for GET /api/v1/predictive/probability-bands."""

    @patch("src.analytics.predictive_analytics.get_risk_probability_bands")
    def test_probability_bands_success(self, mock_func) -> None:
        mock_func.return_value = [
            {"probability_band": "0.0 - 0.2", "count": 0, "percentage": 0.0, "model_version": None},
            {"probability_band": "0.2 - 0.4", "count": 10, "percentage": 10.0, "model_version": None},
            {"probability_band": "0.4 - 0.6", "count": 40, "percentage": 40.0, "model_version": None},
            {"probability_band": "0.6 - 0.8", "count": 50, "percentage": 50.0, "model_version": None},
            {"probability_band": "0.8 - 1.0", "count": 0, "percentage": 0.0, "model_version": None},
        ]
        response = client.get("/api/v1/predictive/probability-bands")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5
        validated = RiskProbabilityBandsResponse(**data)
        assert validated.items[2].probability_band == "0.4 - 0.6"


class TestAPIPredictedProcessingTimeSummaryEndpoint:
    """Tests for GET /api/v1/predictive/processing-time-summary."""

    @patch("src.analytics.predictive_analytics.get_predicted_processing_time_summary")
    def test_processing_time_summary_success(self, mock_func) -> None:
        mock_func.return_value = {
            "count": 100,
            "mean_days": 18.5,
            "median_days": 18.0,
            "min_days": 12.0,
            "max_days": 25.0,
            "model_version": None,
        }
        response = client.get("/api/v1/predictive/processing-time-summary")
        assert response.status_code == 200
        data = response.json()
        assert data["mean_days"] == 18.5
        validated = PredictedProcessingTimeSummaryResponse(**data)
        assert validated.median_days == 18.0


class TestAPIPredictionErrorSummaryEndpoint:
    """Tests for GET /api/v1/predictive/prediction-error-summary."""

    @patch("src.analytics.predictive_analytics.get_prediction_error_summary")
    def test_prediction_error_summary_success(self, mock_func) -> None:
        mock_func.return_value = {
            "evaluated_count": 100,
            "mae_days": 9.5,
            "rmse_days": 12.0,
            "mean_error_days": -3.5,
            "model_version": None,
        }
        response = client.get("/api/v1/predictive/prediction-error-summary")
        assert response.status_code == 200
        data = response.json()
        assert data["mae_days"] == 9.5
        validated = PredictionErrorSummaryResponse(**data)
        assert validated.rmse_days == 12.0


class TestAPIHighRiskApplicationsEndpoint:
    """Tests for GET /api/v1/predictive/high-risk."""

    @patch("src.analytics.predictive_analytics.get_high_risk_applications")
    def test_high_risk_applications_success(self, mock_func) -> None:
        mock_func.return_value = [
            {
                "application_id": "App_100",
                "application_type": "New credit",
                "loan_goal": "Car",
                "requested_amount": 15000.0,
                "application_status": "None",
                "predicted_risk_class": 1,
                "predicted_risk_label": "High Risk",
                "predicted_risk_probability": 0.85,
                "predicted_processing_days": 22.5,
                "model_version": "v1.0",
                "scored_at": "2026-09-20T14:53:53+00:00",
            }
        ]
        response = client.get("/api/v1/predictive/high-risk?min_probability=0.7&limit=10&model_version=v1.0")
        assert response.status_code == 200
        data = response.json()
        assert data["total_returned"] == 1
        assert data["min_probability"] == 0.7
        assert data["model_version"] == "v1.0"
        mock_func.assert_called_once_with(min_probability=0.7, limit=10, model_version="v1.0")
        validated = HighRiskApplicationsResponse(**data)
        assert validated.items[0].application_id == "App_100"

    def test_high_risk_applications_invalid_min_probability(self) -> None:
        response = client.get("/api/v1/predictive/high-risk?min_probability=1.5")
        assert response.status_code == 422

        response_neg = client.get("/api/v1/predictive/high-risk?min_probability=-0.5")
        assert response_neg.status_code == 422

    def test_high_risk_applications_invalid_limit(self) -> None:
        response = client.get("/api/v1/predictive/high-risk?limit=0")
        assert response.status_code == 422

        response_neg = client.get("/api/v1/predictive/high-risk?limit=-5")
        assert response_neg.status_code == 422
