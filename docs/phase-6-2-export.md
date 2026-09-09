# Phase 6.2: Analytics Export Module

## Overview

Phase 6.2 extends the Phase 6 Python analytics layer with an export module that converts analytics query results (Phase 6.1) into portable data files. These files feed downstream consumers: Power BI data models, pandas/notebook workflows, and report generation pipelines.

**Status:** Phase 6.2 - Analytics Export Module ✅ COMPLETE
**Last Updated:** 2026-09-09

## Purpose

The Analytics Export Module serves as the **file-serialization layer** for Phase 6:

1. **Produces portable artifacts** (CSV, Parquet) from live PostgreSQL analytics queries
2. **Reuses Phase 6.1 query functions** as data sources — no SQL duplication
3. **Outputs to a governed directory** (`reports/generated/analytics/`) under `.gitignore`
4. **Supports Power BI direct consumption** (Parquet/CSV import)
5. **Tracks export provenance** (source function, row counts, timestamps)

## Architecture

```
src/analytics/export.py
    │
    ├─► src/analytics/queries.py (13 query functions from Phase 6.1)
    │
    ├─► src/database.py (connection management)
    │
    ├─► pandas.DataFrame (serialization engine)
    │
    └─► reports/generated/analytics/ (output artifacts)
         ├─ *.csv    (UTF-8, human-readable)
         └─ *.parquet (columnar, compressed, typed)

Dependencies:
    pandas   — DataFrame construction and CSV writing
    pyarrow  — Parquet writing (required for .to_parquet())
```

**Design Principles:**
- Each export function wraps exactly one Phase 6.1 query (stateless, idempotent)
- `export_all()` batch-exports every dataset and returns a manifest
- No hardcoded credentials, paths, or connection parameters
- Core helpers (`export_to_csv`, `export_to_parquet`) are format-agnostic and reusable

## Available Functions

### Core (Format-Agnostic)

| Function | Description | Returns |
|----------|-------------|---------|
| `export_to_csv(data, output_dir, filename, source_function)` | Generic CSV export | `dict` metadata |
| `export_to_parquet(data, output_dir, filename, source_function)` | Generic Parquet export | `dict` metadata |

### Dataset-Specific (Phase 6.1 Integration)

| Function | Source Query | Output Files | Rows (expected) |
|----------|-------------|--------------|-----------------|
| `export_executive_summary()` | `get_executive_summary()` | `executive_summary.csv` / `.parquet` | 1 |
| `export_application_volume_by_type()` | `get_application_volume_by_type()` | `application_volume_by_type.csv` / `.parquet` | 2 |
| `export_application_volume_over_time(granularity)` | `get_application_volume_over_time()` | `application_volume_by_{monthly/daily}.csv` / `.parquet` | 14+ / 300+ |
| `export_activity_summary()` | `get_activity_summary()` | `activity_summary.csv` / `.parquet` | 26 |
| `export_resource_workload(limit)` | `get_resource_workload()` | `resource_workload.csv` / `.parquet` | 149 (or limit) |
| `export_lifecycle_outcomes()` | `get_lifecycle_outcome_summary()` | `lifecycle_outcomes.csv` / `.parquet` | 5+ |
| `export_loan_goal_summary()` | `get_loan_goal_summary()` | `loan_goal_summary.csv` / `.parquet` | 6+ |
| `export_processing_time_distribution()` | `get_processing_time_distribution()` | `processing_time_distribution.csv` / `.parquet` | 5 |

### Batch & Manifest

| Function | Description | Returns |
|----------|-------------|---------|
| `export_all(output_dir, formats)` | Batch-export all datasets | `dict` manifest with per-dataset metadata |
| `get_export_manifest(output_dir)` | List exported files in output directory | `dict` with file list and sizes |

### Metadata Schema

Each export returns a metadata dict:

```python
{
    'filename': 'activity_summary.csv',          # file name
    'path': '/abs/path/activity_summary.csv',    # absolute path
    'format': 'csv',                             # 'csv' or 'parquet'
    'rows': 26,                                  # row count
    'size_bytes': 2048,                          # file size in bytes
    'source_function': 'get_activity_summary',   # originating query function
    'exported_at': '2026-09-09T14:30:00+00:00',  # UTC ISO timestamp
}
```

`export_all()` returns an aggregate manifest:

```python
{
    'exported_at': '2026-09-09T14:30:00+00:00',
    'output_dir': '/abs/path/reports/generated/analytics',
    'datasets': {
        'executive_summary': [{'filename': ..., 'format': 'csv', ...}, ...],
        'activity_summary': [...],
        ...
    },
    'total_files': 18,
    'total_rows': 412,
}
```

`get_export_manifest()` returns a directory scan:

```python
{
    'output_dir': '/abs/path/reports/generated/analytics',
    'files': [
        {'filename': 'activity_summary.csv', 'format': 'csv', 'size_bytes': 2048, 'modified_at': '...'},
        ...
    ],
    'total_files': 18,
}
```

## Usage Examples

### Quick Start — Batch Export All

```python
from src.analytics.export import export_all

# Export every dataset to both CSV and Parquet (default)
manifest = export_all()
print(f"Exported {manifest['total_files']} files, {manifest['total_rows']} total rows")
for name, exports in manifest['datasets'].items():
    for meta in exports:
        print(f"  {meta['filename']}: {meta['rows']} rows, {meta['size_bytes']} bytes")
```

### Selective Export — Single Dataset

```python
from src.analytics.export import export_activity_summary

# CSV only, to default directory (reports/generated/analytics/)
results = export_activity_summary(formats=('csv',))
print(results[0]['path'])  # /path/to/reports/generated/analytics/activity_summary.csv

# Custom output directory
from pathlib import Path
results = export_activity_summary(output_dir=Path('my_exports'), formats=('csv', 'parquet'))
```

### Time-Series Export with Granularity

```python
from src.analytics.export import export_application_volume_over_time

# Monthly trend (default)
monthly = export_application_volume_over_time(granularity='monthly')

# Daily granularity
daily = export_application_volume_over_time(granularity='daily')
```

### Core Helpers — Raw Data

```python
from src.analytics.export import export_to_csv, export_to_parquet

data = [
    {'category': 'New credit', 'count': 28131},
    {'category': 'Limit raise', 'count': 3378},
]

# Generic CSV
meta = export_to_csv(data, 'reports/generated/analytics', 'custom_metric')

# Generic Parquet
meta = export_to_parquet(data, 'reports/generated/analytics', 'custom_metric')
```

### Load Exports in pandas (Roundtrip Verification)

```python
import pandas as pd

# Read back CSV
df = pd.read_csv('reports/generated/analytics/activity_summary.csv')
print(f"{len(df)} activities")  # 26 activities

# Read back Parquet (more efficient, preserves types)
df = pd.read_parquet('reports/generated/analytics/activity_summary.parquet')
print(df.head())
```

### Check What Has Been Exported

```python
from src.analytics.export import get_export_manifest

manifest = get_export_manifest()
print(f"{manifest['total_files']} files in {manifest['output_dir']}")
for f in manifest['files']:
    print(f"  {f['filename']} ({f['size_bytes']} bytes)")
```

### Power BI Integration

CSV and Parquet files in `reports/generated/analytics/` can be loaded directly into Power BI:
- **CSV:** Get Data → Text/CSV → select file
- **Parquet:** Get Data → Parquet (or convert via Python script in PBI)

## Testing

Run tests with:

```bash
pytest tests/test_analytics_export.py -v
pytest tests/ -v          # full suite
```

**Test Coverage (55 tests):**

| Test Class | Count | Description |
|------------|-------|-------------|
| `TestExportToCSV` | 10 | Core CSV export (no DB) |
| `TestExportToParquet` | 7 | Core Parquet export (no DB) |
| `TestExportValidation` | 6 | Input validation (None, empty, wrong type) |
| `TestExportExecutiveSummary` | 4 | Executive summary (DB) |
| `TestExportApplicationVolume` | 4 | Volume by type and over time (DB) |
| `TestExportActivitySummary` | 3 | Activity summary (DB) |
| `TestExportResourceWorkload` | 2 | Resource workload (DB) |
| `TestExportLifecycleOutcomes` | 1 | Lifecycle outcomes (DB) |
| `TestExportLoanGoalSummary` | 1 | Loan goal summary (DB) |
| `TestExportProcessingTimeDistribution` | 2 | Duration distribution (DB) |
| `TestExportAll` | 6 | Batch export |
| `TestExportManifest` | 5 | Manifest scanning |
| `TestSourceFunctionMetadata` | 4 | Source function provenance |

**Edge cases covered:**
- Null / empty / wrong-type inputs raise `ValueError`
- Nested directory creation
- Unicode (UTF-8) handling
- File size and row-count metadata accuracy
- CSV/Parquet roundtrip readback verification

## Output Directory

Default: `reports/generated/analytics/` (Git-ignored via `reports/generated/` entry in `.gitignore`)

A custom directory can be passed to any export function. Directories are created recursively if they do not exist.

**Files are Git-ignored** — this is intentional; generated analytics exports are reproducible artifacts derived from the PostgreSQL database, not source-controlled assets.

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `pandas` | `>=2.2,<3.0` | DataFrame construction, CSV serialization |
| `pyarrow` | `>=14.0,<20.0` | Parquet serialization (required for `DataFrame.to_parquet()`) |

Both are in `requirements.txt` and `pyproject.toml`.

## References

- **Phase 6.1 Query Layer:** `src/analytics/queries.py` (13 query functions)
- **Phase 6.1 Tests:** `tests/test_analytics_queries.py` (50 tests)
- **Phase 6.1 Documentation:** `docs/phase-6-python-analytics.md`
- **Phase 5 SQL Analytics:** `sql/002_analytics_views.sql` (13 views + 4 materialized views)
- **Database Connection:** `src/database.py`
- **BPI Challenge 2017:** [4TU.ResearchData](https://doi.org/10.4121/uuid:5f3067df-f10b-45da-b98b-86ae4c7a310b)
