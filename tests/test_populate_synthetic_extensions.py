"""Integration tests for database population of synthetic operational extensions."""

from __future__ import annotations

import pytest

from scripts.populate_synthetic_extensions import populate_synthetic_extensions
from src.database import check_database_connection, get_connection


@pytest.fixture(scope="module")
def db_available() -> bool:
    return check_database_connection()


class TestPopulateSyntheticExtensions:
    """Integration and idempotency tests for synthetic extensions population."""

    def test_database_population_counts_and_integrity(self, db_available: bool) -> None:
        if not db_available:
            pytest.skip("PostgreSQL database not available")

        # Execute population
        exit_code = populate_synthetic_extensions(seed=42, batch_size=1000, dry_run=False)
        assert exit_code == 0

        with get_connection() as conn:
            with conn.cursor() as cur:
                # 1. Total count check
                cur.execute("SELECT COUNT(*) FROM synthetic_extensions;")
                synth_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM applications;")
                app_count = cur.fetchone()[0]

                assert app_count == 31509
                assert synth_count == 31509

                # 2. Referential integrity check (zero orphans)
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM synthetic_extensions s
                    LEFT JOIN applications a ON s.application_id = a.application_id
                    WHERE a.application_id IS NULL;
                    """
                )
                orphan_count = cur.fetchone()[0]
                assert orphan_count == 0

                # 3. Priority check constraint check
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM synthetic_extensions
                    WHERE priority NOT IN ('low', 'normal', 'high', 'urgent');
                    """
                )
                invalid_priority_count = cur.fetchone()[0]
                assert invalid_priority_count == 0

                # 4. Quality score bounds check
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM synthetic_extensions
                    WHERE quality_score < 65.00 OR quality_score > 100.00;
                    """
                )
                invalid_quality_count = cur.fetchone()[0]
                assert invalid_quality_count == 0

    def test_population_idempotency(self, db_available: bool) -> None:
        if not db_available:
            pytest.skip("PostgreSQL database not available")

        # Rerun population script a second time with same seed
        exit_code = populate_synthetic_extensions(seed=42, batch_size=1000, dry_run=False)
        assert exit_code == 0

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM synthetic_extensions;")
                synth_count = cur.fetchone()[0]
                assert synth_count == 31509

    def test_data_loads_audit_logging(self, db_available: bool) -> None:
        if not db_available:
            pytest.skip("PostgreSQL database not available")

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT load_type, records_loaded, load_status
                    FROM data_loads
                    WHERE load_type = 'synthetic_extension'
                    ORDER BY completed_at DESC
                    LIMIT 1;
                    """
                )
                row = cur.fetchone()
                assert row is not None
                load_type, records_loaded, load_status = row
                assert load_type == "synthetic_extension"
                assert records_loaded == 31509
                assert load_status == "SUCCESS"
