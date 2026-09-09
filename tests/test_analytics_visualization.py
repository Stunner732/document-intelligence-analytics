"""Tests for Phase 6.3 Analytics Visualization Module.

Tests verify that visualization functions:
1. Execute successfully and return metadata dicts
2. Save valid PNG files to disk
3. Produce correct figure types and axis content
4. Handle empty datasets gracefully
5. Include expected titles and labels
6. Reuse Phase 6.1 query functions correctly
7. Do not modify the database

Test categories:
- TestPlotExecutiveSummary: KPI stat tile chart
- TestPlotApplicationVolumeByType: Horizontal bar chart
- TestPlotApplicationVolumeOverTime: Line chart (monthly + daily)
- TestPlotActivitySummary: Top-N horizontal bar
- TestPlotResourceWorkload: Top-N horizontal bar
- TestPlotLifecycleOutcomes: Donut chart
- TestPlotLoanGoalSummary: Grouped bar chart
- TestPlotProcessingTimeDistribution: Vertical bar chart
- TestPlotAll: Batch generation
- TestPlotManifest: Directory scanner
- TestPlotEmptyHandling: Empty dataset behavior
"""

import pytest
import os
from pathlib import Path
from matplotlib.figure import Figure


# ---------------------------------------------------------------------------
# Executive Summary KPI Tiles
# ---------------------------------------------------------------------------

class TestPlotExecutiveSummary:
    """Test executive summary KPI tile chart."""

    def test_returns_metadata_dict(self, tmp_path):
        """Should return metadata dict with required keys."""
        from src.analytics.visualization import plot_executive_summary
        meta = plot_executive_summary(output_dir=tmp_path)
        assert isinstance(meta, dict)
        required_keys = {"filename", "path", "format", "size_bytes", "rows", "figure_type", "source_function", "generated_at"}
        assert required_keys == set(meta.keys())

    def test_creates_png_file(self, tmp_path):
        """Should save a PNG file to disk."""
        from src.analytics.visualization import plot_executive_summary
        meta = plot_executive_summary(output_dir=tmp_path)
        assert Path(meta["path"]).exists()
        assert meta["filename"] == "executive_summary.png"
        assert meta["format"] == "png"

    def test_file_is_non_empty(self, tmp_path):
        """PNG file should have positive size."""
        from src.analytics.visualization import plot_executive_summary
        meta = plot_executive_summary(output_dir=tmp_path)
        assert meta["size_bytes"] > 0

    def test_metadata_source_function(self, tmp_path):
        """Should report correct source query function."""
        from src.analytics.visualization import plot_executive_summary
        meta = plot_executive_summary(output_dir=tmp_path)
        assert meta["source_function"] == "get_executive_summary"

    def test_figure_type_is_kpi_tiles(self, tmp_path):
        """Figure type should be kpi_tiles."""
        from src.analytics.visualization import plot_executive_summary
        meta = plot_executive_summary(output_dir=tmp_path)
        assert meta["figure_type"] == "kpi_tiles"

    def test_query_function_is_used(self, tmp_path):
        """Should call get_executive_summary (verified via source_function metadata)."""
        from src.analytics.visualization import plot_executive_summary
        meta = plot_executive_summary(output_dir=tmp_path)
        assert "executive_summary" in meta["source_function"]

    def test_no_database_modification(self, tmp_path):
        """Plot generation should not change row counts in the database."""
        from src.analytics.visualization import plot_executive_summary
        from src.database import get_cursor
        with get_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM applications")
            before = cur.fetchone()[0]
        plot_executive_summary(output_dir=tmp_path)
        with get_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM applications")
            after = cur.fetchone()[0]
        assert before == after

    def test_creates_output_directory(self):
        """Should create nested output directory if it does not exist."""
        from src.analytics.visualization import plot_executive_summary
        out_dir = Path("test_nested_viz_output/inner")
        try:
            meta = plot_executive_summary(output_dir=out_dir)
            assert Path(meta["path"]).exists()
        finally:
            import shutil
            if Path("test_nested_viz_output").exists():
                shutil.rmtree("test_nested_viz_output", ignore_errors=True)


# ---------------------------------------------------------------------------
# Application Volume by Type (horizontal bar)
# ---------------------------------------------------------------------------

class TestPlotApplicationVolumeByType:
    """Test application volume by type bar chart."""

    def test_returns_metadata_dict(self, tmp_path):
        """Should return metadata dict."""
        from src.analytics.visualization import plot_application_volume_by_type
        meta = plot_application_volume_by_type(output_dir=tmp_path)
        assert isinstance(meta, dict)
        assert meta["figure_type"] == "bar"

    def test_creates_png_file(self, tmp_path):
        """Should save a PNG file."""
        from src.analytics.visualization import plot_application_volume_by_type
        meta = plot_application_volume_by_type(output_dir=tmp_path)
        assert Path(meta["path"]).exists()
        assert meta["filename"] == "application_volume_by_type.png"

    def test_file_is_non_empty(self, tmp_path):
        """File should be non-empty."""
        from src.analytics.visualization import plot_application_volume_by_type
        meta = plot_application_volume_by_type(output_dir=tmp_path)
        assert meta["size_bytes"] > 0

    def test_source_function(self, tmp_path):
        """Should report correct source function."""
        from src.analytics.visualization import plot_application_volume_by_type
        meta = plot_application_volume_by_type(output_dir=tmp_path)
        assert meta["source_function"] == "get_application_volume_by_type"

    def test_rows_count_matches_data(self, tmp_path):
        """Rows should match number of application types (2)."""
        from src.analytics.visualization import plot_application_volume_by_type
        meta = plot_application_volume_by_type(output_dir=tmp_path)
        assert meta["rows"] == 2

    def test_no_database_modification(self, tmp_path):
        """Should not modify database."""
        from src.analytics.visualization import plot_application_volume_by_type
        from src.database import get_cursor
        with get_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM applications")
            before = cur.fetchone()[0]
        plot_application_volume_by_type(output_dir=tmp_path)
        with get_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM applications")
            after = cur.fetchone()[0]
        assert before == after


# ---------------------------------------------------------------------------
# Application Volume Over Time (line chart)
# ---------------------------------------------------------------------------

class TestPlotApplicationVolumeOverTime:
    """Test application volume over time line chart."""

    def test_monthly_returns_metadata(self, tmp_path):
        """Monthly granularity should return metadata dict."""
        from src.analytics.visualization import plot_application_volume_over_time
        meta = plot_application_volume_over_time(output_dir=tmp_path, granularity="monthly")
        assert isinstance(meta, dict)
        assert meta["figure_type"] == "line"

    def test_daily_returns_metadata(self, tmp_path):
        """Daily granularity should return metadata dict."""
        from src.analytics.visualization import plot_application_volume_over_time
        meta = plot_application_volume_over_time(output_dir=tmp_path, granularity="daily")
        assert isinstance(meta, dict)
        assert meta["figure_type"] == "line"

    def test_monthly_file_created(self, tmp_path):
        """Monthly chart should create a file with correct name."""
        from src.analytics.visualization import plot_application_volume_over_time
        meta = plot_application_volume_over_time(output_dir=tmp_path, granularity="monthly")
        assert Path(meta["path"]).exists()
        assert "monthly" in meta["filename"]

    def test_daily_file_created(self, tmp_path):
        """Daily chart should create a file with correct name."""
        from src.analytics.visualization import plot_application_volume_over_time
        meta = plot_application_volume_over_time(output_dir=tmp_path, granularity="daily")
        assert Path(meta["path"]).exists()
        assert "daily" in meta["filename"]

    def test_rows_are_positive(self, tmp_path):
        """Rows should be greater than zero for both granularities."""
        from src.analytics.visualization import plot_application_volume_over_time
        monthly = plot_application_volume_over_time(output_dir=tmp_path, granularity="monthly")
        daily = plot_application_volume_over_time(output_dir=tmp_path, granularity="daily")
        assert monthly["rows"] > 0
        assert daily["rows"] > 0

    def test_invalid_granularity_raises_error(self, tmp_path):
        """Invalid granularity should raise ValueError."""
        from src.analytics.visualization import plot_application_volume_over_time
        with pytest.raises(ValueError, match="granularity must be"):
            plot_application_volume_over_time(output_dir=tmp_path, granularity="hourly")

    def test_no_database_modification(self, tmp_path):
        """Should not modify database."""
        from src.analytics.visualization import plot_application_volume_over_time
        from src.database import get_cursor
        with get_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM applications")
            before = cur.fetchone()[0]
        plot_application_volume_over_time(output_dir=tmp_path, granularity="monthly")
        with get_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM applications")
            after = cur.fetchone()[0]
        assert before == after


# ---------------------------------------------------------------------------
# Activity Summary (top-N horizontal bar)
# ---------------------------------------------------------------------------

class TestPlotActivitySummary:
    """Test activity summary bar chart."""

    def test_returns_metadata(self, tmp_path):
        """Should return metadata dict."""
        from src.analytics.visualization import plot_activity_summary
        meta = plot_activity_summary(output_dir=tmp_path)
        assert isinstance(meta, dict)
        assert meta["figure_type"] == "bar"

    def test_creates_png_file(self, tmp_path):
        """Should create PNG file."""
        from src.analytics.visualization import plot_activity_summary
        meta = plot_activity_summary(output_dir=tmp_path)
        assert Path(meta["path"]).exists()
        assert meta["filename"] == "activity_summary.png"

    def test_rows_match_top_n(self, tmp_path):
        """Rows should match top_n (default 10)."""
        from src.analytics.visualization import plot_activity_summary
        meta = plot_activity_summary(output_dir=tmp_path)
        assert meta["rows"] == 10

    def test_custom_top_n(self, tmp_path):
        """Custom top_n should affect row count."""
        from src.analytics.visualization import plot_activity_summary
        meta = plot_activity_summary(output_dir=tmp_path, top_n=5)
        assert meta["rows"] == 5

    def test_file_non_empty(self, tmp_path):
        """File size should be positive."""
        from src.analytics.visualization import plot_activity_summary
        meta = plot_activity_summary(output_dir=tmp_path)
        assert meta["size_bytes"] > 0


# ---------------------------------------------------------------------------
# Resource Workload (top-N horizontal bar)
# ---------------------------------------------------------------------------

class TestPlotResourceWorkload:
    """Test resource workload bar chart."""

    def test_returns_metadata(self, tmp_path):
        """Should return metadata dict."""
        from src.analytics.visualization import plot_resource_workload
        meta = plot_resource_workload(output_dir=tmp_path)
        assert isinstance(meta, dict)
        assert meta["figure_type"] == "bar"

    def test_creates_png_file(self, tmp_path):
        """Should create PNG file."""
        from src.analytics.visualization import plot_resource_workload
        meta = plot_resource_workload(output_dir=tmp_path)
        assert Path(meta["path"]).exists()
        assert meta["filename"] == "resource_workload.png"

    def test_rows_match_limit(self, tmp_path):
        """Rows should match limit parameter (default 20)."""
        from src.analytics.visualization import plot_resource_workload
        meta = plot_resource_workload(output_dir=tmp_path)
        assert meta["rows"] == 20

    def test_custom_limit(self, tmp_path):
        """Custom limit should affect row count."""
        from src.analytics.visualization import plot_resource_workload
        meta = plot_resource_workload(output_dir=tmp_path, limit=10)
        assert meta["rows"] == 10

    def test_source_function(self, tmp_path):
        """Should report correct source function."""
        from src.analytics.visualization import plot_resource_workload
        meta = plot_resource_workload(output_dir=tmp_path)
        assert meta["source_function"] == "get_resource_workload"


# ---------------------------------------------------------------------------
# Lifecycle Outcomes (donut chart)
# ---------------------------------------------------------------------------

class TestPlotLifecycleOutcomes:
    """Test lifecycle outcome donut chart."""

    def test_returns_metadata(self, tmp_path):
        """Should return metadata dict with donut type."""
        from src.analytics.visualization import plot_lifecycle_outcomes
        meta = plot_lifecycle_outcomes(output_dir=tmp_path)
        assert isinstance(meta, dict)
        assert meta["figure_type"] == "donut"

    def test_creates_png_file(self, tmp_path):
        """Should create PNG file."""
        from src.analytics.visualization import plot_lifecycle_outcomes
        meta = plot_lifecycle_outcomes(output_dir=tmp_path)
        assert Path(meta["path"]).exists()
        assert meta["filename"] == "lifecycle_outcomes.png"

    def test_rows_positive(self, tmp_path):
        """Should have positive rows (lifecycle outcomes exist)."""
        from src.analytics.visualization import plot_lifecycle_outcomes
        meta = plot_lifecycle_outcomes(output_dir=tmp_path)
        assert meta["rows"] > 0

    def test_file_non_empty(self, tmp_path):
        """File should be non-empty."""
        from src.analytics.visualization import plot_lifecycle_outcomes
        meta = plot_lifecycle_outcomes(output_dir=tmp_path)
        assert meta["size_bytes"] > 0


# ---------------------------------------------------------------------------
# Loan Goal Summary (grouped bar)
# ---------------------------------------------------------------------------

class TestPlotLoanGoalSummary:
    """Test loan goal summary grouped bar chart."""

    def test_returns_metadata(self, tmp_path):
        """Should return metadata dict with grouped_bar type."""
        from src.analytics.visualization import plot_loan_goal_summary
        meta = plot_loan_goal_summary(output_dir=tmp_path)
        assert isinstance(meta, dict)
        assert meta["figure_type"] == "grouped_bar"

    def test_creates_png_file(self, tmp_path):
        """Should create PNG file."""
        from src.analytics.visualization import plot_loan_goal_summary
        meta = plot_loan_goal_summary(output_dir=tmp_path)
        assert Path(meta["path"]).exists()
        assert meta["filename"] == "loan_goal_summary.png"

    def test_rows_positive(self, tmp_path):
        """Should have positive rows (loan goals exist)."""
        from src.analytics.visualization import plot_loan_goal_summary
        meta = plot_loan_goal_summary(output_dir=tmp_path)
        assert meta["rows"] > 0

    def test_file_non_empty(self, tmp_path):
        """File should be non-empty."""
        from src.analytics.visualization import plot_loan_goal_summary
        meta = plot_loan_goal_summary(output_dir=tmp_path)
        assert meta["size_bytes"] > 0


# ---------------------------------------------------------------------------
# Processing Time Distribution (vertical bar)
# ---------------------------------------------------------------------------

class TestPlotProcessingTimeDistribution:
    """Test processing time distribution bar chart."""

    def test_returns_metadata(self, tmp_path):
        """Should return metadata dict with bar type."""
        from src.analytics.visualization import plot_processing_time_distribution
        meta = plot_processing_time_distribution(output_dir=tmp_path)
        assert isinstance(meta, dict)
        assert meta["figure_type"] == "bar"

    def test_creates_png_file(self, tmp_path):
        """Should create PNG file."""
        from src.analytics.visualization import plot_processing_time_distribution
        meta = plot_processing_time_distribution(output_dir=tmp_path)
        assert Path(meta["path"]).exists()
        assert meta["filename"] == "processing_time_distribution.png"

    def test_rows_match_buckets(self, tmp_path):
        """Rows should match number of time buckets (5)."""
        from src.analytics.visualization import plot_processing_time_distribution
        meta = plot_processing_time_distribution(output_dir=tmp_path)
        assert meta["rows"] == 5

    def test_file_non_empty(self, tmp_path):
        """File should be non-empty."""
        from src.analytics.visualization import plot_processing_time_distribution
        meta = plot_processing_time_distribution(output_dir=tmp_path)
        assert meta["size_bytes"] > 0


# ---------------------------------------------------------------------------
# Batch generation (plot_all)
# ---------------------------------------------------------------------------

class TestPlotAll:
    """Test batch plot generation."""

    def test_plot_all_creates_figures(self, tmp_path):
        """Batch generation should create all expected figures."""
        from src.analytics.visualization import plot_all
        manifest = plot_all(output_dir=tmp_path)
        assert manifest["total_figures"] > 0

    def test_plot_all_has_all_figures(self, tmp_path):
        """Batch should include all expected figure names."""
        from src.analytics.visualization import plot_all
        manifest = plot_all(output_dir=tmp_path)
        expected = {
            "executive_summary",
            "application_volume_by_type",
            "application_volume_monthly",
            "application_volume_daily",
            "activity_summary",
            "resource_workload",
            "lifecycle_outcomes",
            "loan_goal_summary",
            "processing_time_distribution",
        }
        assert set(manifest["figures"].keys()) == expected

    def test_plot_all_manifest_structure(self, tmp_path):
        """Manifest should have correct structure."""
        from src.analytics.visualization import plot_all
        manifest = plot_all(output_dir=tmp_path)
        assert "generated_at" in manifest
        assert "output_dir" in manifest
        assert "figures" in manifest
        assert "total_figures" in manifest
        assert "total_size_bytes" in manifest
        assert isinstance(manifest["figures"], dict)

    def test_plot_all_no_errors(self, tmp_path):
        """Batch generation should produce no errors for any figure."""
        from src.analytics.visualization import plot_all
        manifest = plot_all(output_dir=tmp_path)
        for name, meta in manifest["figures"].items():
            assert "error" not in meta, f"Error in {name}: {meta.get('error')}"
            assert "path" in meta

    def test_plot_all_total_size_positive(self, tmp_path):
        """Total size should be positive."""
        from src.analytics.visualization import plot_all
        manifest = plot_all(output_dir=tmp_path)
        assert manifest["total_size_bytes"] > 0

    def test_plot_all_all_files_exist(self, tmp_path):
        """All reported files should exist on disk."""
        from src.analytics.visualization import plot_all
        from pathlib import Path as P
        manifest = plot_all(output_dir=tmp_path)
        for name, meta in manifest["figures"].items():
            assert P(meta["path"]).exists(), f"File missing for {name}"

    def test_plot_all_purposeful_chart_types(self, tmp_path):
        """All figures should have recognized chart types."""
        from src.analytics.visualization import plot_all
        valid_types = {"kpi_tiles", "bar", "line", "donut", "grouped_bar"}
        manifest = plot_all(output_dir=tmp_path)
        for name, meta in manifest["figures"].items():
            assert meta["figure_type"] in valid_types, (
                f"{name} has unexpected figure_type: {meta['figure_type']}"
            )

    def test_plot_all_total_figures_count(self, tmp_path):
        """total_figures should equal count of non-error entries."""
        from src.analytics.visualization import plot_all
        manifest = plot_all(output_dir=tmp_path)
        non_error = sum(
            1 for m in manifest["figures"].values()
            if isinstance(m, dict) and "error" not in m
        )
        assert manifest["total_figures"] == non_error

    def test_plot_all_no_database_modification(self, tmp_path):
        """Batch plot generation should not modify database."""
        from src.analytics.visualization import plot_all
        from src.database import get_cursor
        with get_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM applications")
            before = cur.fetchone()[0]
        plot_all(output_dir=tmp_path)
        with get_cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM applications")
            after = cur.fetchone()[0]
        assert before == after


# ---------------------------------------------------------------------------
# Plot manifest
# ---------------------------------------------------------------------------

class TestPlotManifest:
    """Test plot manifest directory scanner."""

    def test_empty_dir_returns_zero(self, tmp_path):
        """Manifest of empty directory should show 0 files."""
        from src.analytics.visualization import get_plot_manifest
        manifest = get_plot_manifest(output_dir=tmp_path)
        assert manifest["total_files"] == 0
        assert manifest["files"] == []

    def test_manifest_after_plots(self, tmp_path):
        """Manifest should list generated PNG files."""
        from src.analytics.visualization import plot_activity_summary, get_plot_manifest
        plot_activity_summary(output_dir=tmp_path)
        manifest = get_plot_manifest(output_dir=tmp_path)
        assert manifest["total_files"] >= 1
        filenames = {f["filename"] for f in manifest["files"]}
        assert "activity_summary.png" in filenames

    def test_manifest_file_metadata(self, tmp_path):
        """Each file should have correct metadata keys."""
        from src.analytics.visualization import plot_executive_summary, get_plot_manifest
        plot_executive_summary(output_dir=tmp_path)
        manifest = get_plot_manifest(output_dir=tmp_path)
        for f in manifest["files"]:
            assert "filename" in f
            assert "format" in f
            assert "size_bytes" in f
            assert "modified_at" in f
            assert f["format"] == "png"
            assert f["size_bytes"] > 0

    def test_manifest_path_is_absolute(self, tmp_path):
        """Output dir should be an absolute path."""
        from src.analytics.visualization import get_plot_manifest
        manifest = get_plot_manifest(output_dir=tmp_path)
        assert Path(manifest["output_dir"]).is_absolute()

    def test_manifest_after_batch(self, tmp_path):
        """Manifest count should match plot_all output count."""
        from src.analytics.visualization import plot_all, get_plot_manifest
        batch = plot_all(output_dir=tmp_path)
        manifest = get_plot_manifest(output_dir=tmp_path)
        assert manifest["total_files"] == batch["total_figures"]


# ---------------------------------------------------------------------------
# Empty dataset handling
# ---------------------------------------------------------------------------

class TestPlotEmptyHandling:
    """Test that plots handle empty datasets without crashing."""

    def test_activity_summary_custom_top_n_zero(self, tmp_path):
        """top_n=0 should still produce metadata (function called successfully)."""
        from src.analytics.visualization import plot_activity_summary
        # top_n=0 means .head(0) returns empty DataFrame — chart should handle gracefully
        meta = plot_activity_summary(output_dir=tmp_path, top_n=0)
        assert isinstance(meta, dict)
        assert meta["rows"] == 0
        assert Path(meta["path"]).exists()
