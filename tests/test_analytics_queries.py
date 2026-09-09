"""Tests for Phase 6 Python Analytics Query Layer.

Tests verify that query functions:
1. Return correct structure and types
2. Work with the existing PostgreSQL database
3. Handle edge cases appropriately
4. Use existing Phase 5 views correctly
"""

import pytest
from datetime import date


class TestBasicCounts:
    """Test basic count queries."""

    def test_get_total_applications_returns_int(self):
        """Total applications should return an integer."""
        from src.analytics.queries import get_total_applications
        result = get_total_applications()
        assert isinstance(result, int)
        assert result > 0

    def test_get_total_applications_matches_database(self):
        """Total applications should match applications table."""
        from src.analytics.queries import get_total_applications
        from src.database import get_cursor
        result = get_total_applications()
        with get_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM applications")
            expected = cur.fetchone()[0]
        assert result == expected

    def test_get_total_events_returns_int(self):
        """Total events should return an integer."""
        from src.analytics.queries import get_total_events
        result = get_total_events()
        assert isinstance(result, int)
        assert result > 0

    def test_get_total_events_matches_database(self):
        """Total events should match events table."""
        from src.analytics.queries import get_total_events
        from src.database import get_cursor
        result = get_total_events()
        with get_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM events")
            expected = cur.fetchone()[0]
        assert result == expected


class TestApplicationVolumeByType:
    """Test application volume by type query."""

    def test_returns_list_of_dicts(self):
        """Should return a list of dictionaries."""
        from src.analytics.queries import get_application_volume_by_type
        result = get_application_volume_by_type()
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(item, dict) for item in result)

    def test_has_expected_keys(self):
        """Each dict should have expected keys."""
        from src.analytics.queries import get_application_volume_by_type
        result = get_application_volume_by_type()
        expected_keys = {
            'application_type',
            'application_count',
            'avg_events_per_application',
            'avg_processing_hours',
            'avg_requested_amount'
        }
        for item in result:
            assert set(item.keys()) == expected_keys

    def test_has_two_application_types(self):
        """Should have exactly 2 application types (New credit, Limit raise)."""
        from src.analytics.queries import get_application_volume_by_type
        result = get_application_volume_by_type()
        assert len(result) == 2

    def test_application_count_sum_matches_total(self):
        """Sum of application counts should match total applications."""
        from src.analytics.queries import get_application_volume_by_type, get_total_applications
        result = get_application_volume_by_type()
        total = get_total_applications()
        sum_counts = sum(item['application_count'] for item in result)
        assert sum_counts == total

    def test_numeric_values_are_floats(self):
        """Numeric values should be floats."""
        from src.analytics.queries import get_application_volume_by_type
        result = get_application_volume_by_type()
        for item in result:
            assert isinstance(item['avg_events_per_application'], float)
            assert isinstance(item['avg_processing_hours'], float)
            assert isinstance(item['avg_requested_amount'], float)


class TestApplicationVolumeOverTime:
    """Test application volume over time queries."""

    def test_monthly_returns_list_of_dicts(self):
        """Monthly granularity should return list of dicts."""
        from src.analytics.queries import get_application_volume_over_time
        result = get_application_volume_over_time(granularity='monthly')
        assert isinstance(result, list)
        assert len(result) > 0

    def test_monthly_has_expected_keys(self):
        """Monthly result should have expected keys."""
        from src.analytics.queries import get_application_volume_over_time
        result = get_application_volume_over_time(granularity='monthly')
        expected_keys = {'year_month', 'applications', 'total_events', 'avg_events_per_app'}
        for item in result:
            assert set(item.keys()) == expected_keys

    def test_daily_returns_list_of_dicts(self):
        """Daily granularity should return list of dicts."""
        from src.analytics.queries import get_application_volume_over_time
        result = get_application_volume_over_time(granularity='daily')
        assert isinstance(result, list)
        assert len(result) > 0

    def test_daily_has_expected_keys(self):
        """Daily result should have expected keys."""
        from src.analytics.queries import get_application_volume_over_time
        result = get_application_volume_over_time(granularity='daily')
        expected_keys = {'date', 'applications_started', 'total_events'}
        for item in result:
            assert set(item.keys()) == expected_keys

    def test_invalid_granularity_raises_error(self):
        """Invalid granularity should raise ValueError."""
        from src.analytics.queries import get_application_volume_over_time
        with pytest.raises(ValueError, match="granularity must be"):
            get_application_volume_over_time(granularity='hourly')

    def test_date_filtering_works(self):
        """Date filters should correctly filter results."""
        from src.analytics.queries import get_application_volume_over_time
        result = get_application_volume_over_time(
            granularity='daily',
            start_date=date(2016, 1, 1),
            end_date=date(2016, 1, 31)
        )
        assert len(result) > 0
        # All dates should be in January 2016
        for item in result:
            assert item['date'].month == 1
            assert item['date'].year == 2016


class TestEventVolumeOverTime:
    """Test event volume over time queries."""

    def test_monthly_returns_correct_structure(self):
        """Should return list of dicts with expected keys."""
        from src.analytics.queries import get_event_volume_over_time
        result = get_event_volume_over_time(granularity='monthly')
        assert isinstance(result, list)
        expected_keys = {'year_month', 'total_events', 'avg_events_per_app'}
        for item in result:
            assert set(item.keys()) == expected_keys

    def test_invalid_granularity_raises_error(self):
        """Invalid granularity should raise ValueError."""
        from src.analytics.queries import get_event_volume_over_time
        with pytest.raises(ValueError, match="Currently only 'monthly' granularity supported"):
            get_event_volume_over_time(granularity='daily')


class TestProcessingDurationMetrics:
    """Test processing duration metrics."""

    def test_returns_dict_with_expected_keys(self):
        """Should return dict with expected keys."""
        from src.analytics.queries import get_processing_duration_metrics
        result = get_processing_duration_metrics()
        expected_keys = {
            'avg_processing_hours',
            'avg_processing_days',
            'median_bucket',
            'distribution'
        }
        assert isinstance(result, dict)
        assert set(result.keys()) == expected_keys

    def test_distribution_is_list(self):
        """Distribution should be a list."""
        from src.analytics.queries import get_processing_duration_metrics
        result = get_processing_duration_metrics()
        assert isinstance(result['distribution'], list)
        assert len(result['distribution']) > 0

    def test_distribution_items_have_expected_keys(self):
        """Distribution items should have bucket, count, percentage."""
        from src.analytics.queries import get_processing_duration_metrics
        result = get_processing_duration_metrics()
        expected_keys = {'bucket', 'application_count', 'percentage'}
        for item in result['distribution']:
            assert set(item.keys()) == expected_keys

    def test_avg_values_are_floats(self):
        """Average values should be floats."""
        from src.analytics.queries import get_processing_duration_metrics
        result = get_processing_duration_metrics()
        assert isinstance(result['avg_processing_hours'], float)
        assert isinstance(result['avg_processing_days'], float)


class TestProcessingTimeDistribution:
    """Test processing time distribution query."""

    def test_returns_list_of_dicts(self):
        """Should return list of dicts."""
        from src.analytics.queries import get_processing_time_distribution
        result = get_processing_time_distribution()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_has_expected_keys(self):
        """Each dict should have expected keys."""
        from src.analytics.queries import get_processing_time_distribution
        result = get_processing_time_distribution()
        expected_keys = {'bucket', 'application_count', 'percentage', 'avg_events'}
        for item in result:
            assert set(item.keys()) == expected_keys

    def test_percentages_sum_approximately_100(self):
        """Percentages should sum to approximately 100%."""
        from src.analytics.queries import get_processing_time_distribution
        result = get_processing_time_distribution()
        total_pct = sum(item['percentage'] for item in result)
        assert 99.9 <= total_pct <= 100.1

    def test_bucket_counts_sum_to_total_applications(self):
        """Bucket counts should sum to total applications."""
        from src.analytics.queries import get_processing_time_distribution, get_total_applications
        result = get_processing_time_distribution()
        total = get_total_applications()
        sum_counts = sum(item['application_count'] for item in result)
        assert sum_counts == total


class TestActivitySummary:
    """Test activity summary query."""

    def test_returns_list_of_dicts(self):
        """Should return list of dicts."""
        from src.analytics.queries import get_activity_summary
        result = get_activity_summary()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_has_expected_keys(self):
        """Each dict should have expected keys."""
        from src.analytics.queries import get_activity_summary
        result = get_activity_summary()
        expected_keys = {
            'activity',
            'event_count',
            'unique_applications',
            'percentage_of_total',
            'activity_type',
            'complete_pct',
            'suspend_pct',
            'withdraw_pct'
        }
        for item in result:
            assert set(item.keys()) == expected_keys

    def test_has_26_activities(self):
        """Should have 26 distinct activities."""
        from src.analytics.queries import get_activity_summary
        result = get_activity_summary()
        assert len(result) == 26

    def test_percentages_sum_approximately_100(self):
        """Percentages should sum to approximately 100%."""
        from src.analytics.queries import get_activity_summary
        result = get_activity_summary()
        total_pct = sum(item['percentage_of_total'] for item in result)
        assert 99.9 <= total_pct <= 100.1

    def test_activity_types_are_valid(self):
        """Activity types should be one of the expected values."""
        from src.analytics.queries import get_activity_summary
        result = get_activity_summary()
        valid_types = {'Workflow', 'Offer', 'Application', 'Other'}
        for item in result:
            assert item['activity_type'] in valid_types


class TestResourceWorkload:
    """Test resource workload query."""

    def test_returns_list_of_dicts(self):
        """Should return list of dicts."""
        from src.analytics.queries import get_resource_workload
        result = get_resource_workload()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_has_expected_keys(self):
        """Each dict should have expected keys."""
        from src.analytics.queries import get_resource_workload
        result = get_resource_workload()
        expected_keys = {
            'resource',
            'event_count',
            'applications_handled',
            'workload_percentage',
            'unique_activities'
        }
        for item in result:
            assert set(item.keys()) == expected_keys

    def test_has_149_resources(self):
        """Should have 149 distinct resources."""
        from src.analytics.queries import get_resource_workload
        result = get_resource_workload()
        assert len(result) == 149

    def test_limit_parameter_works(self):
        """Limit parameter should restrict results."""
        from src.analytics.queries import get_resource_workload
        result = get_resource_workload(limit=10)
        assert len(result) == 10

    def test_percentages_sum_approximately_100(self):
        """Workload percentages should sum to approximately 100%."""
        from src.analytics.queries import get_resource_workload
        result = get_resource_workload()
        total_pct = sum(item['workload_percentage'] for item in result)
        assert 99.9 <= total_pct <= 100.1


class TestLifecycleOutcomeSummary:
    """Test lifecycle outcome summary query."""

    def test_returns_list_of_dicts(self):
        """Should return list of dicts."""
        from src.analytics.queries import get_lifecycle_outcome_summary
        result = get_lifecycle_outcome_summary()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_has_expected_keys(self):
        """Each dict should have expected keys."""
        from src.analytics.queries import get_lifecycle_outcome_summary
        result = get_lifecycle_outcome_summary()
        expected_keys = {
            'lifecycle_transition',
            'event_count',
            'applications_affected',
            'percentage',
            'workflow_pct',
            'offer_pct',
            'application_pct'
        }
        for item in result:
            assert set(item.keys()) == expected_keys

    def test_percentages_sum_approximately_100(self):
        """Percentages should sum to approximately 100%."""
        from src.analytics.queries import get_lifecycle_outcome_summary
        result = get_lifecycle_outcome_summary()
        total_pct = sum(item['percentage'] for item in result)
        assert 99.9 <= total_pct <= 100.1


class TestLoanGoalSummary:
    """Test loan goal summary query."""

    def test_returns_list_of_dicts(self):
        """Should return list of dicts."""
        from src.analytics.queries import get_loan_goal_summary
        result = get_loan_goal_summary()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_has_expected_keys(self):
        """Each dict should have expected keys."""
        from src.analytics.queries import get_loan_goal_summary
        result = get_loan_goal_summary()
        expected_keys = {
            'loan_goal',
            'application_count',
            'avg_events',
            'avg_processing_hours',
            'avg_requested_amount',
            'first_date',
            'last_date'
        }
        for item in result:
            assert set(item.keys()) == expected_keys

    def test_sum_matches_total_applications(self):
        """Sum of application counts should match total."""
        from src.analytics.queries import get_loan_goal_summary, get_total_applications
        result = get_loan_goal_summary()
        total = get_total_applications()
        sum_counts = sum(item['application_count'] for item in result)
        assert sum_counts == total


class TestApplicationProcessingMetrics:
    """Test per-application processing metrics query."""

    def test_returns_list_of_dicts(self):
        """Should return list of dicts."""
        from src.analytics.queries import get_application_processing_metrics
        result = get_application_processing_metrics(limit=10)
        assert isinstance(result, list)
        assert len(result) == 10

    def test_has_expected_keys(self):
        """Each dict should have expected keys."""
        from src.analytics.queries import get_application_processing_metrics
        result = get_application_processing_metrics(limit=5)
        expected_keys = {
            'application_id',
            'application_type',
            'loan_goal',
            'requested_amount',
            'event_count',
            'first_event_time',
            'last_event_time',
            'processing_hours',
            'processing_days',
            'complete_count',
            'suspend_count',
            'withdraw_count'
        }
        for item in result:
            assert set(item.keys()) == expected_keys

    def test_limit_parameter_works(self):
        """Limit parameter should restrict results."""
        from src.analytics.queries import get_application_processing_metrics
        result = get_application_processing_metrics(limit=50)
        assert len(result) == 50

    def test_without_limit_returns_all_applications(self):
        """Without limit should return all 31,509 applications."""
        from src.analytics.queries import get_application_processing_metrics
        result = get_application_processing_metrics()
        assert len(result) == 31509


class TestExecutiveSummary:
    """Test executive summary query."""

    def test_returns_dict_with_expected_keys(self):
        """Should return dict with expected keys."""
        from src.analytics.queries import get_executive_summary
        result = get_executive_summary()
        expected_keys = {
            'total_applications',
            'total_events',
            'avg_events_per_app',
            'avg_processing_days',
            'distinct_activities',
            'distinct_resources',
            'application_types'
        }
        assert isinstance(result, dict)
        assert set(result.keys()) == expected_keys

    def test_numeric_values_are_correct_types(self):
        """Numeric values should be correct types."""
        from src.analytics.queries import get_executive_summary
        result = get_executive_summary()
        assert isinstance(result['total_applications'], int)
        assert isinstance(result['total_events'], int)
        assert isinstance(result['avg_events_per_app'], float)
        assert isinstance(result['avg_processing_days'], float)
        assert isinstance(result['distinct_activities'], int)
        assert isinstance(result['distinct_resources'], int)

    def test_application_types_is_list(self):
        """Application types should be a list."""
        from src.analytics.queries import get_executive_summary
        result = get_executive_summary()
        assert isinstance(result['application_types'], list)
        assert len(result['application_types']) == 2

    def test_values_match_individual_queries(self):
        """Values should match results from individual queries."""
        from src.analytics.queries import (
            get_executive_summary,
            get_total_applications,
            get_total_events,
            get_activity_summary,
            get_resource_workload
        )
        summary = get_executive_summary()
        assert summary['total_applications'] == get_total_applications()
        assert summary['total_events'] == get_total_events()
        assert summary['distinct_activities'] == len(get_activity_summary())
        assert summary['distinct_resources'] == len(get_resource_workload())


class TestTypeConsistency:
    """Test that all functions return consistent types."""

    def test_all_float_values_are_floats(self):
        """All numeric return values should be floats where expected."""
        from src.analytics.queries import (
            get_application_volume_by_type,
            get_processing_duration_metrics,
            get_activity_summary,
            get_resource_workload
        )

        # Check application volume
        for item in get_application_volume_by_type():
            assert isinstance(item['avg_events_per_application'], float)

        # Check duration metrics
        metrics = get_processing_duration_metrics()
        assert isinstance(metrics['avg_processing_hours'], float)
        assert isinstance(metrics['avg_processing_days'], float)

        # Check activity summary
        for item in get_activity_summary():
            assert isinstance(item['percentage_of_total'], float)

        # Check resource workload
        for item in get_resource_workload():
            assert isinstance(item['workload_percentage'], float)
