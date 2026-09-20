"""Tests for Phase 9.3 Batch Prediction Materialization Script."""

from pathlib import Path
import pytest
import pandas as pd

from scripts.populate_predictive_scores import (
    PredictionRecord,
    generate_validated_predictions,
    populate_predictive_scores,
)
from src.database import check_database_connection, get_cursor
from src.ml.sla_predictor import SLARiskPredictor

DEFAULT_MODEL_PATH = Path("models/sla_predictor.joblib")


@pytest.fixture(scope="module")
def db_available() -> bool:
    return check_database_connection()


@pytest.fixture(scope="module")
def loaded_predictor() -> SLARiskPredictor:
    if not DEFAULT_MODEL_PATH.exists():
        pytest.skip(f"Model artifact not found at {DEFAULT_MODEL_PATH}")
    return SLARiskPredictor.load(DEFAULT_MODEL_PATH)


class TestPredictionRecordValidation:
    """Test unit validation logic in PredictionRecord."""

    def test_valid_record_passes(self):
        rec = PredictionRecord(
            application_id="APP_01",
            model_version="v1.0",
            model_type="HistGradientBoosting",
            risk_class=1,
            risk_probability=0.7500,
            predicted_processing_days=14.50,
        )
        rec.validate()  # Should not raise exception

    def test_empty_model_version_raises(self):
        rec = PredictionRecord("APP_01", "", "HistGradientBoosting", 1, 0.50, 10.0)
        with pytest.raises(ValueError, match="model_version"):
            rec.validate()

    def test_invalid_risk_class_raises(self):
        rec = PredictionRecord("APP_01", "v1.0", "HistGradientBoosting", 2, 0.50, 10.0)
        with pytest.raises(ValueError, match="risk_class"):
            rec.validate()

    def test_invalid_probability_raises(self):
        rec = PredictionRecord("APP_01", "v1.0", "HistGradientBoosting", 0, 1.50, 10.0)
        with pytest.raises(ValueError, match="risk_probability"):
            rec.validate()

    def test_negative_predicted_days_raises(self):
        rec = PredictionRecord("APP_01", "v1.0", "HistGradientBoosting", 0, 0.50, -2.5)
        with pytest.raises(ValueError, match="predicted_processing_days"):
            rec.validate()


class TestGenerateValidatedPredictions:
    """Test batch feature transformation and validation."""

    def test_valid_dataframe_transformation(self, loaded_predictor: SLARiskPredictor):
        sample_df = pd.DataFrame([
            {
                "application_id": "TEST_APP_001",
                "application_type": "New credit",
                "loan_goal": "Home improvement",
                "requested_amount": 15000.0,
                "submission_hour": 10,
                "submission_day_of_week": 1,
                "submission_month": 5,
                "is_weekend": 0,
                "document_type": "Tax return",
                "page_count": 3,
                "branch": "Branch_A",
                "operator_team": "Team_1",
                "priority": "normal",
                "sla_target_hours": 48,
                "region": "North",
                "channel": "Online",
                "quality_score": 85.0,
            }
        ])

        valid_records, skipped = generate_validated_predictions(
            sample_df, loaded_predictor, model_version="v1.0"
        )
        assert len(valid_records) == 1
        assert len(skipped) == 0
        assert valid_records[0].application_id == "TEST_APP_001"
        assert valid_records[0].risk_class in (0, 1)
        assert 0.0 <= valid_records[0].risk_probability <= 1.0
        assert valid_records[0].predicted_processing_days >= 0.0

    def test_missing_required_features_raises_error(self, loaded_predictor: SLARiskPredictor):
        invalid_df = pd.DataFrame([{"application_id": "APP_BAD"}])
        with pytest.raises(ValueError, match="missing required columns"):
            generate_validated_predictions(invalid_df, loaded_predictor, model_version="v1.0")

    def test_duplicate_application_id_deduplication(self, loaded_predictor: SLARiskPredictor):
        dup_df = pd.DataFrame([
            {
                "application_id": "TEST_DUP_01",
                "application_type": "New credit",
                "loan_goal": "Home improvement",
                "requested_amount": 10000.0,
                "submission_hour": 9,
                "submission_day_of_week": 0,
                "submission_month": 1,
                "is_weekend": 0,
                "document_type": "Tax return",
                "page_count": 2,
                "branch": "Branch_A",
                "operator_team": "Team_1",
                "priority": "normal",
                "sla_target_hours": 48,
                "region": "North",
                "channel": "Online",
                "quality_score": 90.0,
            },
            {
                "application_id": "TEST_DUP_01",  # Duplicate ID
                "application_type": "New credit",
                "loan_goal": "Home improvement",
                "requested_amount": 10000.0,
                "submission_hour": 9,
                "submission_day_of_week": 0,
                "submission_month": 1,
                "is_weekend": 0,
                "document_type": "Tax return",
                "page_count": 2,
                "branch": "Branch_A",
                "operator_team": "Team_1",
                "priority": "normal",
                "sla_target_hours": 48,
                "region": "North",
                "channel": "Online",
                "quality_score": 90.0,
            },
        ])

        valid_records, skipped = generate_validated_predictions(
            dup_df, loaded_predictor, model_version="v1.0"
        )
        assert len(valid_records) == 1
        assert len(skipped) == 1
        assert skipped[0]["application_id"] == "TEST_DUP_01"


class TestPopulatePredictiveScoresScript:
    """Integration and dry-run tests for batch scoring script."""

    def test_missing_model_version_returns_error(self):
        exit_code = populate_predictive_scores(model_version="")
        assert exit_code == 1

    def test_dry_run_performs_no_writes(self, db_available: bool):
        if not db_available:
            pytest.skip("Database not available")

        # Initial row count
        with get_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM application_predictions;")
            initial_count = cur.fetchone()[0]

        # Dry run execution with limit=5
        exit_code = populate_predictive_scores(
            model_version="test_dry_v1", limit=5, dry_run=True
        )
        assert exit_code == 0

        # Verify zero rows written
        with get_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM application_predictions;")
            final_count = cur.fetchone()[0]
            assert final_count == initial_count

    def test_upsert_idempotency_and_version_preservation(self, db_available: bool):
        if not db_available:
            pytest.skip("Database not available")

        with get_cursor() as cur:
            cur.execute("SELECT application_id FROM applications LIMIT 1")
            row = cur.fetchone()
            if not row:
                pytest.skip("No applications in database to test script.")
            app_id = row[0]

        # Score limit=1 under version test_script_v1
        exit_code = populate_predictive_scores(
            model_version="test_script_v1", limit=1, dry_run=False
        )
        assert exit_code == 0

        with get_cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM application_predictions WHERE model_version = 'test_script_v1';"
            )
            v1_count = cur.fetchone()[0]
            assert v1_count == 1

        # Rerun same version to test UPSERT idempotency
        exit_code_rerun = populate_predictive_scores(
            model_version="test_script_v1", limit=1, dry_run=False
        )
        assert exit_code_rerun == 0

        with get_cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM application_predictions WHERE model_version = 'test_script_v1';"
            )
            v1_count_rerun = cur.fetchone()[0]
            assert v1_count_rerun == 1  # No duplicate rows created

        # Score under new model version test_script_v2
        exit_code_v2 = populate_predictive_scores(
            model_version="test_script_v2", limit=1, dry_run=False
        )
        assert exit_code_v2 == 0

        with get_cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM application_predictions WHERE model_version = 'test_script_v2';"
            )
            v2_count = cur.fetchone()[0]
            assert v2_count == 1

            # Verify v1 is preserved
            cur.execute(
                "SELECT COUNT(*) FROM application_predictions WHERE model_version = 'test_script_v1';"
            )
            assert cur.fetchone()[0] == 1

            # Cleanup test script predictions
            cur.execute(
                "DELETE FROM application_predictions WHERE model_version LIKE 'test_script_v%';"
            )
            cur.connection.commit()
