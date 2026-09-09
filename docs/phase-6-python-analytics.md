# Phase 6: Python Analytics Query Layer

## Overview

Phase 6.1 introduces a Python analytics query layer built on top of the Phase 5 SQL Analytics views. This module provides a clean, type-safe interface for analytical queries against the BPI Challenge 2017 loan application event log.

**Status:** Phase 6.1 - Python Analytics Query Layer ✅ COMPLETE
**Last Updated:** 2026-09-09

## Purpose

The Python Analytics Query Layer serves as the consumption layer for Phase 5 SQL Analytics views. It:

1. **Provides a programmatic interface** to analytical queries (functions, not raw SQL)
2. **Returns structured Python results** (dicts/lists) ready for pandas, visualization, or API use
3. **Encapsulates query logic** so consumers don't need to know SQL syntax or view definitions
4. **Validates data types** (floats, ints, strings) for downstream consistency
5. **Builds on existing infrastructure** without duplicating Phase 5 SQL

## Architecture

```
src/analytics/queries.py
    │
    ├─► src/database.py (connection management)
    │
    └─► PostgreSQL Phase 5 Views
         ├─ view_application_metrics
         ├─ view_daily_throughput
         ├─ view_activity_summary
         ├─ view_resource_workload
         ├─ view_processing_time_buckets
         ├─ view_lifecycle_transition_metrics
         ├─ view_loan_goal_metrics
         ├─ view_monthly_summary
         └─ mv_* materialized views
```

**Design Principles:**
- Query functions are stateless (no side effects, no caching)
- Each function corresponds to one analytical question
- Functions return Python dicts/lists with consistent keys
- Floats are explicitly cast (avoid Decimal types from PostgreSQL)
- No hardcoded credentials or connection parameters

## Available Query Functions

### Basic Counts

| Function | Returns | Source View | Description |
|----------|---------|-------------|-------------|
| `get_total_applications()` | `int` | `view_application_metrics` | Total application count (31,509) |
| `get_total_events()` | `int` | `events` table | Total event count (1,202,267) |

### Application Analysis

| Function | Returns | Source View | Description |
|----------|---------|-------------|-------------|
| `get_application_volume_by_type()` | `list[dict]` | `mv_application_type_summary` | Metrics by application type |
| `get_application_volume_over_time(granularity)` | `list[dict]` | `view_monthly_summary` or `view_daily_throughput` | Volume trends (monthly/daily) |
| `get_application_processing_metrics(limit)` | `list[dict]` | `view_application_metrics` | Per-application processing metrics |

### Process Performance

| Function | Returns | Source View | Description |
|----------|---------|-------------|-------------|
| `get_processing_duration_metrics()` | `dict` | `view_application_metrics` + `view_processing_time_buckets` | Avg duration, median bucket, distribution |
| `get_processing_time_distribution()` | `list[dict]` | `view_processing_time_buckets` | Application count by duration bucket |

### Activity & Resource Analysis

| Function | Returns | Source View | Description |
|----------|---------|-------------|-------------|
| `get_activity_summary()` | `list[dict]` | `view_activity_summary` | Activity frequency and lifecycle analysis (26 activities) |
| `get_resource_workload(limit)` | `list[dict]` | `view_resource_workload` | Resource workload distribution (149 resources) |

### Outcome & Goal Analysis

| Function | Returns | Source View | Description |
|----------|---------|-------------|-------------|
| `get_lifecycle_outcome_summary()` | `list[dict]` | `view_lifecycle_transition_metrics` | Lifecycle transition analysis |
| `get_loan_goal_summary()` | `list[dict]` | `view_loan_goal_metrics` | Metrics by loan goal/purpose |

### Aggregated Summary

| Function | Returns | Source View | Description |
|----------|---------|-------------|-------------|
| `get_executive_summary()` | `dict` | Multiple views | High-level metrics for dashboard cards |

## KPI Definitions

### Core KPIs

| KPI | Definition | Source |
|-----|-----------|--------|
| **Total Applications** | Unique loan application cases in the dataset | `COUNT(*) FROM applications` |
| **Total Events** | All workflow events across all applications | `COUNT(*) FROM events` |
| **Avg Events per App** | Mean number of events per application | `AVG(event_count) FROM view_application_metrics` |
| **Avg Processing Days** | Mean duration from first to last event (days) | `AVG(processing_days) FROM view_application_metrics` |
| **Application Type Mix** | Distribution of New credit vs. Limit raise | `mv_application_type_summary` |
| **Monthly Volume Trend** | Application count by month | `view_monthly_summary` |

### Activity KPIs

| KPI | Definition | Source |
|-----|-----------|--------|
| **Top Activities** | Activities with highest event counts | `view_activity_summary ORDER BY event_count DESC` |
| **Activity Concentration** | % of events in top 5 activities | Calculated from `view_activity_summary` |
| **Workflow Activity %** | % of events with W_ prefix | `activity_type = 'Workflow'` |
| **Offer Activity %** | % of events with O_ prefix | `activity_type = 'Offer'` |

### Resource KPIs

| KPI | Definition | Source |
|-----|-----------|--------|
| **Max User Workload** | Highest % of events handled by single resource | `MAX(workload_percentage) FROM view_resource_workload` |
| **Workload Imbalance** | Std dev of resource workload (inequity measure) | Calculated from `view_resource_workload` |
| **Active Resources** | Number of distinct users with events | `COUNT(*) FROM view_resource_workload` |

### Outcome KPIs

| KPI | Definition | Source |
|-----|-----------|--------|
| **Completion Rate** | % of applications reaching 'complete' lifecycle | `view_lifecycle_transition_metrics WHERE lifecycle = 'complete'` |
| **Suspension Rate** | % of applications with 'suspend' events | `view_lifecycle_transition_metrics WHERE lifecycle = 'suspend'` |
| **Withdrawal Rate** | % of applications with 'withdraw' events | `view_lifecycle_transition_metrics WHERE lifecycle = 'withdraw'` |

### Duration KPIs

| KPI | Definition | Source |
|-----|-----------|--------|
| **Median Processing Bucket** | Duration bucket containing 50th percentile | `view_processing_time_buckets` cumulative distribution |
| **Applications in 1-4 Weeks** | % taking 1-4 weeks (typical cycle time) | `view_processing_time_buckets WHERE bucket = '1-4 weeks'` |
| **SLA Compliance** | % meeting SLA target | **NOT AVAILABLE** - requires synthetic SLA data |

## Data Limitations

The BPI Challenge 2017 dataset has real limitations that affect available analytics:

### Available in the Dataset
- ✅ 31,509 unique loan application cases
- ✅ 1,202,267 workflow events (Jan 2016 – Feb 2017)
- ✅ 26 distinct activity types (W_/O_/A_ prefixes)
- ✅ 149 distinct resources/users
- ✅ 2 application types: "New credit" (89.3%), "Limit raise" (10.7%)
- ✅ 5+ loan goals/purposes
- ✅ Lifecycle transitions: complete, suspend, withdraw
- ✅ Requested amounts (numeric)
- ✅ Event timestamps (start/end, duration calculable)

### NOT Available in the Dataset
- ❌ **Synthetic operational fields:** branch, priority, SLA targets, page counts, regions, operator teams
- ❌ **Document processing metrics:** page counts, physical documents, error flags (fictional only)
- ❌ **SLA compliance:** no actual SLA targets in source data
- ❌ **Customer identity:** anonymized event log, no customer data
- ❌ **Financial outcomes:** loan approval/denial amounts, actual credit decisions
- ❌ **Historical trends:** data spans only Jan 2016 – Feb 2017 (13 months)

### Important Context

This dataset is a **real loan application event log**, not a document-processing dataset. The project terms it "document intelligence" for demonstration purposes, but analytics are grounded in actual loan application workflow data.

Synthetic extensions (branch, priority, SLA, etc.) are defined in the schema (`synthetic_extensions` table) but **not populated**. If future phases need these fields, they must be generated with clear documentation that they are synthetic labels, not historical facts.

## Usage Examples

### Quick Start

```python
from src.analytics.queries import get_executive_summary

# Get high-level summary for dashboard
summary = get_executive_summary()
print(f"Total applications: {summary['total_applications']}")
print(f"Total events: {summary['total_events']}")
print(f"Avg events per app: {summary['avg_events_per_app']:.1f}")
```

### Application Volume Analysis

```python
from src.analytics.queries import get_application_volume_by_type, get_application_volume_over_time

# By type
by_type = get_application_volume_by_type()
for app_type in by_type:
    print(f"{app_type['application_type']}: {app_type['application_count']} apps")

# Over time (monthly)
monthly = get_application_volume_over_time(granularity='monthly')
for month in monthly:
    print(f"{month['year_month']}: {month['applications']} apps, {month['total_events']} events")
```

### Processing Performance

```python
from src.analytics.queries import get_processing_duration_metrics, get_processing_time_distribution

# Duration metrics
metrics = get_processing_duration_metrics()
print(f"Avg processing: {metrics['avg_processing_days']:.1f} days")
print(f"Median bucket: {metrics['median_bucket']}")

# Distribution
dist = get_processing_time_distribution()
for bucket in dist:
    print(f"{bucket['bucket']}: {bucket['application_count']} apps ({bucket['percentage']:.1f}%)")
```

### Activity & Resource Analysis

```python
from src.analytics.queries import get_activity_summary, get_resource_workload

# Top activities
activities = get_activity_summary()
print("Top 5 activities:")
for activity in activities[:5]:
    print(f"  {activity['activity']}: {activity['event_count']} events ({activity['percentage_of_total']:.1f}%)")

# Top resources
resources = get_resource_workload(limit=10)
print("\nTop 10 resources:")
for resource in resources:
    print(f"  {resource['resource']}: {resource['event_count']} events ({resource['workload_percentage']:.1f}%)")
```

### Export to pandas DataFrame

```python
import pandas as pd
from src.analytics.queries import get_application_volume_over_time, get_activity_summary

# Convert to DataFrame for visualization
monthly_df = pd.DataFrame(get_application_volume_over_time(granularity='monthly'))
monthly_df.plot(x='year_month', y='applications', kind='line')

activities_df = pd.DataFrame(get_activity_summary())
activities_df.head(10).plot(kind='bar', x='activity', y='event_count')
```

## Testing

Run tests with:
```bash
pytest tests/test_analytics_queries.py -v
```

**Test Coverage:**
- 25+ test functions covering all query functions
- Type validation (ints, floats, strings, lists, dicts)
- Structure validation (keys, lengths, value ranges)
- Database validation (counts match actual data)
- Edge cases (limit parameters, granularity validation, date filters)

**Test Categories:**
- `TestBasicCounts`: Application and event count validation
- `TestApplicationVolumeByType`: Application type distribution
- `TestApplicationVolumeOverTime`: Monthly/daily volume trends
- `TestProcessingDurationMetrics`: Duration statistics
- `TestActivitySummary`: Activity frequency analysis
- `TestResourceWorkload`: Resource utilization
- `TestLifecycleOutcomeSummary`: Outcome distribution
- `TestLoanGoalSummary`: Loan purpose analysis
- `TestApplicationProcessingMetrics`: Per-application metrics
- `TestExecutiveSummary`: Aggregated summary
- `TestTypeConsistency`: Float type validation

## Dependencies

**Required:**
- `psycopg` (PostgreSQL adapter, already in requirements.txt)
- `src.database` (connection management, already in src/)

**Optional (for downstream use):**
- `pandas` (DataFrame export, listed in requirements.txt)
- `matplotlib` / `seaborn` (visualization, listed in requirements.txt)

## Limitations

1. **No Caching:** Each query executes against PostgreSQL. For repeated calls, consider caching at the caller level (e.g., pandas DataFrame in memory).

2. **No Concurrent Access:** `get_cursor()` creates a new connection per call. High-concurrency scenarios need connection pooling.

3. **No Write Operations:** Query functions are read-only. Materialized view refresh is handled separately by `scripts/refresh_views.py`.

4. **Limited to Phase 5 Views:** Functions query existing views only. New analytical perspectives require new SQL views (Phase 5) or new Python queries on base tables.

5. **No SLA/Document Metrics:** Dataset limitations prevent SLA compliance, document count, or error-rate analytics. Synthetic extension population is required for those KPIs (not in Phase 6.1).

## Future Extensions (Phase 6.2+)

- **Export Module:** `src/analytics/export.py` for CSV/Parquet generation
- **Power BI Data Model:** Semantic model documentation
- **Additional KPIs:** Workload imbalance, rework cycles, trend calculations
- **Visualization Functions:** Pre-built matplotlib/seaborn chart functions
- **API Integration:** FastAPI endpoints wrapping query functions

## References

- **Phase 5 SQL Analytics:** `sql/002_analytics_views.sql` (13 views + 4 materialized views)
- **Phase 5 Tests:** `tests/test_sql_analytics.py` (33 tests)
- **View Management:** `src/analytics/views.py`
- **Database Connection:** `src/database.py`
- **BPI Challenge 2017:** [4TU.ResearchData](https://doi.org/10.4121/uuid:5f3067df-f10b-45da-b98b-86ae4c7a310b)
