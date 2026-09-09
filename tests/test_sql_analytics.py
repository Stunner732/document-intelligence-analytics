"""Tests for Phase 5 SQL Analytics Views."""

import pytest
from pathlib import Path
from contextlib import contextmanager


class TestAnalyticsViewsExistence:
    """Test that all Phase 5 analytics views exist."""

    def test_view_application_metrics_exists(self):
        """view_application_metrics should exist."""
        from src.analytics.views import view_exists
        assert view_exists('view_application_metrics')

    def test_view_daily_throughput_exists(self):
        """view_daily_throughput should exist."""
        from src.analytics.views import view_exists
        assert view_exists('view_daily_throughput')

    def test_view_activity_summary_exists(self):
        """view_activity_summary should exist."""
        from src.analytics.views import view_exists
        assert view_exists('view_activity_summary')

    def test_view_resource_workload_exists(self):
        """view_resource_workload should exist."""
        from src.analytics.views import view_exists
        assert view_exists('view_resource_workload')

    def test_view_application_type_metrics_exists(self):
        """view_application_type_metrics should exist."""
        from src.analytics.views import view_exists
        assert view_exists('view_application_type_metrics')

    def test_view_loan_goal_metrics_exists(self):
        """view_loan_goal_metrics should exist."""
        from src.analytics.views import view_exists
        assert view_exists('view_loan_goal_metrics')

    def test_view_lifecycle_transition_metrics_exists(self):
        """view_lifecycle_transition_metrics should exist."""
        from src.analytics.views import view_exists
        assert view_exists('view_lifecycle_transition_metrics')

    def test_view_event_origin_metrics_exists(self):
        """view_event_origin_metrics should exist."""
        from src.analytics.views import view_exists
        assert view_exists('view_event_origin_metrics')

    def test_view_monthly_summary_exists(self):
        """view_monthly_summary should exist."""
        from src.analytics.views import view_exists
        assert view_exists('view_monthly_summary')

    def test_view_weekly_summary_exists(self):
        """view_weekly_summary should exist."""
        from src.analytics.views import view_exists
        assert view_exists('view_weekly_summary')

    def test_view_event_sequence_exists(self):
        """view_event_sequence should exist."""
        from src.analytics.views import view_exists
        assert view_exists('view_event_sequence')

    def test_view_processing_time_buckets_exists(self):
        """view_processing_time_buckets should exist."""
        from src.analytics.views import view_exists
        assert view_exists('view_processing_time_buckets')

    def test_view_offer_analysis_exists(self):
        """view_offer_analysis should exist."""
        from src.analytics.views import view_exists
        assert view_exists('view_offer_analysis')


class TestMaterializedViewsExistence:
    """Test that all Phase 5 materialized views exist."""

    def test_mv_activity_summary_exists(self):
        """mv_activity_summary should exist."""
        from src.analytics.views import materialized_view_exists
        assert materialized_view_exists('mv_activity_summary')

    def test_mv_resource_workload_exists(self):
        """mv_resource_workload should exist."""
        from src.analytics.views import materialized_view_exists
        assert materialized_view_exists('mv_resource_workload')

    def test_mv_monthly_summary_exists(self):
        """mv_monthly_summary should exist."""
        from src.analytics.views import materialized_view_exists
        assert materialized_view_exists('mv_monthly_summary')

    def test_mv_application_type_summary_exists(self):
        """mv_application_type_summary should exist."""
        from src.analytics.views import materialized_view_exists
        assert materialized_view_exists('mv_application_type_summary')


class TestViewColumnStructure:
    """Test that views have expected columns."""

    def test_application_metrics_columns(self):
        """view_application_metrics should have expected columns."""
        from src.database import get_cursor
        with get_cursor() as cur:
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = 'view_application_metrics'
                ORDER BY ordinal_position
            """)
            columns = [row[0] for row in cur.fetchall()]
            expected = ['application_id', 'application_type', 'loan_goal',
                       'requested_amount', 'event_count', 'first_event_time',
                       'last_event_time', 'processing_hours', 'processing_days',
                       'complete_count', 'suspend_count', 'withdraw_count',
                       'workflow_activity_count', 'offer_activity_count',
                       'application_activity_count', 'first_date', 'first_year',
                       'first_month', 'first_week']
            for col in expected:
                assert col in columns, f"Missing column: {col}"

    def test_daily_throughput_columns(self):
        """view_daily_throughput should have expected columns."""
        from src.database import get_cursor
        with get_cursor() as cur:
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = 'view_daily_throughput'
                ORDER BY ordinal_position
            """)
            columns = [row[0] for row in cur.fetchall()]
            expected = ['date', 'applications_started', 'total_events']
            for col in expected:
                assert col in columns, f"Missing column: {col}"

    def test_activity_summary_columns(self):
        """view_activity_summary should have expected columns."""
        from src.database import get_cursor
        with get_cursor() as cur:
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = 'view_activity_summary'
                ORDER BY ordinal_position
            """)
            columns = [row[0] for row in cur.fetchall()]
            expected = ['activity', 'event_count', 'unique_applications',
                       'percentage_of_total', 'activity_type', 'complete_pct',
                       'suspend_pct', 'withdraw_pct']
            for col in expected:
                assert col in columns, f"Missing column: {col}"


class TestViewDataIntegrity:
    """Test that views return valid data."""

    def test_application_metrics_row_count(self):
        """view_application_metrics should match application count."""
        from src.database import get_cursor
        with get_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM applications")
            app_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM view_application_metrics")
            view_count = cur.fetchone()[0]
            assert view_count == app_count, (
                f"View row count ({view_count}) != application count ({app_count})"
            )

    def test_activity_summary_total_percentage(self):
        """Activity summary percentages should sum to ~100%."""
        from src.database import get_cursor
        with get_cursor() as cur:
            cur.execute("SELECT SUM(percentage_of_total) FROM view_activity_summary")
            total_pct = cur.fetchone()[0]
            assert 99.9 <= total_pct <= 100.1, (
                f"Activity percentages sum to {total_pct}, expected ~100"
            )

    def test_daily_throughput_has_data(self):
        """Daily throughput should have at least one row."""
        from src.database import get_cursor
        with get_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM view_daily_throughput")
            count = cur.fetchone()[0]
            assert count > 0, "Daily throughput view has no data"

    def test_resource_workload_sum(self):
        """Resource workload percentages should sum to ~100%."""
        from src.database import get_cursor
        with get_cursor() as cur:
            cur.execute("""
                SELECT SUM(workload_percentage) FROM view_resource_workload
            """)
            total_pct = cur.fetchone()[0]
            assert 99.9 <= total_pct <= 100.1, (
                f"Resource percentages sum to {total_pct}, expected ~100"
            )

    def test_processing_time_buckets_sum(self):
        """Processing time bucket percentages should sum to ~100%."""
        from src.database import get_cursor
        with get_cursor() as cur:
            cur.execute("SELECT SUM(percentage) FROM view_processing_time_buckets")
            total_pct = cur.fetchone()[0]
            assert 99.9 <= total_pct <= 100.1, (
                f"Time bucket percentages sum to {total_pct}, expected ~100"
            )


class TestMaterializedViewRefresh:
    """Test materialized view refresh functionality."""

    def test_refresh_materialized_views(self):
        """Materialized views should refresh without error."""
        from src.analytics.views import refresh_materialized_views
        refreshed = refresh_materialized_views()
        assert len(refreshed) == 4, (
            f"Expected 4 views refreshed, got {len(refreshed)}"
        )
        expected = [
            'mv_activity_summary',
            'mv_resource_workload',
            'mv_monthly_summary',
            'mv_application_type_summary',
        ]
        for view in expected:
            assert view in refreshed, f"View {view} not refreshed"

    def test_mv_application_type_summary_row_count(self):
        """mv_application_type_summary should have 2 rows (New credit, Limit raise)."""
        from src.database import get_cursor
        with get_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM mv_application_type_summary")
            count = cur.fetchone()[0]
            assert count == 2, f"Application type summary has {count} rows, expected 2"


class TestAnalyticsModuleFunctions:
    """Test the analytics module functions."""

    def test_get_all_views(self):
        """get_all_views should return expected views."""
        from src.analytics.views import get_all_views
        views = get_all_views()
        assert len(views) >= 13, f"Expected at least 13 views, got {len(views)}"

    def test_get_all_materialized_views(self):
        """get_all_materialized_views should return expected views."""
        from src.analytics.views import get_all_materialized_views
        views = get_all_materialized_views()
        assert len(views) == 4, f"Expected 4 materialized views, got {len(views)}"

    def test_run_analytics_queries(self):
        """run_analytics_queries should return valid results."""
        from src.analytics.views import run_analytics_queries
        results = run_analytics_queries()
        assert 'total_applications' in results
        assert 'total_events' in results
        assert 'top_activities' in results
        assert 'processing_time_buckets' in results


class TestSQLMigrationFile:
    """Test the SQL migration file."""

    def test_migration_file_exists(self):
        """002_analytics_views.sql should exist."""
        migration_file = Path(__file__).parent.parent / "sql" / "002_analytics_views.sql"
        assert migration_file.exists(), f"Migration file not found: {migration_file}"

    def test_migration_has_create_views(self):
        """Migration should contain CREATE VIEW statements."""
        migration_file = Path(__file__).parent.parent / "sql" / "002_analytics_views.sql"
        content = migration_file.read_text(encoding="utf-8")
        assert "CREATE OR REPLACE VIEW" in content
        assert "CREATE MATERIALIZED VIEW" in content

    def test_migration_records_version(self):
        """Migration should record version in schema_versions."""
        migration_file = Path(__file__).parent.parent / "sql" / "002_analytics_views.sql"
        content = migration_file.read_text(encoding="utf-8")
        assert "schema_versions" in content
        assert "INSERT INTO schema_versions" in content