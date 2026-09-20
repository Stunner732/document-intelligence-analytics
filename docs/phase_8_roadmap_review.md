# Phase 8 — Roadmap Review & Next-Phase Planning

> Comprehensive review of project roadmap, verified current state, and proposed execution plan for Phase 8.

---

## 1. Current Project Status

The **AI-Powered Document Intelligence & Operations Analytics** project has completed Phases 1 through 7.4.

### Verified Stack & Artifacts
- **PostgreSQL 16.15**: Database `document_intelligence` running in Podman with 6 schema tables.
  - `applications`: **31,509** loan application cases.
  - `events`: **1,202,267** workflow events.
  - `offers`: Validated offer records.
  - `synthetic_extensions`: 0 rows (ready for Phase 8 population).
  - `13` analytical views + `4` materialized views.
- **Python Analytics & Export Layer**:
  - `13` typed query functions in `src/analytics/queries.py`.
  - Batch CSV and Parquet export generators with manifest tracking (`src/analytics/export.py`).
  - `8` Matplotlib/Seaborn visualization functions (`src/analytics/visualization.py`).
- **Apache Superset 6.1.0**:
  - Running in Podman at `http://localhost:8088`.
  - Superset MCP server connected and active at `http://127.0.0.1:5008/mcp`.
  - **3 Published Dashboards**:
    1. **Executive Operations Overview** (ID 1, 9 charts, 3 native filters) — `http://localhost:8088/superset/dashboard/executive-operations-overview/`
    2. **Process Performance** (ID 2, 11 charts, 3 native filters) — `http://localhost:8088/superset/dashboard/2/`
    3. **Resource & Workload** (ID 3, 8 charts, 1 native filter) — `http://localhost:8088/superset/dashboard/3/`
  - All **28 charts** across the 3 dashboards execute with 0 query errors.
- **Test Suite**: **214 / 214 tests passing** (100% success rate across data quality, schema, SQL views, query layer, exports, and visualizations).
- **Git Status**: Clean working tree with respect to tracked repository files.

---

## 2. Roadmap Findings & Intent Analysis

Inspection of committed project documentation reveals the explicit design intent for Phase 8:

1. **`src/config.py` (Line 4)**:
   > *"This module intentionally contains no AI-model configuration. Local model discovery and integration are deferred to Phase 8."*
2. **`PROJECT_STATUS.md` (Line 328)**:
   > *"Phase 7: ML for document classification and SLA-risk modeling"* (Note: Superset BI Dashboards were executed as Phase 7.1–7.4; machine learning and predictive modeling represent the subsequent technical phase).
3. **`README.md` (Line 407)** & **`docs/architecture.md` (Line 409)**:
   > *"Document intelligence layer — Potential future integration of AI/ML components for document classification, automated processing analysis, or synthetic field population. The `synthetic_extensions` table and `docs/synthetic-extension.md` document the design..."*
4. **`docs/synthetic-extension.md`**:
   > Defines the specification for deterministic synthetic operational labels at the loan-application-case grain: `document_type`, `page_count`, `branch`, `operator_team`, `priority`, `region`, `quality_score`, `sla_target_hours`, `error_flag`.

---

## 3. Recommended Next Phase: Phase 8 — Document Intelligence & Predictive Analytics Layer

### Purpose
Transform the static operational process analytics stack into an **AI-Powered Document Intelligence & Predictive Analytics** pipeline by:
1. Populating deterministic synthetic operational labels into the existing `synthetic_extensions` PostgreSQL table following `docs/synthetic-extension.md`.
2. Building a machine learning pipeline for **SLA Risk Classification** and **Cycle Time Prediction** (predicting long-duration applications or SLA breach risk based on initial case attributes and activity sequences).
3. Integrating predictive model outputs into the Python query layer and SQL analytics views.

### Deliverables
- **`src/cleaning/synthetic_generator.py`**: Seed-controlled generator producing deterministic synthetic metadata for all 31,509 cases into `synthetic_extensions`.
- **`src/ml/sla_predictor.py`**: Scikit-Learn / LightGBM pipeline training an SLA risk classifier and processing duration regressor.
- **`src/analytics/predictive_queries.py`**: Python query functions returning SLA breach risk scores and synthetic document metrics.
- **Automated Tests**: Pytest coverage for synthetic generation, model training, feature extraction, and prediction endpoints.

---

## 4. Proposed Bounded Implementation Steps

### Step 8.1 — Synthetic Operational Extension Population
- Implement `src/cleaning/synthetic_generator.py` using a fixed random seed (`42`).
- Derive `document_type`, `page_count`, `priority`, `branch`, `operator_team`, `region`, `quality_score`, and `sla_target_hours` deterministically from application trace properties per `docs/synthetic-extension.md`.
- Populate all 31,509 records into `synthetic_extensions` table with complete lineage metadata tagging as `synthetic`.

### Step 8.2 — SLA Risk & Cycle Time Machine Learning Pipeline
- Create `src/ml/sla_predictor.py`.
- Extract case-level features from `applications` and `view_application_metrics` (requested amount, application type, loan goal, initial event sequence, synthetic priority/page count).
- Train an SLA risk classifier (predicting whether processing duration exceeds `sla_target_hours` or 7 days).
- Evaluate model using standard metrics (ROC-AUC, Precision, Recall, F1-Score) and save trained model artifacts to `models/` (Git-ignored).

### Step 8.3 — Predictive Query Layer & Analytical Integration
- Add predictive query functions in `src/analytics/queries.py` (e.g., `get_sla_risk_summary()`, `get_document_type_performance()`).
- Create view `view_predictive_sla_risk` joining application metrics with synthetic extensions and risk scores.

### Step 8.4 — Automated Test Suite & Documentation
- Write unit tests in `tests/test_synthetic_generator.py` and `tests/test_ml_pipeline.py`.
- Update `README.md` and `docs/architecture.md` with Phase 8 verification details.

---

## 5. Acceptance Criteria

1. **Synthetic Extensions Populated**: `synthetic_extensions` table contains exactly **31,509** rows with zero missing values and deterministic seed verification.
2. **Model Accuracy & Evaluation**: Trained SLA risk model achieves ROC-AUC $\ge 0.75$ on test split with reproducible evaluation metrics.
3. **Query Layer Functional**: New typed Python functions execute cleanly without raw SQL duplication.
4. **Test Suite Execution**: All new tests pass, maintaining **214/214 + new tests passing** (100% success rate).
5. **Zero Disruption**: Zero modifications to raw source events, existing 13 views, or the 3 published Superset dashboards.

---

## 6. Risks & Dependencies

| Risk / Dependency | Mitigation |
| :--- | :--- |
| **Data Contamination** | Synthetic fields strictly isolated to `synthetic_extensions` table and clearly labeled in lineage metadata as synthetic. |
| **Model Reproducibility** | Fixed random seeds (`seed=42`) used for data split and model training. |
| **Test Suite Regressions** | Existing test files remain unmodified; new tests added in dedicated test modules. |

---

## 7. Items Explicitly Out of Scope

- Cloud API deployments (AWS / GCP / Azure).
- Live third-party LLM API calls with paid API keys.
- Destructive modifications to PostgreSQL raw tables (`applications`, `events`, `offers`).
- Modifying existing Superset dashboards 1, 2, or 3.
