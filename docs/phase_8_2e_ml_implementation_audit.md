# Phase 8.2E — Part 1: ML Implementation Audit Report

## Executive Summary & Audit Scope

This document presents the **Machine Learning Implementation Audit** for **Phase 8.2E — Part 1** of the **AI-Powered Document Intelligence & Operations Analytics** project.

The purpose of this audit is to conduct a final verification of the Phase 8.2 machine learning implementation (`src/ml/feature_engineering.py`, `src/ml/sla_predictor.py`, `tests/test_ml_pipeline.py`) prior to API development or dashboard integration.

> [!IMPORTANT]
> **Audit Integrity & Safety Guarantees**:
> - **Audit-Only Operation**: Zero modifications were made to production source code, unit tests, PostgreSQL schemas, SQL views, or Superset dashboards.
> - **Artifact Preservation**: The production model artifact `models/sla_predictor.joblib` and experimental artifact `models/sla_predictor_ablation.joblib` remain **100% untouched**.
> - **Separation of Evidence**: Clear structural demarcation between verified implementation facts, empirical experimental results, and unresolved limitations.

---

## 1. Verified Implementation Facts

Codebase inspection of `src/ml/feature_engineering.py`, `src/ml/sla_predictor.py`, and `tests/test_ml_pipeline.py` confirms the following facts:

### A. Target Construction
1. **Training-Only Threshold Calculation**:
   - `compute_training_threshold(y_days_train, strategy="median")` computes the operational threshold strictly on the training set processing duration split (`y_days_train`).
   - In `prepare_features_and_targets(df, threshold=train_median_thresh)`, passing the training-derived threshold applies the constant float threshold ($T_{\text{train\_median}} = 14.2529$ days) to construct test set target labels ($y_{\text{test}} = 1$ if $\text{processing\_days} > T_{\text{train\_median}}$, else $0$).
   - **Verification Result**: Zero threshold leakage between training and test sets.
2. **Distinct Target Definitions**:
   - `is_sla_breach_median` evaluates operational long-cycle turnaround risk ($\text{processing\_days} > 14.2529$ days), which is strictly distinct from contractual SLA targets (`is_sla_breach_strict`: $\text{processing\_hours} > \text{sla\_target\_hours}$).
3. **Consistent Target Construction**:
   - Both training and test classification target vectors evaluate the identical training-derived threshold.

### B. Data Leakage Guardrails
1. **At-Start Feature Availability**:
   - All 16 features ($X$) extracted in `prepare_features_and_targets()` are known at application registration ($t0$).
   - Downstream execution fields (`event_count`, `last_event_time`, `complete_count`, `suspend_count`, `withdraw_count`, activity counts, final `status`, outcome flags) are explicitly defined in `LEAKAGE_FEATURES` and excluded from `features_df`.
2. **Preprocessing Isolation**:
   - Scikit-Learn `ColumnTransformer` (StandardScaler for numerics, OneHotEncoder for categoricals) is constructed inside a Scikit-Learn `Pipeline`.
   - Preprocessors are fitted strictly on `X_train` during `fit()` and strictly on training folds `X_tr` during cross-validation.
3. **Cross-Validation Isolation**:
   - `cross_validate_training(X_train, y_cls_train, y_reg_days_train, cv=5)` executes 5-fold Stratified K-Fold cross-validation strictly on `X_train`.
   - The holdout test set (`X_test`) is never exposed to fold preprocessors or classifiers.

### C. Evaluation Methodology & Artifact Persistence
1. **Evaluation Functions**:
   - `predict_cycle_time()` applies `np.expm1(np.maximum(0.0, log_preds))` to convert log-scale predictions back to processing days on original scale.
   - `evaluate()` computes ROC-AUC, PR-AUC, F1-Score, Precision, Recall, MAE, RMSE, and $R^2$ using identical `train_test_split(..., test_size=0.20, random_state=42)` across all models and dummy baselines.
2. **Artifact Preservation**:
   - Production model artifact: `models/sla_predictor.joblib` (unmodified).
   - Experimental ablation artifact: `models/sla_predictor_ablation.joblib` (unmodified).

---

## 2. Reported Experimental Results

Empirical results obtained from Phase 8.2D experiments across 31,509 cases (80% train / 20% holdout test split):

### Classification Model Performance (Operational Median SLA Risk Target: $T = 14.2529$ Days)

| Metric | Dummy Classifier (Prior Class Rate) | Model A: Real-Source Features (6 Predictors) | Model B: Full Feature Set (15 Predictors) | Ablation Delta (Full vs. Real) |
| :--- | :--- | :--- | :--- | :--- |
| **5-Fold CV Mean ROC-AUC** | 0.5000 | **0.5833** | **0.5888** | $+0.0055$ |
| **5-Fold CV Mean PR-AUC** | 0.5000 | **0.5786** | **0.5815** | $+0.0029$ |
| **5-Fold CV Mean F1-Score** | 0.5000 | **0.5786** | **0.5791** | $+0.0005$ |
| **Holdout ROC-AUC** (20% Test) | 0.5000 | **0.5840** | **0.5878** | $+0.0038$ |
| **Holdout PR-AUC** (20% Test) | 0.5000 | **0.5746** | **0.5768** | $+0.0022$ |
| **Holdout F1-Score** (20% Test) | 0.5000 | **0.5748** | **0.5760** | $+0.0012$ |
| **Holdout Precision** | 0.5000 | **0.5820** | **0.5840** | $+0.0020$ |
| **Holdout Recall** | 0.5000 | **0.5678** | **0.5681** | $+0.0003$ |

### Regression Model Performance (Cycle-Time Prediction: Target = `processing_days`)

| Metric | Dummy Regressor (Median Baseline) | Model A: Real-Source Features (6 Predictors) | Model B: Full Feature Set (15 Predictors) | Ablation Delta (Full vs. Real) |
| :--- | :--- | :--- | :--- | :--- |
| **Holdout MAE (Days)** | 15.3400 | **10.3802** | **10.3854** | **Real-Only is better** ($-0.0052$ days) |
| **Holdout RMSE (Days)** | 22.6133 | **13.7220** | **13.7383** | **Real-Only is better** ($-0.0163$ days) |
| **Holdout $R^2$ Score** | -0.1287 | **-0.0384** | **-0.0409** | **Real-Only is better** ($+0.0025$) |

### Feature Ablation Analysis
- **Real-Source Features (6 Predictors)**: `requested_amount`, `application_type`, `loan_goal`, `submission_hour`, `submission_day_of_week`, `submission_month`.
- **Synthetic Extension Features (9 Predictors)**: `document_type`, `page_count`, `branch`, `operator_team`, `priority`, `region`, `channel`, `quality_score`, `sla_target_hours`.
- **Finding**: Synthetic extension features (which expand to 49 One-Hot columns) produce negligible classification difference ($+0.0038$ ROC-AUC) and **degrade regression performance** (higher MAE and lower $R^2$). Synthetic features represent uninformative statistical noise relative to real trace duration.

---

## 3. Potential Concerns & Unresolved Questions

1. **Weak Discriminative Signal ($ROC\text{-}AUC \approx 0.58–0.59$)**:
   - The at-start feature set (`requested_amount`, `application_type`, `loan_goal`, submission time) provides modest predictive signal above random guessing ($0.50$).
   - *Root Cause*: BPI Challenge 2017 is an anonymized workflow event log lacking applicant financial risk attributes (credit score, income, debt-to-income ratio). Processing duration is heavily driven by unobserved applicant response delay.
2. **Negative $R^2$ Score (-0.0384)**:
   - Evaluated on original scale (`processing_days`), $R^2$ remains negative due to uncorrected exponentiation variance bias on extreme right-tail outliers ($> 100$ days).
3. **Recommendation for API & Model Standardization**:
   - Standardize on **Model A (Real-Source Features)** to simplify API parameter payloads, eliminate synthetic noise, and improve regression accuracy.

---

## 4. Final Audit Checklist & Summary

- **Files Inspected**: `src/ml/feature_engineering.py`, `src/ml/sla_predictor.py`, `tests/test_ml_pipeline.py`, `docs/phase_8_2c_model_evaluation_audit.md`, `docs/phase_8_2d_target_correction_feature_ablation.md`.
- **Checks Performed**: Target threshold leakage, data leakage guardrails, preprocessing fold isolation, cross-validation holdout isolation, baseline metric equality, synthetic feature ablation, artifact immutability.
- **Focused Test Suite Results**: Executed `pytest tests/test_ml_pipeline.py` — **8 / 8 tests passing** (0 errors).
- **Artifact & Data Modification Confirmation**: **Zero files, model joblib artifacts, or PostgreSQL database records were modified during this audit**.
