"""Analytics Export Module for CSV and Parquet Generation.

This module provides functions to export analytics query results (from Phase 6.1)
to CSV and Parquet files for downstream consumption by Power BI, pandas, or other
analytics tools.

All exports use Phase 6.1 query functions as data sources — no SQL duplication.
Exports are written to a configurable output directory (default: reports/generated/analytics/).

Supported formats:
- CSV (universal compatibility, UTF-8 encoded)
- Parquet (columnar, compressed, efficient for large datasets)

Each export returns metadata about the written file (path, row count, size).
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


# Default export directory (relative to project root)
DEFAULT_EXPORT_DIR = Path("reports/generated/analytics")


def _ensure_output_dir(output_dir: Path) -> Path:
    """Ensure the output directory exists, create if necessary.

    Args:
        output_dir: Target directory path.

    Returns:
        Resolved absolute Path of the directory.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir.resolve()


def _build_export_metadata(
    filename: str,
    output_path: Path,
    row_count: int,
    format_type: str,
    source_function: str,
) -> dict[str, Any]:
    """Build metadata dict for an export operation.

    Args:
        filename: Name of the exported file.
        output_path: Full path of the exported file.
        row_count: Number of rows exported.
        format_type: 'csv' or 'parquet'.
        source_function: Name of the query function used.

    Returns:
        Dict with export metadata.
    """
    file_size = os.path.getsize(output_path) if output_path.exists() else 0
    return {
        'filename': filename,
        'path': str(output_path),
        'format': format_type,
        'rows': row_count,
        'size_bytes': file_size,
        'source_function': source_function,
        'exported_at': datetime.now(timezone.utc).isoformat(),
    }


def export_to_csv(
    data: list[dict[str, Any]] | dict[str, Any],
    output_dir: Path | str,
    filename: str,
    source_function: str = 'unknown',
) -> dict[str, Any]:
    """Export analytics data to a CSV file.

    Args:
        data: List of dicts or single dict to export. If a single dict, it is
              exported as a single-row CSV (for summary/metadata exports).
        output_dir: Directory to write the CSV file.
        filename: Name of the CSV file (without extension, .csv appended).
        source_function: Name of the source query function (for metadata).

    Returns:
        Dict with export metadata (filename, path, rows, size, etc.).

    Raises:
        ValueError: If data is empty or not a list/dict.
        OSError: If the file cannot be written.
    """
    if data is None:
        raise ValueError("Data cannot be None")

    # Normalize to list of dicts
    if isinstance(data, dict):
        rows = [data]
    elif isinstance(data, list):
        rows = data
    else:
        raise ValueError(f"Data must be a list or dict, got {type(data).__name__}")

    if len(rows) == 0:
        raise ValueError("Data is empty — nothing to export")

    out_dir = _ensure_output_dir(Path(output_dir))
    csv_filename = f"{filename}.csv"
    csv_path = out_dir / csv_filename

    df = pd.DataFrame(rows)
    df.to_csv(csv_path, index=False, encoding='utf-8')

    return _build_export_metadata(
        filename=csv_filename,
        output_path=csv_path,
        row_count=len(rows),
        format_type='csv',
        source_function=source_function,
    )


def export_to_parquet(
    data: list[dict[str, Any]] | dict[str, Any],
    output_dir: Path | str,
    filename: str,
    source_function: str = 'unknown',
) -> dict[str, Any]:
    """Export analytics data to a Parquet file.

    Args:
        data: List of dicts or single dict to export.
        output_dir: Directory to write the Parquet file.
        filename: Name of the Parquet file (without extension, .parquet appended).
        source_function: Name of the source query function (for metadata).

    Returns:
        Dict with export metadata (filename, path, rows, size, etc.).

    Raises:
        ValueError: If data is empty or not a list/dict.
        OSError: If the file cannot be written.
    """
    if data is None:
        raise ValueError("Data cannot be None")

    if isinstance(data, dict):
        rows = [data]
    elif isinstance(data, list):
        rows = data
    else:
        raise ValueError(f"Data must be a list or dict, got {type(data).__name__}")

    if len(rows) == 0:
        raise ValueError("Data is empty — nothing to export")

    out_dir = _ensure_output_dir(Path(output_dir))
    parquet_filename = f"{filename}.parquet"
    parquet_path = out_dir / parquet_filename

    df = pd.DataFrame(rows)
    df.to_parquet(parquet_path, index=False)

    return _build_export_metadata(
        filename=parquet_filename,
        output_path=parquet_path,
        row_count=len(rows),
        format_type='parquet',
        source_function=source_function,
    )


def export_executive_summary(
    output_dir: Path | str | None = None,
    formats: tuple[str, ...] = ('csv', 'parquet'),
) -> list[dict[str, Any]]:
    """Export executive summary to CSV and/or Parquet.

    Uses: src.analytics.queries.get_executive_summary()

    Args:
        output_dir: Target directory. Defaults to reports/generated/analytics/.
        formats: Tuple of format strings ('csv', 'parquet').

    Returns:
        List of export metadata dicts (one per format).
    """
    from src.analytics.queries import get_executive_summary

    data = get_executive_summary()
    out_dir = Path(output_dir) if output_dir else DEFAULT_EXPORT_DIR
    results = []

    if 'csv' in formats:
        results.append(export_to_csv(
            data, out_dir, 'executive_summary',
            source_function='get_executive_summary',
        ))
    if 'parquet' in formats:
        results.append(export_to_parquet(
            data, out_dir, 'executive_summary',
            source_function='get_executive_summary',
        ))

    return results


def export_application_volume_by_type(
    output_dir: Path | str | None = None,
    formats: tuple[str, ...] = ('csv', 'parquet'),
) -> list[dict[str, Any]]:
    """Export application volume by type to CSV and/or Parquet.

    Uses: src.analytics.queries.get_application_volume_by_type()

    Args:
        output_dir: Target directory. Defaults to reports/generated/analytics/.
        formats: Tuple of format strings ('csv', 'parquet').

    Returns:
        List of export metadata dicts (one per format).
    """
    from src.analytics.queries import get_application_volume_by_type

    data = get_application_volume_by_type()
    out_dir = Path(output_dir) if output_dir else DEFAULT_EXPORT_DIR
    results = []

    if 'csv' in formats:
        results.append(export_to_csv(
            data, out_dir, 'application_volume_by_type',
            source_function='get_application_volume_by_type',
        ))
    if 'parquet' in formats:
        results.append(export_to_parquet(
            data, out_dir, 'application_volume_by_type',
            source_function='get_application_volume_by_type',
        ))

    return results


def export_application_volume_over_time(
    output_dir: Path | str | None = None,
    granularity: str = 'monthly',
    formats: tuple[str, ...] = ('csv', 'parquet'),
) -> list[dict[str, Any]]:
    """Export application volume over time to CSV and/or Parquet.

    Uses: src.analytics.queries.get_application_volume_over_time()

    Args:
        output_dir: Target directory. Defaults to reports/generated/analytics/.
        granularity: 'monthly' or 'daily'.
        formats: Tuple of format strings ('csv', 'parquet').

    Returns:
        List of export metadata dicts (one per format).
    """
    from src.analytics.queries import get_application_volume_over_time

    data = get_application_volume_over_time(granularity=granularity)
    out_dir = Path(output_dir) if output_dir else DEFAULT_EXPORT_DIR
    suffix = f"_by_{granularity}"
    results = []

    if 'csv' in formats:
        results.append(export_to_csv(
            data, out_dir, f'application_volume{suffix}',
            source_function='get_application_volume_over_time',
        ))
    if 'parquet' in formats:
        results.append(export_to_parquet(
            data, out_dir, f'application_volume{suffix}',
            source_function='get_application_volume_over_time',
        ))

    return results


def export_activity_summary(
    output_dir: Path | str | None = None,
    formats: tuple[str, ...] = ('csv', 'parquet'),
) -> list[dict[str, Any]]:
    """Export activity summary to CSV and/or Parquet.

    Uses: src.analytics.queries.get_activity_summary()

    Args:
        output_dir: Target directory. Defaults to reports/generated/analytics/.
        formats: Tuple of format strings ('csv', 'parquet').

    Returns:
        List of export metadata dicts (one per format).
    """
    from src.analytics.queries import get_activity_summary

    data = get_activity_summary()
    out_dir = Path(output_dir) if output_dir else DEFAULT_EXPORT_DIR
    results = []

    if 'csv' in formats:
        results.append(export_to_csv(
            data, out_dir, 'activity_summary',
            source_function='get_activity_summary',
        ))
    if 'parquet' in formats:
        results.append(export_to_parquet(
            data, out_dir, 'activity_summary',
            source_function='get_activity_summary',
        ))

    return results


def export_resource_workload(
    output_dir: Path | str | None = None,
    formats: tuple[str, ...] = ('csv', 'parquet'),
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Export resource workload distribution to CSV and/or Parquet.

    Uses: src.analytics.queries.get_resource_workload()

    Args:
        output_dir: Target directory. Defaults to reports/generated/analytics/.
        formats: Tuple of format strings ('csv', 'parquet').
        limit: Optional limit on number of resources exported.

    Returns:
        List of export metadata dicts (one per format).
    """
    from src.analytics.queries import get_resource_workload

    data = get_resource_workload(limit=limit)
    out_dir = Path(output_dir) if output_dir else DEFAULT_EXPORT_DIR
    results = []

    if 'csv' in formats:
        results.append(export_to_csv(
            data, out_dir, 'resource_workload',
            source_function='get_resource_workload',
        ))
    if 'parquet' in formats:
        results.append(export_to_parquet(
            data, out_dir, 'resource_workload',
            source_function='get_resource_workload',
        ))

    return results


def export_lifecycle_outcomes(
    output_dir: Path | str | None = None,
    formats: tuple[str, ...] = ('csv', 'parquet'),
) -> list[dict[str, Any]]:
    """Export lifecycle outcome summary to CSV and/or Parquet.

    Uses: src.analytics.queries.get_lifecycle_outcome_summary()

    Args:
        output_dir: Target directory. Defaults to reports/generated/analytics/.
        formats: Tuple of format strings ('csv', 'parquet').

    Returns:
        List of export metadata dicts (one per format).
    """
    from src.analytics.queries import get_lifecycle_outcome_summary

    data = get_lifecycle_outcome_summary()
    out_dir = Path(output_dir) if output_dir else DEFAULT_EXPORT_DIR
    results = []

    if 'csv' in formats:
        results.append(export_to_csv(
            data, out_dir, 'lifecycle_outcomes',
            source_function='get_lifecycle_outcome_summary',
        ))
    if 'parquet' in formats:
        results.append(export_to_parquet(
            data, out_dir, 'lifecycle_outcomes',
            source_function='get_lifecycle_outcome_summary',
        ))

    return results


def export_loan_goal_summary(
    output_dir: Path | str | None = None,
    formats: tuple[str, ...] = ('csv', 'parquet'),
) -> list[dict[str, Any]]:
    """Export loan goal summary to CSV and/or Parquet.

    Uses: src.analytics.queries.get_loan_goal_summary()

    Args:
        output_dir: Target directory. Defaults to reports/generated/analytics/.
        formats: Tuple of format strings ('csv', 'parquet').

    Returns:
        List of export metadata dicts (one per format).
    """
    from src.analytics.queries import get_loan_goal_summary

    data = get_loan_goal_summary()
    out_dir = Path(output_dir) if output_dir else DEFAULT_EXPORT_DIR
    results = []

    if 'csv' in formats:
        results.append(export_to_csv(
            data, out_dir, 'loan_goal_summary',
            source_function='get_loan_goal_summary',
        ))
    if 'parquet' in formats:
        results.append(export_to_parquet(
            data, out_dir, 'loan_goal_summary',
            source_function='get_loan_goal_summary',
        ))

    return results


def export_processing_time_distribution(
    output_dir: Path | str | None = None,
    formats: tuple[str, ...] = ('csv', 'parquet'),
) -> list[dict[str, Any]]:
    """Export processing time distribution to CSV and/or Parquet.

    Uses: src.analytics.queries.get_processing_time_distribution()

    Args:
        output_dir: Target directory. Defaults to reports/generated/analytics/.
        formats: Tuple of format strings ('csv', 'parquet').

    Returns:
        List of export metadata dicts (one per format).
    """
    from src.analytics.queries import get_processing_time_distribution

    data = get_processing_time_distribution()
    out_dir = Path(output_dir) if output_dir else DEFAULT_EXPORT_DIR
    results = []

    if 'csv' in formats:
        results.append(export_to_csv(
            data, out_dir, 'processing_time_distribution',
            source_function='get_processing_time_distribution',
        ))
    if 'parquet' in formats:
        results.append(export_to_parquet(
            data, out_dir, 'processing_time_distribution',
            source_function='get_processing_time_distribution',
        ))

    return results


def export_all(
    output_dir: Path | str | None = None,
    formats: tuple[str, ...] = ('csv', 'parquet'),
) -> dict[str, Any]:
    """Export all analytics datasets to CSV and/or Parquet.

    Batch export of all available analytics datasets. Returns a manifest
    of all exports with metadata.

    Args:
        output_dir: Target directory. Defaults to reports/generated/analytics/.
        formats: Tuple of format strings ('csv', 'parquet').

    Returns:
        Dict with keys:
        - exported_at: ISO timestamp of the batch export
        - output_dir: Absolute path of output directory
        - datasets: Dict mapping dataset name to list of export metadata
        - total_files: Total number of files written
        - total_rows: Sum of all exported rows
    """
    out_dir = Path(output_dir) if output_dir else DEFAULT_EXPORT_DIR
    datasets = {}

    exporters = [
        ('executive_summary', export_executive_summary),
        ('application_volume_by_type', export_application_volume_by_type),
        ('application_volume_monthly', lambda d, f: export_application_volume_over_time(d, 'monthly', f)),
        ('application_volume_daily', lambda d, f: export_application_volume_over_time(d, 'daily', f)),
        ('activity_summary', export_activity_summary),
        ('resource_workload', export_resource_workload),
        ('lifecycle_outcomes', export_lifecycle_outcomes),
        ('loan_goal_summary', export_loan_goal_summary),
        ('processing_time_distribution', export_processing_time_distribution),
    ]

    total_files = 0
    total_rows = 0

    for name, exporter in exporters:
        try:
            results = exporter(out_dir, formats)
            datasets[name] = results
            for meta in results:
                total_files += 1
                total_rows += meta['rows']
        except Exception as e:
            datasets[name] = [{'error': str(e)}]

    return {
        'exported_at': datetime.now(timezone.utc).isoformat(),
        'output_dir': str(_ensure_output_dir(out_dir)),
        'datasets': datasets,
        'total_files': total_files,
        'total_rows': total_rows,
    }


def get_export_manifest(output_dir: Path | str | None = None) -> dict[str, Any]:
    """List all exported files in the output directory.

    Scans the output directory for CSV and Parquet files and returns
    metadata about each.

    Args:
        output_dir: Directory to scan. Defaults to reports/generated/analytics/.

    Returns:
        Dict with keys:
        - output_dir: Absolute path
        - files: List of dicts with filename, format, size_bytes, modified_at
        - total_files: Count of export files
    """
    out_dir = Path(output_dir) if output_dir else DEFAULT_EXPORT_DIR
    out_dir = out_dir.resolve()

    files = []
    if out_dir.exists():
        for f in sorted(out_dir.iterdir()):
            if f.suffix in ('.csv', '.parquet'):
                stat = f.stat()
                files.append({
                    'filename': f.name,
                    'format': f.suffix.lstrip('.'),
                    'size_bytes': stat.st_size,
                    'modified_at': datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                })

    return {
        'output_dir': str(out_dir),
        'files': files,
        'total_files': len(files),
    }
