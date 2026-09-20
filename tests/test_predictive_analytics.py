"""Unit and integration tests for Python Predictive Analytics Layer (src/analytics/predictive_analytics.py)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.analytics.predictive_analytics import (
    get_high_risk_applications,
    get_predicted_processing_time_summary,
    get_prediction_coverage,
    get_prediction_error_summary,
    get_risk_distribution,
    get_risk_probability_bands,
)
from src.database import check_database_connection


@pytest.fixture(scope="module")
def db_available() -> bool:
    """Fixture indicating if live PostgreSQL database is reachable."""
    return check_database_connection()


class TestPredictiveAnalyticsValidation:
    """Test input validation across all predictive analytics functions."""

    def test_invalid_model_version_type_raises(self) -> None:
        with pytest.raises(ValueError, match="model_version must be a non-empty string"):
            get_prediction_coverage(model_version=123)  # type: ignore

        with pytest.raises(ValueError, match="model_version must be a non-empty string"):
            get_risk_distribution(model_version="")

        with pytest.raises(ValueError, match="model_version must be a non-empty string"):
            get_risk_probability_bands(model_version="   ")

        with pytest.raises(ValueError, match="model_version must be a non-empty string"):
            get_predicted_processing_time_summary(model_version=[])  # type: ignore

        with pytest.raises(ValueError, match="model_version must be a non-empty string"):
            get_prediction_error_summary(model_version={})  # type: ignore

    def test_invalid_high_risk_min_probability_raises(self) -> None:
        with pytest.raises(ValueError, match="min_probability must be between 0.0 and 1.0"):
            get_high_risk_applications(min_probability=-0.1)

        with pytest.raises(ValueError, match="min_probability must be between 0.0 and 1.0"):
            get_high_risk_applications(min_probability=1.05)

        with pytest.raises(ValueError, match="min_probability must be a float"):
            get_high_risk_applications(min_probability="0.5")  # type: ignore

        with pytest.raises(ValueError, match="min_probability must be a float"):
            get_high_risk_applications(min_probability=True)  # type: ignore

    def test_invalid_high_risk_limit_raises(self) -> None:
        with pytest.raises(ValueError, match="limit must be a positive integer"):
            get_high_risk_applications(limit=0)

        with pytest.raises(ValueError, match="limit must be a positive integer"):
            get_high_risk_applications(limit=-10)

        with pytest.raises(ValueError, match="limit must be a positive integer"):
            get_high_risk_applications(limit="50")  # type: ignore

        with pytest.raises(ValueError, match="limit must be a positive integer"):
            get_high_risk_applications(limit=False)  # type: ignore


class TestPredictiveAnalyticsMockedUnit:
    """Mocked unit tests covering edge cases and query execution parameters."""

    @patch("src.analytics.predictive_analytics.get_cursor")
    def test_coverage_with_zero_predictions(self, mock_get_cursor: MagicMock) -> None:
        mock_cur = MagicMock()
        # First query total apps = 100, second query scored apps = 0
        mock_cur.fetchone.side_effect = [(100,), (0,)]
        mock_get_cursor.return_value.__enter__.return_value = mock_cur

        res = get_prediction_coverage()
        assert res["total_applications"] == 100
        assert res["applications_with_predictions"] == 0
        assert res["applications_without_predictions"] == 100
        assert res["coverage_percentage"] == 0.0
        assert res["model_version"] is None

    @patch("src.analytics.predictive_analytics.get_cursor")
    def test_coverage_with_model_version_filter(self, mock_get_cursor: MagicMock) -> None:
        mock_cur = MagicMock()
        mock_cur.fetchone.side_effect = [(100,), (80,)]
        mock_get_cursor.return_value.__enter__.return_value = mock_cur

        res = get_prediction_coverage(model_version=" v1.0 ")
        assert res["total_applications"] == 100
        assert res["applications_with_predictions"] == 80
        assert res["applications_without_predictions"] == 20
        assert res["coverage_percentage"] == 80.0
        assert res["model_version"] == "v1.0"
        # Verify parameterized query passed model_version
        assert mock_cur.execute.call_count == 2
        mock_cur.execute.assert_called_with(
            "SELECT COUNT(DISTINCT application_id) FROM application_predictions WHERE model_version = %s;",
            ("v1.0",),
        )

    @patch("src.analytics.predictive_analytics.get_cursor")
    def test_risk_distribution_mocked(self, mock_get_cursor: MagicMock) -> None:
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = [(0, "Low Risk", 60), (1, "High Risk", 40)]
        mock_get_cursor.return_value.__enter__.return_value = mock_cur

        res = get_risk_distribution()
        assert len(res) == 2
        assert res[0]["predicted_risk_class"] == 0
        assert res[0]["predicted_risk_label"] == "Low Risk"
        assert res[0]["count"] == 60
        assert res[0]["percentage"] == 60.0
        assert res[1]["predicted_risk_class"] == 1
        assert res[1]["count"] == 40
        assert res[1]["percentage"] == 40.0

    @patch("src.analytics.predictive_analytics.get_cursor")
    def test_probability_bands_structure_and_boundaries(self, mock_get_cursor: MagicMock) -> None:
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = [
            ("0.0 - 0.2", 10),
            ("0.2 - 0.4", 20),
            ("0.4 - 0.6", 30),
            ("0.6 - 0.8", 30),
            ("0.8 - 1.0", 10),
        ]
        mock_get_cursor.return_value.__enter__.return_value = mock_cur

        res = get_risk_probability_bands()
        assert len(res) == 5
        expected_bands = ["0.0 - 0.2", "0.2 - 0.4", "0.4 - 0.6", "0.6 - 0.8", "0.8 - 1.0"]
        for idx, item in enumerate(res):
            assert item["probability_band"] == expected_bands[idx]
            assert isinstance(item["count"], int)
            assert isinstance(item["percentage"], float)
        assert res[0]["count"] == 10
        assert res[0]["percentage"] == 10.0

    @patch("src.analytics.predictive_analytics.get_cursor")
    def test_probability_bands_missing_bands_are_zero_filled(self, mock_get_cursor: MagicMock) -> None:
        mock_cur = MagicMock()
        # DB only returns rows for 2 bands
        mock_cur.fetchall.return_value = [
            ("0.4 - 0.6", 50),
            ("0.6 - 0.8", 50),
        ]
        mock_get_cursor.return_value.__enter__.return_value = mock_cur

        res = get_risk_probability_bands()
        assert len(res) == 5
        assert res[0]["probability_band"] == "0.0 - 0.2"
        assert res[0]["count"] == 0
        assert res[0]["percentage"] == 0.0
        assert res[2]["probability_band"] == "0.4 - 0.6"
        assert res[2]["count"] == 50
        assert res[2]["percentage"] == 50.0

    @patch("src.analytics.predictive_analytics.get_cursor")
    def test_predicted_processing_time_empty_population(self, mock_get_cursor: MagicMock) -> None:
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (0, None, None, None, None)
        mock_get_cursor.return_value.__enter__.return_value = mock_cur

        res = get_predicted_processing_time_summary(model_version="v2.0")
        assert res["count"] == 0
        assert res["mean_days"] == 0.0
        assert res["median_days"] == 0.0
        assert res["min_days"] == 0.0
        assert res["max_days"] == 0.0
        assert res["model_version"] == "v2.0"

    @patch("src.analytics.predictive_analytics.get_cursor")
    def test_prediction_error_empty_retrospective_population(self, mock_get_cursor: MagicMock) -> None:
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (0, None, None, None)
        mock_get_cursor.return_value.__enter__.return_value = mock_cur

        res = get_prediction_error_summary()
        assert res["evaluated_count"] == 0
        assert res["mae_days"] == 0.0
        assert res["rmse_days"] == 0.0
        assert res["mean_error_days"] == 0.0
        assert res["model_version"] is None

    @patch("src.analytics.predictive_analytics.get_cursor")
    def test_high_risk_applications_ordering_and_params(self, mock_get_cursor: MagicMock) -> None:
        now_dt = datetime.now(timezone.utc)
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = [
            ("App_200", "New credit", "Car", 15000.0, "None", 1, "High Risk", 0.85, 22.5, "v1.0", now_dt),
            ("App_100", "New credit", "Home", 25000.0, "None", 1, "High Risk", 0.75, 19.2, "v1.0", now_dt),
        ]
        mock_get_cursor.return_value.__enter__.return_value = mock_cur

        res = get_high_risk_applications(min_probability=0.7, limit=10, model_version="v1.0")
        assert len(res) == 2
        assert res[0]["application_id"] == "App_200"
        assert res[0]["predicted_risk_probability"] == 0.85
        assert res[1]["application_id"] == "App_100"
        assert res[1]["predicted_risk_probability"] == 0.75
        mock_cur.execute.assert_called_once()
        # Verify query parameters passed to execute
        query_arg, params_arg = mock_cur.execute.call_args[0]
        assert "WHERE predicted_risk_probability >= %s" in query_arg
        assert "ORDER BY predicted_risk_probability DESC, application_id ASC" in query_arg
        assert params_arg == (0.7, "v1.0", 10)


class TestPredictiveAnalyticsLiveDBIntegration:
    """Integration tests running read-only queries against live PostgreSQL DB."""

    def test_live_prediction_coverage(self, db_available: bool) -> None:
        if not db_available:
            pytest.skip("PostgreSQL database not available")

        cov = get_prediction_coverage()
        assert cov["total_applications"] == 31509
        assert cov["applications_with_predictions"] == 31509
        assert cov["applications_without_predictions"] == 0
        assert cov["coverage_percentage"] == 100.0

        cov_v1 = get_prediction_coverage(model_version="v1.0")
        assert cov_v1["applications_with_predictions"] == 31509
        assert cov_v1["model_version"] == "v1.0"

        cov_v9 = get_prediction_coverage(model_version="v9.99")
        assert cov_v9["applications_with_predictions"] == 0
        assert cov_v9["coverage_percentage"] == 0.0

    def test_live_risk_distribution(self, db_available: bool) -> None:
        if not db_available:
            pytest.skip("PostgreSQL database not available")

        dist = get_risk_distribution()
        assert isinstance(dist, list)
        assert len(dist) > 0
        total_count = sum(item["count"] for item in dist)
        assert total_count == 31509
        total_pct = sum(item["percentage"] for item in dist)
        assert pytest.approx(total_pct, abs=0.1) == 100.0

    def test_live_risk_probability_bands(self, db_available: bool) -> None:
        if not db_available:
            pytest.skip("PostgreSQL database not available")

        bands = get_risk_probability_bands()
        assert len(bands) == 5
        band_names = [b["probability_band"] for b in bands]
        assert band_names == ["0.0 - 0.2", "0.2 - 0.4", "0.4 - 0.6", "0.6 - 0.8", "0.8 - 1.0"]
        total_count = sum(b["count"] for b in bands)
        assert total_count == 31509

    def test_live_predicted_processing_time_summary(self, db_available: bool) -> None:
        if not db_available:
            pytest.skip("PostgreSQL database not available")

        summary = get_predicted_processing_time_summary()
        assert summary["count"] == 31509
        assert summary["mean_days"] > 0.0
        assert summary["median_days"] > 0.0
        assert summary["min_days"] >= 0.0
        assert summary["max_days"] >= summary["min_days"]

    def test_live_prediction_error_summary(self, db_available: bool) -> None:
        if not db_available:
            pytest.skip("PostgreSQL database not available")

        err_summary = get_prediction_error_summary()
        assert err_summary["evaluated_count"] > 0
        assert err_summary["mae_days"] >= 0.0
        assert err_summary["rmse_days"] >= err_summary["mae_days"]

    def test_live_high_risk_applications(self, db_available: bool) -> None:
        if not db_available:
            pytest.skip("PostgreSQL database not available")

        high_risk = get_high_risk_applications(min_probability=0.5, limit=5)
        assert isinstance(high_risk, list)
        assert len(high_risk) <= 5
        if high_risk:
            # Check deterministic tie-break ordering: descending probability, ascending application_id
            for i in range(len(high_risk) - 1):
                prob1 = high_risk[i]["predicted_risk_probability"]
                prob2 = high_risk[i + 1]["predicted_risk_probability"]
                assert prob1 >= prob2
                if prob1 == prob2:
                    assert high_risk[i]["application_id"] < high_risk[i + 1]["application_id"]
