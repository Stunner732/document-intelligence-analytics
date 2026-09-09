"""Python Analytics Query Layer for BPI Challenge 2017 Loan Application Analysis.

This module provides a clean query interface for analytical metrics derived from
the Phase 5 SQL Analytics views and materialized views. It builds on the existing
database infrastructure and Phase 5 views without duplicating SQL logic.

All queries use the existing views:
- view_application_metrics (31,509 applications)
- view_daily_throughput (daily volume)
- view_activity_summary (26 activities)
- view_resource_workload (149 resources)
- view_processing_time_buckets (duration distribution)
- view_lifecycle_transition_metrics (outcome analysis)
- view_loan_goal_metrics (loan purpose analysis)
- view_monthly_summary (temporal trends)
- mv_* materialized views (pre-computed aggregations)

The BPI Challenge 2017 dataset is a real loan application event log from a Dutch
financial institution. It does NOT contain document-processing metrics, SLA targets,
branches, or page counts. Those synthetic extensions are defined in the schema but
not populated. This module works with real data only.
"""

from typing import Any
from datetime import date

from src.database import get_cursor


def get_total_applications() -> int:
    """Get total number of loan applications in the dataset.

    Source: view_application_metrics (matches applications table row count)

    Returns:
        Total count of unique applications (31,509 expected)
    """
    with get_cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM view_application_metrics")
        return cur.fetchone()[0]


def get_total_events() -> int:
    """Get total number of events across all applications.

    Source: events table (base table)

    Returns:
        Total event count (1,202,267 expected)
    """
    with get_cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM events")
        return cur.fetchone()[0]


def get_application_volume_by_type() -> list[dict[str, Any]]:
    """Get application count and metrics grouped by application type.

    Source: mv_application_type_summary (materialized view)

    Returns:
        List of dicts with keys:
        - application_type: "New credit" or "Limit raise"
        - application_count: Number of applications
        - avg_events_per_application: Mean events per app
        - avg_processing_hours: Mean processing duration
        - avg_requested_amount: Mean requested loan amount

    Example:
        >>> data = get_application_volume_by_type()
        >>> data[0]['application_type']
        'New credit'
    """
    with get_cursor() as cur:
        cur.execute("""
            SELECT
                application_type,
                application_count,
                avg_events_per_application,
                avg_processing_hours,
                avg_requested_amount
            FROM mv_application_type_summary
            ORDER BY application_count DESC
        """)
        rows = cur.fetchall()
        return [
            {
                'application_type': row[0],
                'application_count': row[1],
                'avg_events_per_application': float(row[2]) if row[2] else 0.0,
                'avg_processing_hours': float(row[3]) if row[3] else 0.0,
                'avg_requested_amount': float(row[4]) if row[4] else 0.0,
            }
            for row in rows
        ]


def get_application_volume_over_time(
    granularity: str = 'monthly',
    start_date: date | None = None,
    end_date: date | None = None
) -> list[dict[str, Any]]:
    """Get application volume trends over time.

    Source: view_monthly_summary or view_daily_throughput

    Args:
        granularity: 'monthly' (default) or 'daily'
        start_date: Optional start date filter (inclusive)
        end_date: Optional end date filter (inclusive)

    Returns:
        For monthly granularity:
        - year_month: YYYY-MM format
        - applications: Application count
        - total_events: Event count
        - avg_events_per_app: Average events

        For daily granularity:
        - date: Date (YYYY-MM-DD)
        - applications_started: Applications started that day
        - total_events: Events for applications starting that day

    Raises:
        ValueError: If granularity is not 'monthly' or 'daily'
    """
    if granularity not in ('monthly', 'daily'):
        raise ValueError(f"granularity must be 'monthly' or 'daily', got '{granularity}'")

    with get_cursor() as cur:
        if granularity == 'monthly':
            query = """
                SELECT
                    year_month,
                    applications,
                    total_events,
                    avg_events_per_app
                FROM view_monthly_summary
                WHERE 1=1
            """
            params = []
            if start_date:
                # Filter by year/month derived from year_month (YYYY-MM format)
                query += " AND year_month >= TO_CHAR(%s, 'YYYY-MM')"
                params.append(start_date)
            if end_date:
                query += " AND year_month <= TO_CHAR(%s, 'YYYY-MM')"
                params.append(end_date)
            query += " ORDER BY year_month"

            cur.execute(query, params)
            rows = cur.fetchall()
            return [
                {
                    'year_month': row[0],
                    'applications': row[1],
                    'total_events': row[2],
                    'avg_events_per_app': float(row[3]) if row[3] else 0.0,
                }
                for row in rows
            ]
        else:  # daily
            query = """
                SELECT
                    date,
                    applications_started,
                    total_events
                FROM view_daily_throughput
                WHERE 1=1
            """
            params = []
            if start_date:
                query += " AND date >= %s"
                params.append(start_date)
            if end_date:
                query += " AND date <= %s"
                params.append(end_date)
            query += " ORDER BY date"

            cur.execute(query, params)
            rows = cur.fetchall()
            return [
                {
                    'date': row[0],
                    'applications_started': row[1],
                    'total_events': row[2],
                }
                for row in rows
            ]


def get_event_volume_over_time(granularity: str = 'monthly') -> list[dict[str, Any]]:
    """Get event volume trends over time.

    Source: view_monthly_summary

    Args:
        granularity: 'monthly' (default) - currently only monthly supported

    Returns:
        List of dicts with keys:
        - year_month: YYYY-MM format
        - total_events: Event count
        - avg_events_per_app: Average events per application
    """
    if granularity != 'monthly':
        raise ValueError(f"Currently only 'monthly' granularity supported, got '{granularity}'")

    with get_cursor() as cur:
        cur.execute("""
            SELECT
                year_month,
                total_events,
                avg_events_per_app
            FROM view_monthly_summary
            ORDER BY year_month
        """)
        rows = cur.fetchall()
        return [
            {
                'year_month': row[0],
                'total_events': row[1],
                'avg_events_per_app': float(row[2]) if row[2] else 0.0,
            }
            for row in rows
        ]


def get_processing_duration_metrics() -> dict[str, Any]:
    """Get processing duration statistics (average, median, distribution).

    Source: view_application_metrics, view_processing_time_buckets

    Returns:
        Dict with keys:
        - avg_processing_hours: Mean processing duration in hours
        - avg_processing_days: Mean processing duration in days
        - median_bucket: The bucket containing the median (approximate)
        - distribution: List of duration bucket distributions
    """
    with get_cursor() as cur:
        # Average processing duration
        cur.execute("""
            SELECT
                AVG(processing_hours) as avg_hours,
                AVG(processing_days) as avg_days
            FROM view_application_metrics
        """)
        avg_row = cur.fetchone()
        avg_hours = float(avg_row[0]) if avg_row[0] else 0.0
        avg_days = float(avg_row[1]) if avg_row[1] else 0.0

        # Distribution from buckets
        cur.execute("""
            SELECT
                bucket,
                application_count,
                percentage
            FROM view_processing_time_buckets
            ORDER BY
                CASE bucket
                    WHEN '< 1 hour' THEN 1
                    WHEN '1-24 hours' THEN 2
                    WHEN '1-7 days' THEN 3
                    WHEN '1-4 weeks' THEN 4
                    ELSE 5
                END
        """)
        buckets = cur.fetchall()
        distribution = [
            {
                'bucket': row[0],
                'application_count': row[1],
                'percentage': float(row[2]) if row[2] else 0.0,
            }
            for row in buckets
        ]

        # Approximate median bucket (cumulative percentage approach)
        median_bucket = None
        cumulative = 0.0
        for bucket in distribution:
            cumulative += bucket['percentage']
            if cumulative >= 50.0:
                median_bucket = bucket['bucket']
                break

        return {
            'avg_processing_hours': avg_hours,
            'avg_processing_days': avg_days,
            'median_bucket': median_bucket,
            'distribution': distribution,
        }


def get_processing_time_distribution() -> list[dict[str, Any]]:
    """Get application count by processing time bucket.

    Source: view_processing_time_buckets

    Returns:
        List of dicts with keys:
        - bucket: Duration category ('< 1 hour', '1-24 hours', '1-7 days', '1-4 weeks', '> 4 weeks')
        - application_count: Number of applications in this bucket
        - percentage: Percentage of total applications
        - avg_events: Average events for applications in this bucket
    """
    with get_cursor() as cur:
        cur.execute("""
            SELECT
                bucket,
                application_count,
                percentage,
                avg_events
            FROM view_processing_time_buckets
            ORDER BY
                CASE bucket
                    WHEN '< 1 hour' THEN 1
                    WHEN '1-24 hours' THEN 2
                    WHEN '1-7 days' THEN 3
                    WHEN '1-4 weeks' THEN 4
                    ELSE 5
                END
        """)
        rows = cur.fetchall()
        return [
            {
                'bucket': row[0],
                'application_count': row[1],
                'percentage': float(row[2]) if row[2] else 0.0,
                'avg_events': float(row[3]) if row[3] else 0.0,
            }
            for row in rows
        ]


def get_activity_summary() -> list[dict[str, Any]]:
    """Get activity frequency and lifecycle analysis.

    Source: view_activity_summary

    Returns:
        List of dicts with keys:
        - activity: Activity name (e.g., 'W_Validate application')
        - event_count: Total events for this activity
        - unique_applications: Distinct applications with this activity
        - percentage_of_total: Percentage of all events
        - activity_type: Category ('Workflow', 'Offer', 'Application', 'Other')
        - complete_pct: Percentage of events with lifecycle='complete'
        - suspend_pct: Percentage of events with lifecycle='suspend'
        - withdraw_pct: Percentage of events with lifecycle='withdraw'
    """
    with get_cursor() as cur:
        cur.execute("""
            SELECT
                activity,
                event_count,
                unique_applications,
                percentage_of_total,
                activity_type,
                complete_pct,
                suspend_pct,
                withdraw_pct
            FROM view_activity_summary
            ORDER BY event_count DESC
        """)
        rows = cur.fetchall()
        return [
            {
                'activity': row[0],
                'event_count': row[1],
                'unique_applications': row[2],
                'percentage_of_total': float(row[3]) if row[3] else 0.0,
                'activity_type': row[4],
                'complete_pct': float(row[5]) if row[5] else 0.0,
                'suspend_pct': float(row[6]) if row[6] else 0.0,
                'withdraw_pct': float(row[7]) if row[7] else 0.0,
            }
            for row in rows
        ]


def get_resource_workload(limit: int | None = None) -> list[dict[str, Any]]:
    """Get resource (user) workload distribution.

    Source: view_resource_workload

    Args:
        limit: Optional limit on number of resources returned (top N by workload)

    Returns:
        List of dicts with keys:
        - resource: User/resource identifier
        - event_count: Total events handled
        - applications_handled: Distinct applications worked on
        - workload_percentage: Percentage of total events handled
        - unique_activities: Number of distinct activities performed
    """
    with get_cursor() as cur:
        query = """
            SELECT
                resource,
                event_count,
                applications_handled,
                workload_percentage,
                unique_activities
            FROM view_resource_workload
            ORDER BY event_count DESC
        """
        params = []
        if limit:
            query += " LIMIT %s"
            params.append(limit)

        cur.execute(query, params)
        rows = cur.fetchall()
        return [
            {
                'resource': row[0],
                'event_count': row[1],
                'applications_handled': row[2],
                'workload_percentage': float(row[3]) if row[3] else 0.0,
                'unique_activities': row[4],
            }
            for row in rows
        ]


def get_lifecycle_outcome_summary() -> list[dict[str, Any]]:
    """Get lifecycle transition analysis (outcome distribution).

    Source: view_lifecycle_transition_metrics

    Returns:
        List of dicts with keys:
        - lifecycle_transition: Transition type ('complete', 'suspend', 'withdraw', etc.)
        - event_count: Number of events with this transition
        - applications_affected: Distinct applications affected
        - percentage: Percentage of total events
        - workflow_pct: Percentage that are workflow activities
        - offer_pct: Percentage that are offer activities
        - application_pct: Percentage that are application activities
    """
    with get_cursor() as cur:
        cur.execute("""
            SELECT
                lifecycle_transition,
                event_count,
                applications_affected,
                percentage,
                workflow_pct,
                offer_pct,
                application_pct
            FROM view_lifecycle_transition_metrics
            ORDER BY event_count DESC
        """)
        rows = cur.fetchall()
        return [
            {
                'lifecycle_transition': row[0],
                'event_count': row[1],
                'applications_affected': row[2],
                'percentage': float(row[3]) if row[3] else 0.0,
                'workflow_pct': float(row[4]) if row[4] else 0.0,
                'offer_pct': float(row[5]) if row[5] else 0.0,
                'application_pct': float(row[6]) if row[6] else 0.0,
            }
            for row in rows
        ]


def get_loan_goal_summary() -> list[dict[str, Any]]:
    """Get application metrics grouped by loan goal (purpose).

    Source: view_loan_goal_metrics

    Returns:
        List of dicts with keys:
        - loan_goal: Loan purpose (e.g., 'Consumer credit', 'Business')
        - application_count: Number of applications
        - avg_events: Average events per application
        - avg_processing_hours: Average processing duration in hours
        - avg_requested_amount: Average requested loan amount
        - first_date: Earliest application date
        - last_date: Latest application date
    """
    with get_cursor() as cur:
        cur.execute("""
            SELECT
                loan_goal,
                application_count,
                avg_events,
                avg_processing_hours,
                avg_requested_amount,
                first_date,
                last_date
            FROM view_loan_goal_metrics
            ORDER BY application_count DESC
        """)
        rows = cur.fetchall()
        return [
            {
                'loan_goal': row[0],
                'application_count': row[1],
                'avg_events': float(row[2]) if row[2] else 0.0,
                'avg_processing_hours': float(row[3]) if row[3] else 0.0,
                'avg_requested_amount': float(row[4]) if row[4] else 0.0,
                'first_date': row[5],
                'last_date': row[6],
            }
            for row in rows
        ]


def get_application_processing_metrics(limit: int | None = None) -> list[dict[str, Any]]:
    """Get per-application processing metrics.

    Source: view_application_metrics

    Args:
        limit: Optional limit on number of applications returned (ordered by processing time DESC)

    Returns:
        List of dicts with keys:
        - application_id: Unique application identifier
        - application_type: "New credit" or "Limit raise"
        - loan_goal: Loan purpose
        - requested_amount: Requested loan amount
        - event_count: Number of events in this application
        - first_event_time: Timestamp of first event
        - last_event_time: Timestamp of last event
        - processing_hours: Duration in hours
        - processing_days: Duration in days
        - complete_count: Number of 'complete' lifecycle events
        - suspend_count: Number of 'suspend' lifecycle events
        - withdraw_count: Number of 'withdraw' lifecycle events

    Note:
        This returns 31,509 rows without limit. Use limit parameter for exploration.
    """
    with get_cursor() as cur:
        query = """
            SELECT
                application_id,
                application_type,
                loan_goal,
                requested_amount,
                event_count,
                first_event_time,
                last_event_time,
                processing_hours,
                processing_days,
                complete_count,
                suspend_count,
                withdraw_count
            FROM view_application_metrics
            ORDER BY processing_hours DESC NULLS LAST
        """
        params = []
        if limit:
            query += " LIMIT %s"
            params.append(limit)

        cur.execute(query, params)
        rows = cur.fetchall()
        return [
            {
                'application_id': row[0],
                'application_type': row[1],
                'loan_goal': row[2],
                'requested_amount': float(row[3]) if row[3] else 0.0,
                'event_count': row[4],
                'first_event_time': row[5],
                'last_event_time': row[6],
                'processing_hours': float(row[7]) if row[7] else 0.0,
                'processing_days': float(row[8]) if row[8] else 0.0,
                'complete_count': row[9],
                'suspend_count': row[10],
                'withdraw_count': row[11],
            }
            for row in rows
        ]


def get_executive_summary() -> dict[str, Any]:
    """Get high-level executive summary metrics.

    Aggregates data from multiple views for dashboard summary cards.

    Source: view_application_metrics, view_activity_summary, view_resource_workload

    Returns:
        Dict with keys:
        - total_applications: Total application count
        - total_events: Total event count
        - avg_events_per_app: Average events per application
        - avg_processing_days: Average processing duration in days
        - distinct_activities: Number of distinct activity types
        - distinct_resources: Number of distinct resources/users
        - application_types: List of application type counts
    """
    with get_cursor() as cur:
        # Total applications and events
        cur.execute("SELECT COUNT(*) FROM view_application_metrics")
        total_applications = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM events")
        total_events = cur.fetchone()[0]

        # Average events per application
        cur.execute("SELECT AVG(event_count) FROM view_application_metrics")
        avg_events = cur.fetchone()[0]
        avg_events_per_app = float(avg_events) if avg_events else 0.0

        # Average processing days
        cur.execute("SELECT AVG(processing_days) FROM view_application_metrics")
        avg_days = cur.fetchone()[0]
        avg_processing_days = float(avg_days) if avg_days else 0.0

        # Distinct activities and resources
        cur.execute("SELECT COUNT(*) FROM view_activity_summary")
        distinct_activities = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM view_resource_workload")
        distinct_resources = cur.fetchone()[0]

        # Application type distribution
        cur.execute("""
            SELECT application_type, application_count
            FROM mv_application_type_summary
            ORDER BY application_count DESC
        """)
        app_types = cur.fetchall()
        application_types = [
            {'type': row[0], 'count': row[1]}
            for row in app_types
        ]

        return {
            'total_applications': total_applications,
            'total_events': total_events,
            'avg_events_per_app': avg_events_per_app,
            'avg_processing_days': avg_processing_days,
            'distinct_activities': distinct_activities,
            'distinct_resources': distinct_resources,
            'application_types': application_types,
        }
