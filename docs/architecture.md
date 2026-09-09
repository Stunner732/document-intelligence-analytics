# Architecture — AI-Powered Document Intelligence & Operations Analytics

> Polished architecture document for the completed portfolio pipeline.
> Source of truth: the committed repository files, not aspirational plans.

---

## 1. System Overview

The pipeline transforms a real-world operational event log into structured business analytics. It is fully implemented, tested, and verified — 214/214 tests pass with zero regressions.

The dataset is the [BPI Challenge 2017](https://data.4tu.nl/articles/dataset/BPI_Challenge_2017/12696884) loan application event log from a Dutch financial institution: **31,509 applications** and **1,202,267 events** spanning January 2016 through February 2017.

No synthetic data drives the analytics. The `synthetic_extensions` table exists in the schema but remains empty; synthetic fields (document type, SLA target, page count, priority, branch) are documented and deferred, not fabricated.

---

## 2. High-Level Architecture (Mermaid)

```mermaid
flowchart TB
    subgraph DATA_SOURCE["Data Source"]
        XES["BPI Challenge 2017 XES Event Log<br/>31,509 apps · 1.2M events"]
    end

    subgraph DATA_QUALITY["Data Quality / Validation Pipeline"]
        DQP["Non-destructive streaming parser<br/>12-rule validation catalog<br/>Quarantine manifest"]
    end

    subgraph DATABASE["PostgreSQL 16"]
        DB["6 tables<br/>applications · events · offers<br/>synthetic_extensions · data_loads<br/>schema_versions"]
        SCHEMA["Schema version tracking<br/>Foreign keys · Indexes · Constraints"]
    end

    subgraph SQL_ANALYTICS["SQL Analytics Layer"]
        VIEWS["13 analytical views"]
        MATVIEWS["4 materialized views"]
    end

    subgraph PYTHON_ANALYTICS["Python Analytics Layer"]
        QUERIES["13 typed query functions"]
    end

    subgraph EXPORT["Analytics Export Layer"]
        CSV_PARQUET["CSV + Parquet exports<br/>Batch export · Manifest tracking"]
    end

    subgraph VISUALIZATION["Visualization Layer"]
        CHARTS["8 chart functions<br/>PNG · Batch generation · Manifest"]
    end

    BI_DASHBOARD["BI / Dashboard Consumption<br/>Power BI · Reports · Manual review"]

    XES --> DQP
    DQP --> DB
    DB --> SCHEMA
    DB --> VIEWS
    DB --> MATVIEWS
    VIEWS --> QUERIES
    MATVIEWS --> QUERIES
    QUERIES --> CSV_PARQUET
    QUERIES --> CHARTS
    CSV_PARQUET --> BI_DASHBOARD
    CHARTS --> BI_DASHBOARD

    style DATA_SOURCE fill:#e8f4f8
    style DATA_QUALITY fill:#fff8e1
    style DATABASE fill:#e8f5e9
    style SQL_ANALYTICS fill:#e3f2fd
    style PYTHON_ANALYTICS fill:#f3e5f5
    style EXPORT fill:#fff3e0
    style VISUALIZATION fill:#fce4ec
    style BI_DASHBOARD fill:#f5f5f5
```

---

## 3. Layer-by-Layer Specification

### 3.1 Data Source — BPI Challenge 2017 XES Event Log

| Property | Value |
|----------|-------|
| **Source** | Eindhoven University of Technology / 4TU.ResearchData |
| **File** | `data/raw/BPI_Challenge_2017.xes.gz` |
| **Size** | 29,658,747 bytes (gzip-compressed XML) |
| **Checksum (MD5)** | `10b37a2f78e870d78406198403ff13d2` |
| **Applications (traces)** | 31,509 unique cases |
| **Events** | 1,202,267 workflow events |
| **Time coverage** | January 2016 – February 2017 |
| **Application types** | New credit, Limit raise |
| **Activities** | 26 distinct workflow activities (`W_` / `O_` / `A_` prefixes) |
| **Resources** | 149 anonymized actors/systems |
| **License** | 4TU General Terms of Use |

**Purpose:** Provide the raw operational data for the entire pipeline.

**Input:** Public dataset download (script `scripts/download_bpi_2017.ps1` verifies checksum).

**Processing:** None at this layer; provenance tracked in `data/source_manifest.json`.

**Output:** `data/raw/BPI_Challenge_2017.xes.gz` (Git-ignored, reproducible via download script).

**Business value:** Real-world process data from a financial institution enables credible operational-performance analysis rather than synthetic demonstration.

---

### 3.2 Data Quality / Validation Pipeline

**Verified results against the actual BPI 2017 dataset:**

- 31,509 traces checked
- 1,202,267 events checked
- 0 quarantine candidates
- 0 error or warning rule violations
- Info-level reports only: synthetic extension fields not present in source; SLA consistency deferred (documented, not hidden)

**Purpose:** Detect identity, timestamp, content, scope, and structural issues before data enters the analytical store — without mutating the raw archive.

**Input:** `BPI_Challenge_2017.xes.gz`

**Processing:** Streaming `iterparse` reads the compressed XML event-by-event; 12-rule catalog validates identity (missing IDs, duplicates), timestamps (null checks, monotonicity, impossible durations), content (missing activities), scope (orphaned events), and synthetic-field presence. Quarantine manifest collects bounded examples (max 20 per rule).

**Output:** `reports/generated/data_quality/data_quality_report.json`, `.md`, and `quarantine_manifest.json`.

**Business value:** Non-destructive validation builds trust in downstream metrics; the quarantine approach allows review rather than silent deletion.

---

### 3.3 Database — PostgreSQL 16

**Schema (6 tables):**

| Table | Purpose | Row Count (verified) |
|-------|---------|---------------------|
| `applications` | One row per loan application (trace-level) | 31,509 |
| `events` | One row per workflow event (FK to applications) | 1,202,267 |
| `offers` | Optional offer records per application | (real offers present) |
| `synthetic_extensions` | Reserved for future synthetic operational fields; currently empty | 0 |
| `data_loads` | Import lineage tracking | Migration records |
| `schema_versions` | Migration version history | `001`, `002` |

**Indexes and constraints:** Foreign keys enforce referential integrity (`events.application_id` → `applications.application_id`). Indexes cover common query patterns: application lookups (`idx_applications_first_event_time`), time-range queries (`idx_events_app_time`), resource filtering (`idx_events_resource`), activity filtering (`idx_events_activity`), and lifecycle filtering (`idx_events_lifecycle_transition`).

**Purpose:** Persistent, queryable, indexed storage with version-controlled schema.

**Input:** Cleaned event logs loaded via `scripts/load_xes_to_db.py`.

**Processing:** Streaming loader inserts traces one at a time (matching the quality pipeline's memory-efficient pattern). Schema migrations tracked in `sql/001_create_schema.sql` and `sql/002_analytics_views.sql`; `src/database.py` provides `run_migrations()` and `get_schema_version()`.

**Output:** Fully populated database; `data_loads` records each import.

**Business value:** Structured relational storage enables complex analytical queries, reproducible results, and multi-user access.

---

### 3.4 SQL Analytics Layer — 13 Views + 4 Materialized Views

**13 regular analytical views (`sql/002_analytics_views.sql`):**

1. `view_application_metrics` — per-application duration, event counts, lifecycle breakdown (`complete`/`suspend`/`withdraw`), workflow/offer/application activity counts.
2. `view_daily_throughput` — daily started applications and event sums.
3. `view_activity_summary` — activity frequency (`W_` / `O_` / `A_` classification), lifecycle percentages.
4. `view_resource_workload` — resource utilization and workload percentage distribution.
5. `view_application_type_metrics` — metrics by `New credit` vs `Limit raise`.
6. `view_loan_goal_metrics` — metrics grouped by loan purpose.
7. `view_lifecycle_transition_metrics` — outcome distribution with workflow/offer/application percentages.
8. `view_event_origin_metrics` — event origin analysis.
9. `view_monthly_summary` — monthly aggregated volume, processing time, distinct types/goals.
10. `view_weekly_summary` — weekly aggregated metrics.
11. `view_event_sequence` — event sequence with `ROW_NUMBER()`, `LEAD` (`next_activity`), `LAG` (`prev_activity`), and derived `time_to_next`.
12. `view_processing_time_buckets` — duration categories (`< 1 hour` to `> 4 weeks`) with counts and percentages.
13. `view_offer_analysis` — offer status metrics (`Created`, `Sent`, `Accepted`, `Returned`, `Refused`, `Cancelled`).

**4 materialized views (pre-computed for heavy aggregations):**

- `mv_activity_summary`
- `mv_resource_workload`
- `mv_monthly_summary`
- `mv_application_type_summary`

**Purpose:** Reusable, query-optimized analytical definitions that eliminate SQL duplication in the Python layer.

**Input:** `applications` and `events` tables.

**Processing:** Standard SQL (`SELECT`, `GROUP BY`, window functions `LEAD`/`LAG`, `ROW_NUMBER()`, `CASE` classification, derived epoch calculations for processing duration). Materialized views pre-compute aggregations; regular views compute on demand.

**Output:** Queryable analytical datasets accessible to Python query functions.

**Business value:** Analysts and downstream Python functions read from a consistent, tested analytical layer rather than rewriting aggregation logic per report.

---

### 3.5 Python Analytics Layer — 13 Typed Query Functions

`src/analytics/queries.py` provides 13 typed functions consuming the SQL views. Each uses `get_cursor()` from `src/database.py` — no SQL duplication, no hardcoded credentials.

| Function | Returns | Source View |
|----------|---------|-------------|
| `get_total_applications()` | `int` | `view_application_metrics` |
| `get_total_events()` | `int` | `events` (base table) |
| `get_application_volume_by_type()` | `list[dict]` | `mv_application_type_summary` |
| `get_application_volume_over_time()` | `list[dict]` | `view_monthly_summary` or `view_daily_throughput` (granularity filter: `monthly`/`daily`; optional `start_date`/`end_date`) |
| `get_event_volume_over_time()` | `list[dict]` | `view_monthly_summary` |
| `get_processing_duration_metrics()` | `dict` | `view_application_metrics` + `view_processing_time_buckets` (avg hours/days, median bucket, full bucket distribution) |
| `get_processing_time_distribution()` | `list[dict]` | `view_processing_time_buckets` |
| `get_activity_summary()` | `list[dict]` | `view_activity_summary` |
| `get_resource_workload()` | `list[dict]` | `view_resource_workload` (optional `limit`) |
| `get_lifecycle_outcome_summary()` | `list[dict]` | `view_lifecycle_transition_metrics` |
| `get_loan_goal_summary()` | `list[dict]` | `view_loan_goal_metrics` |
| `get_application_processing_metrics()` | `list[dict]` | `view_application_metrics` (optional `limit`, ordered by `processing_hours DESC`) |
| `get_executive_summary()` | `dict` | Aggregates `view_application_metrics`, `events`, `view_activity_summary`, `view_resource_workload`, `mv_application_type_summary` |

**Purpose:** Clean Python interface over SQL analytics.

**Input:** Phase 5 SQL views and materialized views.

**Processing:** Each function executes a targeted `SELECT` through `get_cursor()`, transforms `fetchall()` results into typed Python structures (`int`, `list[dict[str, Any]]`, `dict[str, Any]`), and handles `None` values with safe float conversions. No SQL is duplicated from the view definitions.

**Output:** Structured Python data ready for export and visualization.

**Business value:** Python developers can retrieve analytics without writing SQL; type hints and docstrings make the interface self-documenting.

---

### 3.6 Analytics Export Layer

`src/analytics/export.py` converts query results to portable formats.

| Feature | Implementation |
|---------|----------------|
| **Formats** | CSV (UTF-8) and Parquet (PyArrow, columnar, compressed) |
| **Datasets exported** | 8: `executive_summary`, `application_volume_by_type`, `application_volume_over_time` (monthly/daily), `activity_summary`, `resource_workload`, `lifecycle_outcomes`, `loan_goal_summary`, `processing_time_distribution` |
| **Batch export** | `export_all()` produces all datasets; returns manifest |
| **Manifest** | `get_export_manifest()` scans `reports/generated/analytics/` for `.csv`/`.parquet`; returns `filename`, `format`, `size_bytes`, `modified_at` |
| **Output directory** | `reports/generated/analytics/` (Git-ignored, reproducible) |
| **Metadata per file** | Filename, path, format, row count, byte size, source function, UTC timestamp |

**Purpose:** Make analytical results consumable by downstream tools (Power BI, Excel, pandas, Jupyter).

**Input:** Results from the 13 Python query functions.

**Processing:** `pandas.DataFrame` creation; `to_csv()` (UTF-8, index=False) or `to_parquet()`; `_build_export_metadata()` creates structured metadata. Batch `export_all()` iterates over 9 exporter functions and aggregates results.

**Output:** `.csv` and `.parquet` files + manifest dict.

**Business value:** Portable, typed file formats support both interactive BI import (CSV) and efficient storage/re-analysis (Parquet) without duplicating SQL or query logic.

---

### 3.7 Visualization Layer

`src/analytics/visualization.py` generates 8 chart types from the Python query layer.

| Function | Chart Type | Insight Delivered |
|----------|-----------|-------------------|
| `plot_executive_summary()` | KPI stat tiles (2×2 grid) | Headline metrics at a glance |
| `plot_application_volume_by_type()` | Horizontal bar | `New credit` vs `Limit raise` counts |
| `plot_application_volume_over_time()` | Line chart (dual axis for monthly) | Monthly/daily volume + total events overlay |
| `plot_activity_summary()` | Horizontal bar (top 10 by default) | Most frequent workflow activities |
| `plot_resource_workload()` | Horizontal bar (top 20 by default) | Resource utilization comparison |
| `plot_lifecycle_outcomes()` | Donut chart | Complete / suspend / withdraw distribution |
| `plot_loan_goal_summary()` | Grouped bar (dual axis) | Application count vs average processing hours by loan purpose |
| `plot_processing_time_distribution()` | Vertical bar | Duration bucket distribution |

**Shared design:** `seaborn-whitegrid`, 120 DPI, `Agg` non-interactive backend (CI-safe), HUSL palette (`PALETTE = sns.color_palette("husl", 8)`), consistent font sizing, `bbox_inches="tight"`. Each function returns metadata (`filename`, `path`, `format`: `png`, `size_bytes`, `rows`, `figure_type`, `source_function`, `generated_at`). Empty data produces a "No data available" placeholder. Batch `plot_all()` produces all charts with aggregate manifest (`get_plot_manifest()` scans `reports/generated/plots/`).

**Purpose:** Transform numerical query results into business-facing visual artifacts.

**Input:** Phase 6.1 Python query results (`get_executive_summary()`, `get_application_volume_by_type()`, etc.).

**Processing:** Each chart calls exactly one query function; `pandas.DataFrame` transformation; `matplotlib.pyplot` / `seaborn` plotting; `_save_figure()` writes PNG; `_build_plot_metadata()` creates structured metadata. No SQL is duplicated.

**Output:** `.png` files in `reports/generated/plots/` + manifest.

**Business value:** Visual artifacts communicate trends and distributions faster than raw tables; consistent styling produces a professional deliverable.

---

### 3.8 BI / Dashboard Consumption

**Purpose:** Final consumption layer for stakeholders.

**Input:** CSV/Parquet exports (`reports/generated/analytics/`) and PNG charts (`reports/generated/plots/`).

**Processing:** External (not implemented in this repository): Power BI import, manual review, or embedded in reports.

**Output:** Operational decision-making (volume trends, processing times, resource allocation, lifecycle outcomes).

**Business value:** The pipeline delivers actionable answers to questions operations managers ask.

---

## 4. End-to-End Data Flow

How a single raw event moves through the system:

1. **Source archive:** The event is embedded in `BPI_Challenge_2017.xes.gz` as `<event>` XML inside a `<trace>`.
2. **Data quality pipeline:** `run_quality_checks()` streams the trace through `iterparse`, extracts the event's `EventID`, `time:timestamp`, `concept:name` (activity), and `concept:name` trace identifier. It checks identity (is the event orphaned?), timestamp validity, monotonicity, and activity presence. For the BPI dataset, no issues were found; 0 quarantine entries generated.
3. **Database loader:** `load_xes_to_db.py` inserts the event into the `events` table (`event_id`, `application_id` FK, `activity`, `event_timestamp`, `resource`, `lifecycle_transition`, `action`, `event_origin`). The parent application is inserted or verified in the `applications` table (`application_type`, `loan_goal`, etc.).
4. **Schema tracking:** `data_loads` records the import; `schema_versions` tracks `001` and `002`.
5. **SQL analytics:** `view_application_metrics` calculates processing duration from `events.event_timestamp` for each `applications.application_id`. `view_activity_summary` aggregates the event's activity frequency. `view_lifecycle_transition_metrics` categorizes the event's `lifecycle_transition`. Materialized views (`mv_activity_summary`, `mv_resource_workload`, `mv_monthly_summary`, `mv_application_type_summary`) pre-compute heavy aggregations.
6. **Python query layer:** `get_activity_summary()` reads `view_activity_summary`. `get_executive_summary()` aggregates multiple views. `get_application_processing_metrics()` reads `view_application_metrics`. All queries return typed Python structures.
7. **Export layer:** `export_activity_summary()` writes `activity_summary.csv` and `.parquet`. `export_all()` writes 8 datasets and a manifest.
8. **Visualization layer:** `plot_activity_summary()` creates `activity_summary.png`. `plot_all()` creates all charts and a plot manifest.
9. **Consumption:** A stakeholder opens `executive_summary.png` or imports `executive_summary.csv` into Power BI to see 31,509 applications and 1,202,267 events at a glance.

---

## 5. Analytics Flow

How SQL analytical views become business-facing outputs:

```
PostgreSQL Tables (applications, events)
        ↓
SQL Migration: 002_analytics_views.sql
        ↓
13 Regular Views + 4 Materialized Views
        ↓
Python Query Layer (13 typed functions in queries.py)
        ↓
        ↓─────────────→ Export Module (export.py) → CSV / Parquet + Manifest
        ↓
Visualization Module (visualization.py) → PNG Charts + Manifest
```

Each layer consumes the previous layer's output without duplicating logic. The Python query functions read from views by name (`view_application_metrics`, `view_activity_summary`, etc.). The export module calls query functions and writes files. The visualization module calls the same query functions and writes PNGs. The design principle is: one SQL definition drives all downstream usage.

---

## 6. Business Questions Supported (Verified by Implementation)

Only questions supported by the actual query functions, SQL views, and exported/visualized datasets are listed below.

- **How many applications are being processed?** → `get_total_applications()`; `view_application_metrics`; `executive_summary` dataset and chart.
- **How many events occur across the dataset?** → `get_total_events()`; base `events` count.
- **How does application volume change over time?** → `get_application_volume_over_time()` (`monthly`/`daily` granularity with optional date filters); `get_event_volume_over_time()`; `view_monthly_summary`; line charts (`application_volume_over_time_*.png`).
- **Which application types dominate?** → `get_application_volume_by_type()`; `mv_application_type_summary`; `view_application_type_metrics`; bar chart `application_volume_by_type.png`.
- **How long does processing take?** → `get_processing_duration_metrics()` (average hours/days, median bucket); `get_processing_time_distribution()` (`< 1 hour`, `1-24 hours`, `1-7 days`, `1-4 weeks`, `> 4 weeks`); `view_processing_time_buckets`; `processing_time_distribution.png`.
- **Which activities occur most frequently?** → `get_activity_summary()` (26 activities); `view_activity_summary`; `activity_summary.png`.
- **How is workload distributed across resources?** → `get_resource_workload()` (149 resources, optional `limit`); `view_resource_workload`; `resource_workload.png`.
- **What lifecycle patterns exist?** → `get_lifecycle_outcome_summary()`; `view_lifecycle_transition_metrics`; `lifecycle_outcomes.png` (donut chart showing `complete` / `suspend` / `withdraw` percentages).
- **How do loan goals differ?** → `get_loan_goal_summary()`; `view_loan_goal_metrics`; `loan_goal_summary.png` (grouped bar: application count vs average processing hours by loan purpose).
- **How do individual applications compare?** → `get_application_processing_metrics()`; `view_application_metrics`; sorted by `processing_hours DESC`.

These are the only business capabilities implemented. No AI document classification, no SLA prediction, no interactive dashboard, and no LLM integration exist in the committed code.

---

## 7. Design Decisions (Verified from Implementation)

1. **PostgreSQL 16 as analytical storage layer** — Native installation (not Docker) verified; 6-table star schema with foreign keys, indexes, and schema version tracking (`schema_versions`).
2. **SQL views and materialized views for reusable analytics** — 13 regular views for flexible on-demand queries; 4 materialized views (`mv_activity_summary`, `mv_resource_workload`, `mv_monthly_summary`, `mv_application_type_summary`) for performance on heavy aggregations.
3. **Python abstraction over SQL queries** — `queries.py` provides typed functions that consume views by name; no duplicated SQL logic, no embedded SQL strings outside the query module.
4. **Non-destructive data quality validation** — Streaming parser (`iterparse`) handles 1.2M events without full memory load; quarantine manifest reports bounded examples; no automatic deletion or mutation of source records.
5. **CSV and Parquet for downstream consumption** — CSV (UTF-8, universal compatibility) and Parquet (columnar, compressed, efficient) both supported; `pyarrow>=14.0,<20.0` dependency verified.
6. **Automated tests across all layers** — `tests/test_quality_pipeline.py` (1), `test_database.py` (17), `test_sql_analytics.py` (33), `test_analytics_queries.py` (50), `test_analytics_export.py` (55), `test_analytics_visualization.py` (58): 214/214 passing.
7. **Schema version tracking** — `sql/001_create_schema.sql` and `sql/002_analytics_views.sql` tracked via `schema_versions`; `run_migrations()` skips already-applied versions.
8. **Streaming database loader** — `load_xes_to_db.py` inserts traces one at a time; `load_xes_to_db` respects existing records; matches quality pipeline memory pattern.
9. **Real dataset over synthetic** — All analytical outputs derive from verified BPI 2017 records; synthetic fields are explicitly documented as unavailable (`unavailable_document_extension_fields`, `sla_consistency_not_evaluable` info rules).
10. **Consistent visualization design** — `seaborn-whitegrid`, 120 DPI, `Agg` backend, HUSL palette, tight layout; metadata tracking per PNG file.

---

## 8. Technology Stack (Verified)

| Layer | Technology | Status |
|-------|-----------|--------|
| Source data | BPI Challenge 2017 XES (gzip XML) | Downloaded, checksum verified |
| Data quality | `xml.etree.ElementTree.iterparse` (streaming), 12-rule catalog | Implemented (`src/cleaning/quality_pipeline.py`) |
| Database | PostgreSQL 16.15 (native Windows) | Running; 6 tables, indexes, constraints |
| SQL analytics | 13 regular views + 4 materialized views (`sql/002_analytics_views.sql`) | Created and verified |
| Python query | `psycopg`, SQLAlchemy 2.0 patterns (`get_cursor()`), typed functions | 13 functions (`src/analytics/queries.py`) |
| Export | `pandas` (CSV), `pyarrow` (Parquet) (`src/analytics/export.py`) | Implemented |
| Visualization | `matplotlib`, `seaborn` (`Agg` backend) (`src/analytics/visualization.py`) | 8 chart functions |
| Configuration | `pydantic-settings`, `python-dotenv`, `.env` | Configured |
| Packaging | `pyproject.toml`, editable install (`pip install -e .`) | Installed (`v0.1.0`) |
| Testing | `pytest`, `pytest-cov` | 214/214 passing |

Not implemented (dependencies may exist but functionality does not):
- **FastAPI backend** — Not implemented; `api/` directory exists but contains no active endpoints.
- **Power BI dashboard** — Planned for future phase; the export layer produces CSV/Parquet specifically to support it, but no `.pbix` file or live connection exists.
- **Local LLM / Hermes Desktop** — Deferred; no LLM endpoint or model runtime integrated.
- **ML / document classification** — `scikit-learn` installed but no ML model, feature engineering, or prediction pipeline implemented.
- **AI document-intelligence capabilities** — Not implemented; the `src/ai/` directory exists but is empty.

---

## 9. Current Scope vs Future Scope

### Currently Implemented (Verified by Code, Tests, and Output)

- **Data acquisition** — BPI Challenge 2017 download script with MD5 verification.
- **Data quality** — Non-destructive streaming pipeline with 12 rules, bounded examples, quarantine manifest, JSON/Markdown reports.
- **Database** — PostgreSQL 16 with 6-table schema, foreign keys, indexes, schema version tracking (`001`, `002`), migration utilities.
- **SQL analytics** — 13 regular views (`view_*`) + 4 materialized views (`mv_*`), covering metrics, throughput, activities, resources, lifecycle, loan goals, event sequences, time-series, processing buckets, and offer analysis.
- **Python analytics** — 13 typed query functions (`get_*`) consuming existing SQL views; no SQL duplication.
- **Analytics export** — CSV + Parquet batch export for 8 datasets; manifest tracking; output directory `reports/generated/analytics/`.
- **Visualization** — 8 chart functions (KPI tiles, bar, line, donut, grouped bar); PNG batch generation; consistent style; manifest tracking; output directory `reports/generated/plots/`.
- **Testing** — 214 automated tests across all layers, zero regressions.

### Planned / Possible Future Work (Not Implemented)

- **Power BI dashboard** — Live connection or `.pbix` import using the CSV/Parquet exports produced by Phase 6.2.
- **Interactive reporting** — Web-based or embedded dashboards (separate from the non-interactive PNG outputs).
- **Process mining** — Deeper event-sequence analysis using `view_event_sequence` (already implemented as SQL) for process discovery models.
- **Expanded analytics** — Rework-cycle detection, trend forecasting, additional time-series modeling.
- **Document intelligence layer** — Potential future integration of AI/ML components for document classification, automated processing analysis, or synthetic field population. The `synthetic_extensions` table and `docs/synthetic-extension.md` document the design, but no ML pipeline, model, or LLM component exists.
- **AI Copilot / Natural-language queries** — Deferred until analytics layer exists; no local LLM endpoint configured.

---

## 10. Project Status Summary (Verified from Committed Code)

| Phase | Status | Verification |
|-------|--------|-------------|
| Phase 1 — Foundation | ✅ Complete | `.gitignore`, `.env.example`, `docker-compose.yml`, `pyproject.toml`, `src/config.py` |
| Phase 2 — Data | ✅ Complete | `BPI_Challenge_2017.xes.gz` downloaded; `data/source_manifest.json`; checksum verified |
| Phase 3 — Data Quality | ✅ Complete | `quality_pipeline.py` (1 test); 31,509 traces, 1,202,267 events, 0 quarantined |
| Phase 4 — Database | ✅ Complete | `sql/001_create_schema.sql` (6 tables); 17 tests passing; PostgreSQL 16.15 native |
| Phase 5 — SQL Analytics | ✅ Complete | `sql/002_analytics_views.sql` (13 views + 4 materialized); 33 tests passing |
| Phase 6.1 — Python Query | ✅ Complete | `queries.py` (13 functions); 50 tests passing |
| Phase 6.2 — Analytics Export | ✅ Complete | `export.py` (8 datasets, CSV/Parquet, batch, manifest); 55 tests passing |
| Phase 6.3 — Visualization | ✅ Complete | `visualization.py` (8 charts, PNG, batch, manifest); 58 tests passing |

**Total tests:** 214 passed. Zero failures. Zero regressions.

---

## 11. Key Files Reference

| Path | Role |
|------|------|
| `README.md` | Project overview, setup, architecture description |
| `PROJECT_STATUS.md` | Session handoff; phase status; next actions |
| `docs/architecture.md` | This document |
| `data/source_manifest.json` | Dataset provenance and checksum |
| `data/raw/BPI_Challenge_2017.xes.gz` | Raw event log (Git-ignored; reproducible via download script) |
| `sql/001_create_schema.sql` | Schema migration: 6 tables + indexes + version tracking |
| `sql/002_analytics_views.sql` | Analytics migration: 13 regular + 4 materialized views |
| `src/cleaning/quality_pipeline.py` | Streaming XES quality pipeline |
| `src/database.py` | Connection, migrations, schema version utilities |
| `src/analytics/queries.py` | 13 typed Python query functions |
| `src/analytics/export.py` | CSV/Parquet export + manifest |
| `src/analytics/visualization.py` | 8 chart functions + PNG generation |
| `tests/test_quality_pipeline.py` | Quality pipeline coverage (1 test) |
| `tests/test_database.py` | Database layer coverage (17 tests) |
| `tests/test_sql_analytics.py` | SQL analytics coverage (33 tests) |
| `tests/test_analytics_queries.py` | Python query layer (50 tests) |
| `tests/test_analytics_export.py` | Export module (55 tests) |
| `tests/test_analytics_visualization.py` | Visualization module (58 tests) |

---

*Document created from the actual repository implementation at `D:\Repository\document-intelligence-analytics`. Every claim in this document is traceable to committed code, passing tests, or verified database state. No aspirational components (FastAPI endpoints, Power BI `.pbix`, LLM integrations, ML models, AI document classification) are presented as implemented.*
