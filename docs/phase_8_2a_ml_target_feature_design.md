# Phase 8.2A — ML Target & Feature Design Specification

## Executive Summary

This document specifies the design for **Machine Learning Target Definitions, Feature Engineering, Leakage Guardrails, Evaluation Strategy, and Model Architecture** for **Phase 8.2** of the **AI-Powered Document Intelligence & Operations Analytics** project.

The goal of Phase 8.2 is to complement the descriptive BI dashboards with predictive capabilities:
1. **Cycle-Time Regression**: Predicting total application processing duration (in days/hours) at the point of application submission.
2. **SLA Risk Classification**: Classifying whether an application is at high risk of breaching operational SLA targets at submission time.

---

## 1. Target Definitions

### 1.1 Representation of Processing Duration
In the BPI Challenge 2017 dataset, processing duration is derived strictly from real event timestamps in `applications` and `view_application_metrics`:
- $\text{processing\_hours} = \frac{\text{last\_event\_time} - \text{first\_event\_time}}{3600\text{ seconds}}$
- $\text{processing\_days} = \frac{\text{last\_event\_time} - \text{first\_event\_time}}{86400\text{ seconds}}$

Across all 31,509 cases in PostgreSQL:
- **Mean Processing Time**: 525.59 hours (**21.90 days**)
- **Median Processing Time**: 342.10 hours (**14.25 days**)
- **Min / Max**: 0.06 hours (0.002 days) to 6,865.74 hours (286.07 days)
- **Missing / Null Count**: 0 nulls across all 31,509 cases.

### 1.2 Cycle-Time Regression Target ($y_{\text{reg}}$)
- **Primary Regression Target**: $y_{\text{reg}} = \text{processing\_days}$ (continuous float $\ge 0.0$).
- **Transformed Target for Skew Mitigation**: Because processing duration is heavily right-skewed (skewness $> 3.5$), models (such as Linear/Ridge Regression or Neural Networks) will train on log-transformed targets:
  $$y_{\text{log}} = \log(1 + \text{processing\_days})$$
- Predictions are converted back to original scale using $\exp(\hat{y}_{\text{log}}) - 1$ for operational evaluation (MAE, RMSE in days).

### 1.3 SLA Risk Classification Targets ($y_{\text{cls}}$)
Because synthetic SLA targets in `synthetic_extensions` model turn-around expectations ($12, 24, 48, 72$ hours) while the real financial event log spans multi-week loan approval cycles, a dual target design is specified:

1. **Strict Synthetic SLA Breach Target ($y_{\text{synth\_sla}}$)**:
   $$y_{\text{synth\_sla}} = \begin{cases} 1 & \text{if } \text{processing\_hours} > \text{sla\_target\_hours} \\ 0 & \text{otherwise} \end{cases}$$
   - *Empirical Rate*: 98.80% positive (31,130 / 31,509).
   - *Use Case*: Identifies extreme fast-track completions (the 1.2% that meet strict synthetic turnaround).
   - *Challenge*: Severe class imbalance requires PR-AUC and F1 evaluation rather than standard accuracy.

2. **Operational Cycle-Time Risk Target ($y_{\text{op\_sla}}$ - Primary ML Classification Target)**:
   $$y_{\text{op\_sla}} = \begin{cases} 1 & \text{if } \text{processing\_days} > T_{\text{threshold}} \\ 0 & \text{otherwise} \end{cases}$$
   - **Benchmark Threshold ($T_{\text{threshold}} = 21.90\text{ days}$ [Dataset Mean])**: Yields ~38.4% high-risk positive class rate.
   - **Upper-Quartile Threshold ($T_{\text{threshold}} = 30.00\text{ days}$ [Upper 75th Percentile])**: Yields ~25.0% high-risk positive class rate.
   - *Use Case*: Actionable operational early-warning score for triage teams to flag cases likely to take over 3 weeks.

### 1.4 Distinguishing Real Events from Synthetic Labels

| Attribute Category | Source Table | Nature | Examples | Usage in ML |
| :--- | :--- | :--- | :--- | :--- |
| **Real Process Outcomes** | `applications`, `events` | Historical Facts | `processing_days`, `first_event_time`, `requested_amount` | Targets / Real Predictors |
| **Synthetic Metadata** | `synthetic_extensions` | Operational Demonstration | `priority`, `page_count`, `quality_score`, `sla_target_hours`, `branch` | Feature Predictors |

### 1.5 Trace Censoring & Incompleteness Handling
- All 31,509 application traces in PostgreSQL have valid `first_event_time` and `last_event_time` values.
- Traces with $\text{processing\_hours} < 0.10$ hours (6 minutes) represent immediate automated refusals or withdrawals. These are retained to ensure realistic model performance across all submission outcomes.

---

## 2. Feature Availability & Leakage Audit

### 2.1 At-Start Predictor Features (t0 - Submission Time)
To prevent data leakage, **only features known at the exact moment of application registration** may be fed into the model:

#### Real Source Features (`applications` table):
1. `requested_amount` (Numeric float, log-transformed for scaling)
2. `application_type` (Categorical: `New credit`, `Limit raise`)
3. `loan_goal` (Categorical: 14 distinct loan goals e.g. `Home improvement`, `Car`, `Existing loan takeover`)
4. `submission_hour` (Numeric integer 0–23, derived from `first_event_time`)
5. `submission_day_of_week` (Numeric integer 0–6, derived from `first_event_time`)
6. `submission_month` (Numeric integer 1–12, derived from `first_event_time`)
7. `is_weekend` (Boolean integer 0/1, derived from `first_event_time`)

#### Synthetic Extension Features (`synthetic_extensions` table):
8. `document_type` (Categorical: `Mortgage Application`, `Personal Loan Request`, `Proof of Income`, `Identity Verification`, `Tax Return`)
9. `page_count` (Numeric integer 1–25)
10. `branch` (Categorical: 20 branch codes)
11. `operator_team` (Categorical: 5 operational teams)
12. `priority` (Categorical ordinal: `low` [1], `normal` [2], `high` [3], `urgent` [4])
13. `region` (Categorical: 5 regions)
14. `channel` (Categorical: `Online Portal`, `Mobile App`, `In-Person Branch`, `Partner Referral`, `Mail/Post`)
15. `quality_score` (Numeric float 65.00–100.00)
16. `sla_target_hours` (Numeric integer 12, 24, 48, 72)

### 2.2 Target Leakage Audit (STRICTLY EXCLUDED FEATURES)
The following fields represent downstream process execution state and **MUST NOT** be included in at-start predictive models:

> [!CAUTION]
> **Data Leakage Risks**:
> - `event_count`: Directly correlates with total processing duration ($r > 0.72$). Known only after trace completes.
> - `last_event_time`: Directly forms the target variable ($\text{last\_event\_time} - \text{first\_event\_time}$).
> - `complete_count`, `suspend_count`, `withdraw_count`: Accumulated throughout execution.
> - `workflow_activity_count`, `offer_activity_count`, `application_activity_count`: Intermediate event counts.
> - `status`: Final outcome status (`Approved`, `Cancelled`, `Refused`).
> - `error_flag`, `rejection_flag`: Downstream outcome flags.

---

## 3. Evaluation Design

### 3.1 Train / Test Splitting Strategy
- **Primary Split**: Stratified 80/20 train/test split using fixed seed (`seed=42`).
  - Train set: **25,207** cases (80%)
  - Test set: **6,302** cases (20%)
- **Validation Split**: 5-fold Stratified Cross-Validation on training set for hyperparameter tuning.
- **Temporal Out-of-Time Validation**: Secondary temporal split where training is conducted on applications submitted before `2017-01-01` and evaluated on applications submitted in 2017 to test temporal stability.

### 3.2 Model Architecture & Baselines

#### Regression Baselines & Models ($y_{\text{reg}}$):
1. **Dummy Baseline**: Predicts training set median duration ($\text{MAE} \approx 12.5$ days).
2. **Ridge Regression**: Linear baseline with L2 regularization on One-Hot encoded features.
3. **Random Forest Regressor**: Non-linear ensemble model (`n_estimators=100`, `max_depth=10`).
4. **LightGBM / Gradient Boosting Regressor**: High-performance gradient boosted decision tree.

#### Classification Baselines & Models ($y_{\text{cls}}$):
1. **Dummy Baseline**: Most frequent class / Stratified random guess ($\text{ROC-AUC} = 0.50$).
2. **Logistic Regression**: Linear classifier with L2 penalty (`C=1.0`).
3. **Random Forest Classifier**: Non-linear ensemble classifier (`n_estimators=100`, `max_depth=10`).
4. **LightGBM Classifier**: Gradient boosted tree classifier optimized for binary log-loss.

### 3.3 Evaluation Metrics
- **Classification Metrics**:
  - Primary Metric: **ROC-AUC** (Receiver Operating Characteristic - Area Under Curve).
  - Secondary Metrics: **PR-AUC** (Precision-Recall AUC), **F1-Score**, **Precision**, **Recall**, **Brier Score** (calibration quality).
  - Target Goal: $\text{ROC-AUC} \ge 0.75$.
- **Regression Metrics**:
  - **MAE** (Mean Absolute Error in days).
  - **RMSE** (Root Mean Squared Error in days).
  - **$R^2$ Score** (Coefficient of Determination).

---

## 4. Bounded Implementation Plan for Phase 8.2B

When Phase 8.2B is initiated, implementation will be strictly bounded to the following components:

### 4.1 New Modules to Create
1. **`src/ml/feature_engineering.py`**:
   - `extract_features(df)`: Converts database query result into X (features DataFrame) and y (target Series).
   - One-Hot Encoding for categorical features (`application_type`, `loan_goal`, `document_type`, `branch`, `operator_team`, `region`, `channel`).
   - Feature scaling for numeric inputs (`requested_amount`, `quality_score`, `page_count`).
2. **`src/ml/sla_predictor.py`**:
   - `SLARiskPredictor`: Wrapper class for training, cross-validation, hyperparameter tuning, model evaluation, and saving/loading model artifacts to `models/sla_predictor.joblib`.
3. **`tests/test_ml_pipeline.py`**:
   - Automated unit test suite verifying feature extraction, shape stability, zero leakage, model reproducibility (`seed=42`), cross-validation, and inference output keys.

### 4.2 Acceptance Criteria
1. Feature pipeline transforms all 31,509 cases into valid numerical feature matrix without NaNs or infinite values.
2. `test_ml_pipeline.py` tests pass 100%.
3. Full test suite (`pytest`) continues to pass cleanly.
4. Zero modifications to PostgreSQL schemas, source data, SQL views, or Superset dashboards.
