"""Tests for Phase 9 Predictive SLA Risk Schema & Views."""

from pathlib import Path
import pytest
from src.database import get_cursor, table_exists


class TestPredictiveSchemaExistence:
    """Test table and view existence for Phase 9."""

    def test_application_predictions_table_exists(self):
        """application_predictions table should exist."""
        assert table_exists("application_predictions")

    def test_view_predictive_sla_risk_exists(self):
        """view_predictive_sla_risk historical view should exist."""
        with get_cursor() as cur:
            cur.execute(
                "SELECT EXISTS (SELECT FROM information_schema.views WHERE table_schema = 'public' AND table_name = 'view_predictive_sla_risk')"
            )
            assert cur.fetchone()[0] is True

    def test_view_predictive_sla_risk_latest_exists(self):
        """view_predictive_sla_risk_latest single-row view should exist."""
        with get_cursor() as cur:
            cur.execute(
                "SELECT EXISTS (SELECT FROM information_schema.views WHERE table_schema = 'public' AND table_name = 'view_predictive_sla_risk_latest')"
            )
            assert cur.fetchone()[0] is True

    def test_schema_version_003_registered(self):
        """schema_versions should record version 003."""
        with get_cursor() as cur:
            cur.execute("SELECT description FROM schema_versions WHERE version = '003'")
            row = cur.fetchone()
            assert row is not None
            assert "Phase 9" in row[0]


class TestPredictiveTableStructure:
    """Test column definitions, PKs, and constraints for application_predictions."""

    def test_application_predictions_columns(self):
        """Verify column structure of application_predictions."""
        with get_cursor() as cur:
            cur.execute(
                "SELECT column_name, is_nullable FROM information_schema.columns WHERE table_name = 'application_predictions'"
            )
            cols = {row[0]: row[1] for row in cur.fetchall()}

        expected = [
            "application_id",
            "model_version",
            "model_type",
            "risk_class",
            "risk_probability",
            "predicted_processing_days",
            "scored_at",
            "created_at",
            "updated_at",
        ]
        for col in expected:
            assert col in cols, f"Column {col} missing from application_predictions"
            assert cols[col] == "NO", f"Column {col} should be NOT NULL"

    def test_composite_primary_key(self):
        """Verify (application_id, model_version) composite primary key."""
        with get_cursor() as cur:
            cur.execute(
                """
                SELECT kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                WHERE tc.constraint_type = 'PRIMARY KEY'
                  AND tc.table_name = 'application_predictions'
                ORDER BY kcu.ordinal_position;
                """
            )
            pk_cols = [row[0] for row in cur.fetchall()]

        assert pk_cols == ["application_id", "model_version"]


class TestPredictiveConstraintsAndGrain:
    """Test SQL constraints, UPSERT, and view grain using test transaction context."""

    def test_invalid_risk_class_rejected(self):
        """risk_class outside {0, 1} should trigger check constraint violation."""
        with pytest.raises(Exception):
            with get_cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO application_predictions (
                        application_id, model_version, model_type, risk_class, risk_probability, predicted_processing_days
                    ) VALUES ('TEST_APP_01', 'v1.0', 'HistGradientBoosting', 2, 0.5000, 10.00);
                    """
                )

    def test_invalid_probability_rejected(self):
        """risk_probability outside [0, 1] should trigger check constraint violation."""
        with pytest.raises(Exception):
            with get_cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO application_predictions (
                        application_id, model_version, model_type, risk_class, risk_probability, predicted_processing_days
                    ) VALUES ('TEST_APP_01', 'v1.0', 'HistGradientBoosting', 1, 1.5000, 10.00);
                    """
                )

    def test_negative_predicted_days_rejected(self):
        """negative predicted_processing_days should trigger check constraint violation."""
        with pytest.raises(Exception):
            with get_cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO application_predictions (
                        application_id, model_version, model_type, risk_class, risk_probability, predicted_processing_days
                    ) VALUES ('TEST_APP_01', 'v1.0', 'HistGradientBoosting', 1, 0.8000, -5.00);
                    """
                )

    def test_historical_and_latest_view_grain(self):
        """Test multi-version historical preservation and single-row latest view grain."""
        with get_cursor() as cur:
            cur.execute("SELECT application_id FROM applications LIMIT 1")
            row = cur.fetchone()
            if not row:
                pytest.skip("No applications in database to test views.")
            app_id = row[0]

            # Insert prediction for v1.0
            cur.execute(
                """
                INSERT INTO application_predictions (
                    application_id, model_version, model_type, risk_class, risk_probability, predicted_processing_days, scored_at
                ) VALUES (%s, 'test_v1.0', 'HistGradientBoosting', 0, 0.2500, 12.50, NOW() - INTERVAL '1 day')
                ON CONFLICT (application_id, model_version) DO UPDATE SET
                    risk_probability = EXCLUDED.risk_probability;
                """,
                (app_id,),
            )

            # Insert prediction for v2.0
            cur.execute(
                """
                INSERT INTO application_predictions (
                    application_id, model_version, model_type, risk_class, risk_probability, predicted_processing_days, scored_at
                ) VALUES (%s, 'test_v2.0', 'HistGradientBoosting', 1, 0.7500, 18.00, NOW())
                ON CONFLICT (application_id, model_version) DO UPDATE SET
                    risk_probability = EXCLUDED.risk_probability;
                """,
                (app_id,),
            )

            # Historical view should have 2 rows for this application
            cur.execute(
                "SELECT COUNT(*) FROM view_predictive_sla_risk WHERE application_id = %s",
                (app_id,),
            )
            hist_count = cur.fetchone()[0]
            assert hist_count >= 2

            # Latest view should have EXACTLY 1 row for this application (test_v2.0)
            cur.execute(
                "SELECT model_version, predicted_risk_class, predicted_risk_probability FROM view_predictive_sla_risk_latest WHERE application_id = %s",
                (app_id,),
            )
            latest_rows = cur.fetchall()
            assert len(latest_rows) == 1
            assert latest_rows[0][0] == "test_v2.0"
            assert latest_rows[0][1] == 1
            assert float(latest_rows[0][2]) == 0.7500

            # Cleanup test records
            cur.execute(
                "DELETE FROM application_predictions WHERE application_id = %s AND model_version LIKE 'test_v%%'",
                (app_id,),
            )
            cur.connection.commit()

    def test_processing_days_error_handling_for_incomplete(self):
        """processing_days_error should be calculated accurately for completed cases."""
        with get_cursor() as cur:
            cur.execute("SELECT application_id FROM applications LIMIT 1")
            row = cur.fetchone()
            if not row:
                pytest.skip("No applications in database to test views.")
            app_id = row[0]

            cur.execute(
                """
                INSERT INTO application_predictions (
                    application_id, model_version, model_type, risk_class, risk_probability, predicted_processing_days
                ) VALUES (%s, 'test_v_err', 'HistGradientBoosting', 0, 0.3000, 10.00)
                ON CONFLICT (application_id, model_version) DO UPDATE SET
                    risk_probability = EXCLUDED.risk_probability;
                """,
                (app_id,),
            )

            cur.execute(
                """
                SELECT v.application_id, v.processing_days_error, v.actual_processing_days, v.predicted_processing_days, m.complete_count
                FROM view_predictive_sla_risk v
                JOIN view_application_metrics m ON v.application_id = m.application_id
                WHERE v.application_id = %s AND v.model_version = 'test_v_err';
                """,
                (app_id,),
            )
            row = cur.fetchone()
            assert row is not None
            app_id_res, err, actual_days, pred_days, comp_count = row
            if comp_count > 0 and actual_days is not None:
                expected_err = round(float(actual_days) - float(pred_days), 2)
                assert float(err) == expected_err, f"Expected processing_days_error {expected_err}, got {err}"
            else:
                assert err is None, f"processing_days_error should be NULL for incomplete application {app_id_res}"

            # Cleanup
            cur.execute(
                "DELETE FROM application_predictions WHERE application_id = %s AND model_version = 'test_v_err'",
                (app_id,),
            )
            cur.connection.commit()
