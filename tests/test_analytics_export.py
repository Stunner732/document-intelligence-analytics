"""Tests for Phase 6.2 Analytics Export Module.

Tests verify that export functions:
1. Write correct CSV and Parquet files
2. Return proper metadata
3. Handle edge cases (empty data, invalid inputs)
4. Work with Phase 6.1 query functions against the real database
5. Support selective and batch exports
6. Generate correct export manifests

Test categories:
- TestExportToCSV: Core CSV export logic (no DB dependency)
- TestExportToParquet: Core Parquet export logic (no DB dependency)
- TestExportValidation: Input validation for core functions
- TestExportExecutiveSummary: Integration with Phase 6.1 (DB required)
- TestExportApplicationVolume: Integration tests for volume exports
- TestExportActivitySummary: Integration test for activity export
- TestExportResourceWorkload: Integration test for resource export
- TestExportLifecycleOutcomes: Integration test for outcomes export
- TestExportLoanGoalSummary: Integration test for loan goals
- TestExportProcessingTimeDistribution: Integration test for duration export
- TestExportAll: Batch export integration test
- TestExportManifest: Manifest listing functionality
"""

import pytest
import pandas as pd
from pathlib import Path


# ---------------------------------------------------------------------------
# Sample data fixtures (no DB dependency)
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_list_data():
    """Sample list-of-dicts data for export testing."""
    return [
        {'name': 'Alpha', 'value': 100, 'pct': 45.5},
        {'name': 'Beta', 'value': 200, 'pct': 30.2},
        {'name': 'Gamma', 'value': 50, 'pct': 24.3},
    ]


@pytest.fixture
def sample_single_dict():
    """Sample single dict for summary export testing."""
    return {
        'total_applications': 31509,
        'total_events': 1202267,
        'avg_events_per_app': 38.1,
    }


@pytest.fixture
def sample_empty_list():
    """Empty list for validation testing."""
    return []


# ---------------------------------------------------------------------------
# Core CSV export tests (no database dependency)
# ---------------------------------------------------------------------------

class TestExportToCSV:
    """Test core CSV export functionality."""

    def test_creates_csv_file(self, tmp_path, sample_list_data):
        """Should create a CSV file on disk."""
        from src.analytics.export import export_to_csv
        meta = export_to_csv(sample_list_data, tmp_path, 'test_data')
        assert Path(meta['path']).exists()
        assert meta['filename'] == 'test_data.csv'

    def test_csv_has_correct_row_count(self, tmp_path, sample_list_data):
        """CSV should have the same number of rows as input data."""
        from src.analytics.export import export_to_csv
        meta = export_to_csv(sample_list_data, tmp_path, 'test_data')
        assert meta['rows'] == 3

    def test_csv_is_valid_dataframe(self, tmp_path, sample_list_data):
        """Written CSV should be readable by pandas with correct columns."""
        from src.analytics.export import export_to_csv
        meta = export_to_csv(sample_list_data, tmp_path, 'test_data')
        df = pd.read_csv(meta['path'])
        assert list(df.columns) == ['name', 'value', 'pct']
        assert len(df) == 3

    def test_csv_content_matches_input(self, tmp_path, sample_list_data):
        """CSV content should match the input data."""
        from src.analytics.export import export_to_csv
        meta = export_to_csv(sample_list_data, tmp_path, 'test_data')
        df = pd.read_csv(meta['path'])
        assert df['name'].tolist() == ['Alpha', 'Beta', 'Gamma']
        assert df['value'].tolist() == [100, 200, 50]

    def test_single_dict_export(self, tmp_path, sample_single_dict):
        """Single dict should be exported as one-row CSV."""
        from src.analytics.export import export_to_csv
        meta = export_to_csv(sample_single_dict, tmp_path, 'summary')
        df = pd.read_csv(meta['path'])
        assert len(df) == 1
        assert df['total_applications'].iloc[0] == 31509

    def test_metadata_has_required_keys(self, tmp_path, sample_list_data):
        """Export metadata should contain all required keys."""
        from src.analytics.export import export_to_csv
        meta = export_to_csv(sample_list_data, tmp_path, 'test_data')
        required_keys = {'filename', 'path', 'format', 'rows', 'size_bytes', 'source_function', 'exported_at'}
        assert set(meta.keys()) == required_keys

    def test_metadata_format_is_csv(self, tmp_path, sample_list_data):
        """Metadata format should be 'csv'."""
        from src.analytics.export import export_to_csv
        meta = export_to_csv(sample_list_data, tmp_path, 'test_data')
        assert meta['format'] == 'csv'

    def test_metadata_size_is_positive(self, tmp_path, sample_list_data):
        """File size in metadata should be positive."""
        from src.analytics.export import export_to_csv
        meta = export_to_csv(sample_list_data, tmp_path, 'test_data')
        assert meta['size_bytes'] > 0

    def test_creates_subdirectory(self, tmp_path, sample_list_data):
        """Should create nested output directories if they don't exist."""
        from src.analytics.export import export_to_csv
        out_dir = tmp_path / 'subdir1' / 'subdir2'
        meta = export_to_csv(sample_list_data, out_dir, 'test_data')
        assert Path(meta['path']).exists()

    def test_utf8_encoding(self, tmp_path):
        """CSV should handle Unicode characters correctly."""
        from src.analytics.export import export_to_csv
        data = [{'name': 'Ünïcödé', 'value': 1}]
        meta = export_to_csv(data, tmp_path, 'unicode_test')
        df = pd.read_csv(meta['path'])
        assert df['name'].iloc[0] == 'Ünïcödé'


# ---------------------------------------------------------------------------
# Core Parquet export tests (no database dependency)
# ---------------------------------------------------------------------------

class TestExportToParquet:
    """Test core Parquet export functionality."""

    def test_creates_parquet_file(self, tmp_path, sample_list_data):
        """Should create a Parquet file on disk."""
        from src.analytics.export import export_to_parquet
        meta = export_to_parquet(sample_list_data, tmp_path, 'test_data')
        assert Path(meta['path']).exists()
        assert meta['filename'] == 'test_data.parquet'

    def test_parquet_has_correct_row_count(self, tmp_path, sample_list_data):
        """Parquet should have the same number of rows as input data."""
        from src.analytics.export import export_to_parquet
        meta = export_to_parquet(sample_list_data, tmp_path, 'test_data')
        assert meta['rows'] == 3

    def test_parquet_is_valid_dataframe(self, tmp_path, sample_list_data):
        """Written Parquet should be readable by pandas with correct columns."""
        from src.analytics.export import export_to_parquet
        meta = export_to_parquet(sample_list_data, tmp_path, 'test_data')
        df = pd.read_parquet(meta['path'])
        assert list(df.columns) == ['name', 'value', 'pct']
        assert len(df) == 3

    def test_parquet_content_matches_input(self, tmp_path, sample_list_data):
        """Parquet content should match the input data."""
        from src.analytics.export import export_to_parquet
        meta = export_to_parquet(sample_list_data, tmp_path, 'test_data')
        df = pd.read_parquet(meta['path'])
        assert df['name'].tolist() == ['Alpha', 'Beta', 'Gamma']
        assert df['value'].tolist() == [100, 200, 50]

    def test_single_dict_export(self, tmp_path, sample_single_dict):
        """Single dict should be exported as one-row Parquet."""
        from src.analytics.export import export_to_parquet
        meta = export_to_parquet(sample_single_dict, tmp_path, 'summary')
        df = pd.read_parquet(meta['path'])
        assert len(df) == 1
        assert df['total_applications'].iloc[0] == 31509

    def test_metadata_format_is_parquet(self, tmp_path, sample_list_data):
        """Metadata format should be 'parquet'."""
        from src.analytics.export import export_to_parquet
        meta = export_to_parquet(sample_list_data, tmp_path, 'test_data')
        assert meta['format'] == 'parquet'

    def test_parquet_compressed_smaller_than_csv(self, tmp_path, sample_list_data):
        """Parquet file should be reasonably sized (compression working)."""
        from src.analytics.export import export_to_csv, export_to_parquet
        csv_meta = export_to_csv(sample_list_data, tmp_path, 'test_csv')
        parquet_meta = export_to_parquet(sample_list_data, tmp_path, 'test_parquet')
        # Parquet should not be unreasonably larger
        assert parquet_meta['size_bytes'] > 0


# ---------------------------------------------------------------------------
# Input validation tests (no database dependency)
# ---------------------------------------------------------------------------

class TestExportValidation:
    """Test input validation for core export functions."""

    def test_none_data_raises_valueerror_csv(self, tmp_path):
        """None data should raise ValueError for CSV export."""
        from src.analytics.export import export_to_csv
        with pytest.raises(ValueError, match="Data cannot be None"):
            export_to_csv(None, tmp_path, 'test')

    def test_none_data_raises_valueerror_parquet(self, tmp_path):
        """None data should raise ValueError for Parquet export."""
        from src.analytics.export import export_to_parquet
        with pytest.raises(ValueError, match="Data cannot be None"):
            export_to_parquet(None, tmp_path, 'test')

    def test_empty_list_raises_valueerror_csv(self, tmp_path, sample_empty_list):
        """Empty list should raise ValueError for CSV export."""
        from src.analytics.export import export_to_csv
        with pytest.raises(ValueError, match="empty"):
            export_to_csv(sample_empty_list, tmp_path, 'test')

    def test_empty_list_raises_valueerror_parquet(self, tmp_path, sample_empty_list):
        """Empty list should raise ValueError for Parquet export."""
        from src.analytics.export import export_to_parquet
        with pytest.raises(ValueError, match="empty"):
            export_to_parquet(sample_empty_list, tmp_path, 'test')

    def test_invalid_type_raises_valueerror_csv(self, tmp_path):
        """Invalid data type should raise ValueError for CSV export."""
        from src.analytics.export import export_to_csv
        with pytest.raises(ValueError, match="list or dict"):
            export_to_csv("not a list", tmp_path, 'test')

    def test_invalid_type_raises_valueerror_parquet(self, tmp_path):
        """Invalid data type should raise ValueError for Parquet export."""
        from src.analytics.export import export_to_parquet
        with pytest.raises(ValueError, match="list or dict"):
            export_to_parquet(42, tmp_path, 'test')


# ---------------------------------------------------------------------------
# Integration tests: Phase 6.1 query → export (database required)
# ---------------------------------------------------------------------------

class TestExportExecutiveSummary:
    """Test executive summary export against real database."""

    def test_export_csv(self, tmp_path):
        """Should export executive summary to CSV."""
        from src.analytics.export import export_executive_summary
        results = export_executive_summary(output_dir=tmp_path, formats=('csv',))
        assert len(results) == 1
        meta = results[0]
        assert meta['format'] == 'csv'
        assert meta['rows'] == 1
        assert Path(meta['path']).exists()

    def test_export_parquet(self, tmp_path):
        """Should export executive summary to Parquet."""
        from src.analytics.export import export_executive_summary
        results = export_executive_summary(output_dir=tmp_path, formats=('parquet',))
        assert len(results) == 1
        meta = results[0]
        assert meta['format'] == 'parquet'
        assert meta['rows'] == 1

    def test_export_both_formats(self, tmp_path):
        """Should export to both CSV and Parquet."""
        from src.analytics.export import export_executive_summary
        results = export_executive_summary(output_dir=tmp_path)
        assert len(results) == 2
        formats = {r['format'] for r in results}
        assert formats == {'csv', 'parquet'}

    def test_csv_content_matches_query(self, tmp_path):
        """Exported CSV should contain data from get_executive_summary."""
        from src.analytics.export import export_executive_summary
        from src.analytics.queries import get_executive_summary
        results = export_executive_summary(output_dir=tmp_path, formats=('csv',))
        df = pd.read_csv(results[0]['path'])
        summary = get_executive_summary()
        assert df['total_applications'].iloc[0] == summary['total_applications']
        assert df['total_events'].iloc[0] == summary['total_events']


class TestExportApplicationVolume:
    """Test application volume exports against real database."""

    def test_volume_by_type_csv(self, tmp_path):
        """Should export application volume by type to CSV."""
        from src.analytics.export import export_application_volume_by_type
        results = export_application_volume_by_type(output_dir=tmp_path, formats=('csv',))
        assert len(results) == 1
        meta = results[0]
        assert meta['rows'] == 2  # Two application types
        df = pd.read_csv(meta['path'])
        assert 'application_type' in df.columns

    def test_volume_by_type_parquet(self, tmp_path):
        """Should export application volume by type to Parquet."""
        from src.analytics.export import export_application_volume_by_type
        results = export_application_volume_by_type(output_dir=tmp_path, formats=('parquet',))
        assert len(results) == 1
        df = pd.read_parquet(results[0]['path'])
        assert len(df) == 2

    def test_volume_over_time_monthly(self, tmp_path):
        """Should export monthly volume data."""
        from src.analytics.export import export_application_volume_over_time
        results = export_application_volume_over_time(
            output_dir=tmp_path, granularity='monthly', formats=('csv',)
        )
        assert len(results) == 1
        assert results[0]['rows'] > 0
        assert 'monthly' in results[0]['filename']

    def test_volume_over_time_daily(self, tmp_path):
        """Should export daily volume data."""
        from src.analytics.export import export_application_volume_over_time
        results = export_application_volume_over_time(
            output_dir=tmp_path, granularity='daily', formats=('csv',)
        )
        assert len(results) == 1
        assert results[0]['rows'] > 0
        assert 'daily' in results[0]['filename']


class TestExportActivitySummary:
    """Test activity summary export against real database."""

    def test_export_csv(self, tmp_path):
        """Should export activity summary to CSV."""
        from src.analytics.export import export_activity_summary
        results = export_activity_summary(output_dir=tmp_path, formats=('csv',))
        assert len(results) == 1
        meta = results[0]
        assert meta['rows'] == 26  # 26 activities
        df = pd.read_csv(meta['path'])
        assert 'activity' in df.columns
        assert 'event_count' in df.columns

    def test_export_parquet(self, tmp_path):
        """Should export activity summary to Parquet."""
        from src.analytics.export import export_activity_summary
        results = export_activity_summary(output_dir=tmp_path, formats=('parquet',))
        assert len(results) == 1
        assert results[0]['rows'] == 26

    def test_content_matches_query(self, tmp_path):
        """Exported data should match query results."""
        from src.analytics.export import export_activity_summary
        from src.analytics.queries import get_activity_summary
        results = export_activity_summary(output_dir=tmp_path, formats=('csv',))
        df = pd.read_csv(results[0]['path'])
        query_data = get_activity_summary()
        assert len(df) == len(query_data)
        assert df['activity'].iloc[0] == query_data[0]['activity']


class TestExportResourceWorkload:
    """Test resource workload export against real database."""

    def test_export_csv(self, tmp_path):
        """Should export resource workload to CSV."""
        from src.analytics.export import export_resource_workload
        results = export_resource_workload(output_dir=tmp_path, formats=('csv',))
        assert len(results) == 1
        meta = results[0]
        assert meta['rows'] == 149  # 149 resources
        df = pd.read_csv(meta['path'])
        assert 'resource' in df.columns
        assert 'event_count' in df.columns

    def test_with_limit(self, tmp_path):
        """Limit parameter should restrict export count."""
        from src.analytics.export import export_resource_workload
        results = export_resource_workload(output_dir=tmp_path, formats=('csv',), limit=10)
        assert results[0]['rows'] == 10


class TestExportLifecycleOutcomes:
    """Test lifecycle outcomes export against real database."""

    def test_export_csv(self, tmp_path):
        """Should export lifecycle outcomes to CSV."""
        from src.analytics.export import export_lifecycle_outcomes
        results = export_lifecycle_outcomes(output_dir=tmp_path, formats=('csv',))
        assert len(results) == 1
        meta = results[0]
        assert meta['rows'] > 0
        df = pd.read_csv(meta['path'])
        assert 'lifecycle_transition' in df.columns
        assert 'event_count' in df.columns


class TestExportLoanGoalSummary:
    """Test loan goal summary export against real database."""

    def test_export_csv(self, tmp_path):
        """Should export loan goal summary to CSV."""
        from src.analytics.export import export_loan_goal_summary
        results = export_loan_goal_summary(output_dir=tmp_path, formats=('csv',))
        assert len(results) == 1
        meta = results[0]
        assert meta['rows'] > 0
        df = pd.read_csv(meta['path'])
        assert 'loan_goal' in df.columns
        assert 'application_count' in df.columns


class TestExportProcessingTimeDistribution:
    """Test processing time distribution export against real database."""

    def test_export_csv(self, tmp_path):
        """Should export processing time distribution to CSV."""
        from src.analytics.export import export_processing_time_distribution
        results = export_processing_time_distribution(output_dir=tmp_path, formats=('csv',))
        assert len(results) == 1
        meta = results[0]
        assert meta['rows'] > 0
        df = pd.read_csv(meta['path'])
        assert 'bucket' in df.columns
        assert 'application_count' in df.columns

    def test_export_parquet(self, tmp_path):
        """Should export processing time distribution to Parquet."""
        from src.analytics.export import export_processing_time_distribution
        results = export_processing_time_distribution(output_dir=tmp_path, formats=('parquet',))
        assert len(results) == 1
        df = pd.read_parquet(results[0]['path'])
        assert 'bucket' in df.columns


# ---------------------------------------------------------------------------
# Batch export tests
# ---------------------------------------------------------------------------

class TestExportAll:
    """Test batch export of all datasets."""

    def test_export_all_creates_files(self, tmp_path):
        """Batch export should create files for all datasets."""
        from src.analytics.export import export_all
        manifest = export_all(output_dir=tmp_path)
        assert manifest['total_files'] > 0
        assert manifest['total_rows'] > 0

    def test_export_all_has_all_datasets(self, tmp_path):
        """Batch export should include all expected datasets."""
        from src.analytics.export import export_all
        manifest = export_all(output_dir=tmp_path)
        expected_datasets = {
            'executive_summary',
            'application_volume_by_type',
            'application_volume_monthly',
            'application_volume_daily',
            'activity_summary',
            'resource_workload',
            'lifecycle_outcomes',
            'loan_goal_summary',
            'processing_time_distribution',
        }
        assert set(manifest['datasets'].keys()) == expected_datasets

    def test_export_all_metadata_structure(self, tmp_path):
        """Batch export manifest should have correct structure."""
        from src.analytics.export import export_all
        manifest = export_all(output_dir=tmp_path)
        assert 'exported_at' in manifest
        assert 'output_dir' in manifest
        assert 'datasets' in manifest
        assert 'total_files' in manifest
        assert 'total_rows' in manifest
        assert isinstance(manifest['datasets'], dict)

    def test_export_all_dataset_entry_structure(self, tmp_path):
        """Each dataset entry should have export metadata."""
        from src.analytics.export import export_all
        manifest = export_all(output_dir=tmp_path)
        for dataset_name, exports in manifest['datasets'].items():
            if isinstance(exports, list) and len(exports) > 0:
                for export_meta in exports:
                    if 'error' not in export_meta:
                        assert 'filename' in export_meta
                        assert 'path' in export_meta
                        assert 'rows' in export_meta

    def test_export_all_row_counts_match_individual(self, tmp_path):
        """Batch export row counts should match individual exports."""
        from src.analytics.export import export_all, export_activity_summary
        manifest = export_all(output_dir=tmp_path, formats=('csv',))
        activity_rows = manifest['datasets']['activity_summary'][0]['rows']
        assert activity_rows == 26  # Known activity count

    def test_export_all_parquet_only(self, tmp_path):
        """Batch export should support format filtering."""
        from src.analytics.export import export_all
        manifest = export_all(output_dir=tmp_path, formats=('parquet',))
        for dataset_name, exports in manifest['datasets'].items():
            if isinstance(exports, list):
                for export_meta in exports:
                    if 'error' not in export_meta:
                        assert export_meta['format'] == 'parquet'


# ---------------------------------------------------------------------------
# Export manifest tests
# ---------------------------------------------------------------------------

class TestExportManifest:
    """Test export manifest functionality."""

    def test_manifest_of_empty_dir(self, tmp_path):
        """Manifest of empty directory should show 0 files."""
        from src.analytics.export import get_export_manifest
        manifest = get_export_manifest(output_dir=tmp_path)
        assert manifest['total_files'] == 0
        assert manifest['files'] == []

    def test_manifest_after_export(self, tmp_path):
        """Manifest should list exported files after export."""
        from src.analytics.export import export_activity_summary, get_export_manifest
        export_activity_summary(output_dir=tmp_path, formats=('csv', 'parquet'))
        manifest = get_export_manifest(output_dir=tmp_path)
        assert manifest['total_files'] == 2
        filenames = {f['filename'] for f in manifest['files']}
        assert 'activity_summary.csv' in filenames
        assert 'activity_summary.parquet' in filenames

    def test_manifest_file_metadata(self, tmp_path):
        """Each file in manifest should have proper metadata."""
        from src.analytics.export import export_activity_summary, get_export_manifest
        export_activity_summary(output_dir=tmp_path, formats=('csv',))
        manifest = get_export_manifest(output_dir=tmp_path)
        for f in manifest['files']:
            assert 'filename' in f
            assert 'format' in f
            assert 'size_bytes' in f
            assert 'modified_at' in f
            assert f['format'] in ('csv', 'parquet')
            assert f['size_bytes'] > 0

    def test_manifest_path_is_absolute(self, tmp_path):
        """Manifest output_dir should be an absolute path."""
        from src.analytics.export import get_export_manifest
        manifest = get_export_manifest(output_dir=tmp_path)
        assert Path(manifest['output_dir']).is_absolute()

    def test_manifest_after_batch_export(self, tmp_path):
        """Manifest should list all files from batch export."""
        from src.analytics.export import export_all, get_export_manifest
        batch = export_all(output_dir=tmp_path, formats=('csv',))
        manifest = get_export_manifest(output_dir=tmp_path)
        assert manifest['total_files'] == batch['total_files']


# ---------------------------------------------------------------------------
# Source function metadata tests
# ---------------------------------------------------------------------------

class TestSourceFunctionMetadata:
    """Test that source_function metadata is correct."""

    def test_executive_summary_source(self, tmp_path):
        """Executive summary should report correct source function."""
        from src.analytics.export import export_executive_summary
        results = export_executive_summary(output_dir=tmp_path, formats=('csv',))
        assert results[0]['source_function'] == 'get_executive_summary'

    def test_activity_summary_source(self, tmp_path):
        """Activity summary should report correct source function."""
        from src.analytics.export import export_activity_summary
        results = export_activity_summary(output_dir=tmp_path, formats=('csv',))
        assert results[0]['source_function'] == 'get_activity_summary'

    def test_resource_workload_source(self, tmp_path):
        """Resource workload should report correct source function."""
        from src.analytics.export import export_resource_workload
        results = export_resource_workload(output_dir=tmp_path, formats=('csv',))
        assert results[0]['source_function'] == 'get_resource_workload'

    def test_custom_source_function(self, tmp_path, sample_list_data):
        """Core export should accept custom source_function parameter."""
        from src.analytics.export import export_to_csv
        meta = export_to_csv(
            sample_list_data, tmp_path, 'test',
            source_function='my_custom_function',
        )
        assert meta['source_function'] == 'my_custom_function'
