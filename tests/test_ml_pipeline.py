"""Unit and integration tests for SLA Risk Classification & Cycle Time ML pipeline."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import train_test_split

from src.database import check_database_connection
from src.ml.feature_engineering import (
    CATEGORICAL_FEATURES,
    LEAKAGE_FEATURES,
    NUMERIC_FEATURES,
    REAL_SOURCE_FEATURES,
    compute_training_threshold,
    load_dataset_from_db,
    prepare_features_and_targets,
)
from src.ml.sla_predictor import SLARiskPredictor


@pytest.fixture(scope="module")
def db_available() -> bool:
    return check_database_connection()


@pytest.fixture(scope="module")
def ml_dataset(db_available: bool) -> tuple[pd.DataFrame, dict[str, pd.Series]]:
    if not db_available:
        pytest.skip("PostgreSQL database not available")

    raw_df = load_dataset_from_db()
    features_df, targets = prepare_features_and_targets(raw_df)
    return features_df, targets


class TestFeatureEngineering:
    """Test feature extraction, scaling, feature ablation, and leakage guardrails."""

    def test_feature_columns_and_leakage_exclusion(self, ml_dataset: tuple[pd.DataFrame, dict[str, pd.Series]]) -> None:
        features_df, targets = ml_dataset

        # Check total rows
        assert len(features_df) == 31509

        # Verify expected feature columns are present
        expected_features = set(NUMERIC_FEATURES + CATEGORICAL_FEATURES)
        assert set(features_df.columns) == expected_features

        # Verify strict leakage exclusion
        for leakage_col in LEAKAGE_FEATURES:
            assert leakage_col not in features_df.columns, f"Target leakage detected! {leakage_col} is in feature columns"

    def test_training_only_threshold_calculation(self) -> None:
        y_train_dummy = pd.Series([5.0, 10.0, 15.0, 20.0, 100.0])
        med_thresh = compute_training_threshold(y_train_dummy, strategy="median")
        mean_thresh = compute_training_threshold(y_train_dummy, strategy="mean")

        assert med_thresh == 15.0
        assert mean_thresh == 30.0

    def test_targets_dictionary_structure(self, ml_dataset: tuple[pd.DataFrame, dict[str, pd.Series]]) -> None:
        features_df, targets = ml_dataset

        assert "processing_days" in targets
        assert "log_processing_days" in targets
        assert "is_sla_breach_operational" in targets
        assert "is_sla_breach_median" in targets
        assert "is_sla_breach_strict" in targets

        for key, series in targets.items():
            assert len(series) == 31509
            assert not series.isna().any()

        # Median threshold target creates exact 50% split (+/- 1%)
        med_risk = targets["is_sla_breach_median"]
        risk_rate = med_risk.mean()
        assert 0.48 <= risk_rate <= 0.52, f"Median SLA risk rate {risk_rate} outside expected balanced range [0.48, 0.52]"


class TestSLARiskPredictor:
    """Test ML model training, feature ablation, prediction, cross-validation, and artifact persistence."""

    def test_unfitted_model_raises_runtime_error(self) -> None:
        predictor = SLARiskPredictor(random_state=42)
        dummy_df = pd.DataFrame({"requested_amount": [1000.0]})

        with pytest.raises(RuntimeError, match="Model is not fitted yet"):
            predictor.predict_risk(dummy_df)

        with pytest.raises(RuntimeError, match="Model is not fitted yet"):
            predictor.predict_risk_proba(dummy_df)

        with pytest.raises(RuntimeError, match="Model is not fitted yet"):
            predictor.predict_cycle_time(dummy_df)

    def test_feature_ablation_real_vs_full(
        self, ml_dataset: tuple[pd.DataFrame, dict[str, pd.Series]]
    ) -> None:
        features_df, targets = ml_dataset
        X_train, X_test, y_cls_train, y_cls_test, y_log_train, y_log_test, y_days_train, y_days_test = (
            train_test_split(
                features_df,
                targets["is_sla_breach_median"],
                targets["log_processing_days"],
                targets["processing_days"],
                test_size=0.20,
                random_state=42,
                stratify=targets["is_sla_breach_median"],
            )
        )

        # 1. Real-Only Features Model
        p_real = SLARiskPredictor(feature_subset="real", random_state=42)
        p_real.fit(X_train[REAL_SOURCE_FEATURES], y_cls_train, y_log_train)
        eval_real = p_real.evaluate(X_test[REAL_SOURCE_FEATURES], y_cls_test, y_days_test)

        # 2. Full Features Model
        p_full = SLARiskPredictor(feature_subset="full", random_state=42)
        p_full.fit(X_train, y_cls_train, y_log_train)
        eval_full = p_full.evaluate(X_test, y_cls_test, y_days_test)

        assert "roc_auc" in eval_real
        assert "roc_auc" in eval_full
        assert eval_real["roc_auc"] > 0.50
        assert eval_full["roc_auc"] > 0.50

    def test_training_cross_validation(
        self, ml_dataset: tuple[pd.DataFrame, dict[str, pd.Series]]
    ) -> None:
        features_df, targets = ml_dataset
        X_train = features_df.head(500)
        y_cls_train = targets["is_sla_breach_median"].head(500)
        y_days_train = targets["processing_days"].head(500)

        predictor = SLARiskPredictor(feature_subset="real", random_state=42)
        cv_metrics = predictor.cross_validate_training(X_train, y_cls_train, y_days_train, cv=3)

        assert "cv_mean_roc_auc" in cv_metrics
        assert "cv_mean_pr_auc" in cv_metrics
        assert "cv_mean_f1_score" in cv_metrics
        assert "cv_mean_mae_days" in cv_metrics
        assert cv_metrics["cv_mean_roc_auc"] >= 0.0

    def test_model_reproducibility(
        self, ml_dataset: tuple[pd.DataFrame, dict[str, pd.Series]]
    ) -> None:
        features_df, targets = ml_dataset
        sample_X = features_df.head(100)
        sample_y_cls = targets["is_sla_breach_median"].head(100)
        sample_y_log = targets["log_processing_days"].head(100)

        p1 = SLARiskPredictor(random_state=42).fit(sample_X, sample_y_cls, sample_y_log)
        p2 = SLARiskPredictor(random_state=42).fit(sample_X, sample_y_cls, sample_y_log)

        preds1 = p1.predict_risk_proba(sample_X)
        preds2 = p2.predict_risk_proba(sample_X)

        np.testing.assert_allclose(preds1, preds2, rtol=1e-5)

    def test_model_artifact_persistence(
        self, ml_dataset: tuple[pd.DataFrame, dict[str, pd.Series]], tmp_path: Path
    ) -> None:
        features_df, targets = ml_dataset
        sample_X = features_df.head(100)
        sample_y_cls = targets["is_sla_breach_median"].head(100)
        sample_y_log = targets["log_processing_days"].head(100)

        predictor = SLARiskPredictor(feature_subset="real", random_state=42).fit(sample_X, sample_y_cls, sample_y_log)
        model_file = tmp_path / "sla_predictor_ablation.joblib"

        saved_path = predictor.save(model_file)
        assert saved_path.exists()

        loaded_predictor = SLARiskPredictor.load(model_file)
        assert loaded_predictor.is_fitted

        orig_preds = predictor.predict_risk_proba(sample_X)
        loaded_preds = loaded_predictor.predict_risk_proba(sample_X)

        np.testing.assert_allclose(orig_preds, loaded_preds, rtol=1e-5)
