# Phase 8.1A — Synthetic Extension Design Inspection Report

## Executive Summary
This report summarizes the design inspection performed during **Phase 8.1A** in preparation for generating deterministic synthetic operational metadata for the **Document Intelligence & Operations Analytics** project.

The objective of Phase 8.1A is to establish the schema parameters, reconcile documentation with actual PostgreSQL constraints, define a seed-controlled deterministic generation strategy, and guarantee idempotent database insertion before any synthetic data generation takes place in Phase 8.1B.

---

## 1. Schema Findings

### 1.1 Table Structure & Constraints
The `synthetic_extensions` table exists in PostgreSQL database `document_intelligence` as defined in `sql/001_create_schema.sql`:

| Column | Data Type | Constraints & Defaults | Description |
| :--- | :--- | :--- | :--- |
| `application_id` | `VARCHAR(255)` | `PRIMARY KEY`, `REFERENCES applications(application_id) ON DELETE CASCADE` | 1:1 foreign key join to source applications |
| `document_type` | `VARCHAR(100)` | Nullable | Categorical document type label |
| `page_count` | `INTEGER` | Nullable | Document page count |
| `branch` | `VARCHAR(100)` | Nullable | Organizational branch handling application |
| `operator_team` | `VARCHAR(100)` | Nullable | Operational team assigned |
| `priority` | `VARCHAR(20)` | `CHECK (priority IN ('low', 'normal', 'high', 'urgent'))` | Operational processing priority |
| `sla_target_hours`| `INTEGER` | Nullable | Target turnaround time in hours |
| `region` | `VARCHAR(50)` | Nullable | Geographic operational region |
| `channel` | `VARCHAR(50)` | Nullable | Submission channel proxy |
| `quality_score` | `NUMERIC(5, 2)` | Nullable | Document scan quality score (0.00–100.00) |
| `error_flag` | `BOOLEAN` | `DEFAULT FALSE` | Operational rework/error flag proxy |
| `rejection_flag` | `BOOLEAN` | `DEFAULT FALSE` | Application rejection indicator |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | `DEFAULT NOW()` | Record creation timestamp |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | `DEFAULT NOW()` | Record update timestamp |

### 1.2 Table Indexes
- `idx_synthetic_extensions_branch` on `branch`
- `idx_synthetic_extensions_priority` on `priority`
- `idx_synthetic_extensions_region` on `region`

### 1.3 Population & Join Capacity
- Total records in `applications`: **31,509**
- Current records in `synthetic_extensions`: **0**
- Join Key: `synthetic_extensions.application_id = applications.application_id` (100% 1:1 match across all 31,509 cases).

---

## 2. Documentation vs. Schema Discrepancies

A comparison between `docs/synthetic-extension.md` and `sql/001_create_schema.sql` revealed the following key items:

1. **Identifier Terminology**:
   - `docs/synthetic-extension.md` refers to `document_id` as the primary trace identifier.
   - **Schema Reality**: The primary and foreign key in PostgreSQL is `application_id`. The generator must bind directly to `application_id`.

2. **Case Sensitivity in Priority Check Constraint**:
   - `sql/001_create_schema.sql` enforces `CHECK (priority IN ('low', 'normal', 'high', 'urgent'))`.
   - **Requirement**: Generator values for `priority` must strictly be lower-case strings (`'low'`, `'normal'`, `'high'`, `'urgent'`). Uppercase values (e.g. `'HIGH'`) will cause database constraint violations.

3. **Timestamp & Outcome Derivation Boundaries**:
   - `docs/synthetic-extension.md` lists fields like `received_timestamp`, `processing_start_timestamp`, `status`, and `processing_stage`.
   - **Schema Reality**: Timestamps and activity stage states live in `applications` and `events` tables or derived analytical views (`view_application_metrics`). The `synthetic_extensions` table only contains operational metadata attributes and record audit timestamps (`created_at`, `updated_at`).

4. **Lineage Tracking**:
   - Lineage is tracked via `created_at` and `updated_at` on each synthetic extension row, with bulk batch execution records logged in `data_loads` (`load_type = 'synthetic_extension'`).

---

## 3. Recommended Generation Approach

To maintain mathematical determinism, reproducibility, and zero random drift across runs:

1. **Deterministic Hashing / Fixed-Seed PRNG**:
   - Seed anchor: Default random seed `42` combined with hashing of `application_id` (e.g., `SHA-256(seed + application_id)`).
   - Guarantees that any given `application_id` receives identical synthetic attributes regardless of execution environment or execution order.

2. **Mapping & Attribute Rules**:
   - **Priority & SLA**:
     - `low`: `sla_target_hours = 72`
     - `normal`: `sla_target_hours = 48`
     - `high`: `sla_target_hours = 24`
     - `urgent`: `sla_target_hours = 12`
   - **Quality Score**: Uniformly or truncated-normally distributed `NUMERIC(5, 2)` between 65.00 and 100.00.
   - **Document Type**: Hashed selection across standard types (`Mortgage Request`, `Personal Loan Application`, `Proof of Income`, `Identity Verification`, `Tax Return`).
   - **Region & Branch**: Distributed deterministically across 5 regions (`North`, `South`, `East`, `West`, `Central`) and 20 branch codes.
   - **Operator Team**: Hashed assignment into teams (`Team Alpha`, `Team Beta`, `Team Gamma`, `FastTrack Ops`).

---

## 4. Idempotent Population Strategy

To ensure safe, repeatable generation without risk of partial failures or duplicate key errors, population will use PostgreSQL UPSERT syntax:

```sql
INSERT INTO synthetic_extensions (
    application_id, document_type, page_count, branch, operator_team,
    priority, sla_target_hours, region, channel, quality_score,
    error_flag, rejection_flag, updated_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
)
ON CONFLICT (application_id) DO UPDATE SET
    document_type = EXCLUDED.document_type,
    page_count = EXCLUDED.page_count,
    branch = EXCLUDED.branch,
    operator_team = EXCLUDED.operator_team,
    priority = EXCLUDED.priority,
    sla_target_hours = EXCLUDED.sla_target_hours,
    region = EXCLUDED.region,
    channel = EXCLUDED.channel,
    quality_score = EXCLUDED.quality_score,
    error_flag = EXCLUDED.error_flag,
    rejection_flag = EXCLUDED.rejection_flag,
    updated_at = NOW();
```

- **Batching**: Process in batches of 1,000 using `psycopg2.extras.execute_values` inside atomic transactions.
- **Audit**: Log completion status to `data_loads`.

---

## 5. Data Validation Checks

Phase 8.1B will execute the following automated validation checks post-generation:

1. **Record Count Integrity**: `COUNT(synthetic_extensions) == COUNT(applications) == 31,509`.
2. **Referential Integrity**: Zero orphan records (`0` records in `synthetic_extensions` without a matching `application_id` in `applications`).
3. **Constraint Integrity**:
   - `SELECT COUNT(*) FROM synthetic_extensions WHERE priority NOT IN ('low', 'normal', 'high', 'urgent')` must equal `0`.
   - `SELECT COUNT(*) FROM synthetic_extensions WHERE quality_score < 0 OR quality_score > 100` must equal `0`.
4. **Determinism Verification**: Re-running generator on clean target produces zero changed values.

---

## 6. Risks & Open Questions

- **Risk**: Event log outcome vs synthetic flag divergence.
  - *Mitigation*: Ensure `rejection_flag` and `error_flag` in synthetic extensions complement, rather than contradict, source event statuses in `applications`.
- **Performance**: Batch insertion of 31,509 rows taking excessive time.
  - *Mitigation*: Use batch `execute_values` or bulk transaction blocks to complete insertion in under 5 seconds.

---

## 7. Bounded Implementation Plan for Phase 8.1B

When Phase 8.1B is initiated, implementation will strictly follow these bounded steps:

1. Create `scripts/generate_synthetic_extensions.py`:
   - Command-line arguments: `--seed`, `--batch-size`, `--dry-run`.
   - Reads all 31,509 `application_id`s from `applications`.
   - Computes deterministic attributes per application.
   - Executes batch UPSERT into `synthetic_extensions`.
   - Records metadata in `data_loads`.
2. Add pytest test suite in `tests/test_synthetic_extensions.py`:
   - Test generator determinism and seed consistency.
   - Test database UPSERT idempotency.
   - Test check constraint compliance.
3. Run existing test suite (`pytest`) to confirm 100% pass rate.
