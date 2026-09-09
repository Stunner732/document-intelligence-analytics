"""SQL Analytics Views Module

This module provides utilities for managing analytical views and materialized
views for Phase 5 SQL Analytics.

Views created:
- view_application_metrics: Per-application processing metrics
- view_daily_throughput: Daily application and event volume
- view_activity_summary: Activity frequency and distribution
- view_resource_workload: Resource (user) utilization
- view_application_type_metrics: Metrics by application type
- view_loan_goal_metrics: Metrics by loan goal
- view_lifecycle_transition_metrics: Lifecycle transition analysis
- view_event_origin_metrics: Metrics by event origin
- view_monthly_summary: Monthly aggregated metrics
- view_weekly_summary: Weekly aggregated metrics
- view_event_sequence: Event sequence per application
- view_processing_time_buckets: Applications by processing time bucket
- view_offer_analysis: Offer-related metrics

Materialized Views:
- mv_daily_throughput: Pre-computed daily metrics
- mv_activity_summary: Pre-computed activity counts
- mv_resource_workload: Pre-computed resource metrics
- mv_monthly_summary: Pre-computed monthly metrics

All views use only Phase 4 tables (applications, events, offers, synthetic_extensions,
data_loads, schema_versions) with no modifications to existing data.
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Any

import psycopg
from psycopg import Connection

from src.database import get_connection_kwargs


def get_analytics_connection() -> Connection:
    """Create a new connection for analytics operations."""
    return psycopg.connect(**get_connection_kwargs())


@contextmanager
def get_analytics_connection_context() -> Generator[Connection, None, None]:
    """Context manager for analytics connections."""
    conn = psycopg.connect(**get_connection_kwargs())
    try:
        yield conn
    finally:
        conn.close()


def refresh_materialized_views() -> list[str]:
    """Refresh all materialized views. Returns list of refreshed views."""
    views = [
        'mv_activity_summary',
        'mv_resource_workload',
        'mv_monthly_summary',
        'mv_application_type_summary',
    ]

    refreshed = []
    with get_analytics_connection_context() as conn:
        for view in views:
            with conn.cursor() as cur:
                cur.execute(f"REFRESH MATERIALIZED VIEW {view}")
            conn.commit()
            refreshed.append(view)

    return refreshed


def view_exists(view_name: str) -> bool:
    """Check if a view exists in the database."""
    with get_analytics_connection_context() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.views
                    WHERE table_schema = 'public'
                    AND table_name = %s
                );
                """,
                (view_name,),
            )
            return cur.fetchone()[0]


def materialized_view_exists(view_name: str) -> bool:
    """Check if a materialized view exists in the database."""
    with get_analytics_connection_context() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT FROM pg_matviews
                    WHERE schemaname = 'public'
                    AND matviewname = %s
                );
                """,
                (view_name,),
            )
            return cur.fetchone()[0]


def get_all_views() -> list[str]:
    """Get list of all analytics views created in Phase 5."""
    return [
        'view_application_metrics',
        'view_daily_throughput',
        'view_activity_summary',
        'view_resource_workload',
        'view_application_type_metrics',
        'view_loan_goal_metrics',
        'view_lifecycle_transition_metrics',
        'view_event_origin_metrics',
        'view_monthly_summary',
        'view_weekly_summary',
        'view_event_sequence',
        'view_processing_time_buckets',
        'view_offer_analysis',
    ]


def get_all_materialized_views() -> list[str]:
    """Get list of all materialized views created in Phase 5."""
    return [
        'mv_activity_summary',
        'mv_resource_workload',
        'mv_monthly_summary',
        'mv_application_type_summary',
    ]


def get_view_row_count(view_name: str) -> int:
    """Get row count for a view."""
    with get_analytics_connection_context() as conn:
        with conn.cursor() as cur:
            cur.execute(f'SELECT COUNT(*) FROM {view_name}')
            return cur.fetchone()[0]


def run_analytics_queries() -> dict[str, Any]:
    """Run representative analytics queries and return results."""
    results = {}

    with get_analytics_connection_context() as conn:
        with conn.cursor() as cur:
            # Query 1: Total applications
            cur.execute("SELECT COUNT(*) FROM view_application_metrics")
            results['total_applications'] = cur.fetchone()[0]

            # Query 2: Activity distribution top 5
            cur.execute("""
                SELECT activity, event_count, percentage_of_total
                FROM view_activity_summary
                ORDER BY event_count DESC
                LIMIT 5
            """)
            results['top_activities'] = [
                {'activity': row[0], 'count': row[1], 'percentage': row[2]}
                for row in cur.fetchall()
            ]

            # Query 3: Total events
            cur.execute("SELECT COUNT(*) FROM events")
            results['total_events'] = cur.fetchone()[0]

            # Query 4: Applications by type
            cur.execute("""
                SELECT application_type, COUNT(*), avg_events_per_application
                FROM view_application_type_metrics
                GROUP BY application_type, avg_events_per_application
                ORDER BY COUNT(*) DESC
            """)
            results['by_application_type'] = [
                {'type': row[0], 'count': row[1], 'avg_events': row[2]}
                for row in cur.fetchall()
            ]

            # Query 5: Processing time distribution
            cur.execute("""
                SELECT bucket, application_count, percentage
                FROM view_processing_time_buckets
                ORDER BY application_count DESC
            """)
            results['processing_time_buckets'] = [
                {'bucket': row[0], 'count': row[1], 'percentage': row[2]}
                for row in cur.fetchall()
            ]

            # Query 6: Resource workload top 5
            cur.execute("""
                SELECT resource, event_count, applications_handled
                FROM view_resource_workload
                ORDER BY event_count DESC
                LIMIT 5
            """)
            results['top_resources'] = [
                {'resource': row[0], 'events': row[1], 'applications': row[2]}
                for row in cur.fetchall()
            ]

            # Query 7: Lifecycle transition distribution
            cur.execute("""
                SELECT lifecycle_transition, event_count, applications_affected
                FROM view_lifecycle_transition_metrics
                ORDER BY event_count DESC
            """)
            results['lifecycle_transitions'] = [
                {'transition': row[0], 'count': row[1], 'apps': row[2]}
                for row in cur.fetchall()
            ]

            # Query 8: Monthly summary
            cur.execute("""
                SELECT year_month, applications, total_events, avg_events_per_app
                FROM view_monthly_summary
                ORDER BY year_month
            """)
            results['monthly_summary'] = [
                {'month': row[0], 'apps': row[1], 'events': row[2], 'avg_events': row[3]}
                for row in cur.fetchall()
            ]

    return results