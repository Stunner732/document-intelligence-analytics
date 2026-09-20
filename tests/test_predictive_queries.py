"""Unit tests for Predictive Analytics Query Layer."""

from __future__ import annotations

import pytest

from src.analytics.predictive_queries import (
    get_application_features_for_inference,
    predict_application_risk,
    predict_batch_risk,
)
from src.database import check_database_connection


@pytest.fixture(scope="module")
def db_available() -> bool:
    return check_database_connection()


class TestPredictiveQueries:
    """Tests for predictive query functions."""

    def test_get_application_features_for_inference(self, db_available: bool) -> None:
        if not db_available:
            pytest.skip("PostgreSQL database not available")

        app_id = "Application_1000086665"
        features_df = get_application_features_for_inference(app_id)

        assert len(features_df) == 1
        assert "requested_amount" in features_df.columns
        assert "application_type" in features_df.columns
        assert "loan_goal" in features_df.columns

    def test_predict_application_risk(self, db_available: bool) -> None:
        if not db_available:
            pytest.skip("PostgreSQL database not available")

        app_id = "Application_1000086665"
        pred = predict_application_risk(app_id)

        assert pred["application_id"] == app_id
        assert pred["sla_risk_class"] in (0, 1)
        assert pred["sla_risk_label"] in ("Low Risk", "High Risk")
        assert 0.0 <= pred["sla_breach_probability"] <= 1.0
        assert pred["predicted_processing_days"] >= 0.0

    def test_predict_batch_risk(self, db_available: bool) -> None:
        if not db_available:
            pytest.skip("PostgreSQL database not available")

        app_ids = ["Application_1000086665", "Application_1000158214"]
        results = predict_batch_risk(app_ids)

        assert len(results) == 2
        for res in results:
            assert res["status"] == "SUCCESS"
            assert "sla_risk_class" in res
            assert 0.0 <= res["sla_breach_probability"] <= 1.0

    def test_invalid_application_id_raises_error(self, db_available: bool) -> None:
        if not db_available:
            pytest.skip("PostgreSQL database not available")

        with pytest.raises(ValueError):
            predict_application_risk("INVALID_APP_ID_999999")
