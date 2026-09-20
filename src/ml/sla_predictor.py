"""SLA Risk Classifier & Cycle Time Predictor Pipeline.

Provides trained machine learning pipelines for predicting application turnaround times
and SLA breach risks using scikit-learn models, with artifact persistence and evaluation metrics.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline

from src.ml.feature_engineering import (
    REAL_SOURCE_FEATURES,
    build_preprocessor,
)


class SLARiskPredictor:
    """End-to-end Machine Learning pipeline for SLA Risk Classification & Cycle Time Regression."""

    def __init__(self, feature_subset: str = "full", random_state: int = 42) -> None:
        self.feature_subset = feature_subset
        self.random_state = random_state

        # Classifier Pipeline for Operational SLA Risk
        self.cls_pipeline = Pipeline(
            steps=[
                ("preprocessor", build_preprocessor(feature_subset=self.feature_subset)),
                (
                    "classifier",
                    HistGradientBoostingClassifier(
                        random_state=self.random_state,
                        max_iter=100,
                        learning_rate=0.1,
                    ),
                ),
            ]
        )

        # Regressor Pipeline for Log Processing Days
        self.reg_pipeline = Pipeline(
            steps=[
                ("preprocessor", build_preprocessor(feature_subset=self.feature_subset)),
                (
                    "regressor",
                    HistGradientBoostingRegressor(
                        random_state=self.random_state,
                        max_iter=100,
                        learning_rate=0.1,
                    ),
                ),
            ]
        )

        self.is_fitted = False

    def _select_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """Filter input DataFrame to match the configured feature_subset safely."""
        subset = getattr(self, "feature_subset", "full")
        if subset == "real":
            existing_cols = [col for col in REAL_SOURCE_FEATURES if col in X.columns]
            return X[existing_cols].copy()
        return X

    def fit(self, X: pd.DataFrame, y_cls: pd.Series | np.ndarray, y_reg: pd.Series | np.ndarray) -> SLARiskPredictor:
        """Fit classifier and regressor pipelines on training data.

        Args:
            X: Feature DataFrame (at-start predictors).
            y_cls: Binary classification target (0 or 1).
            y_reg: Log-transformed continuous regression target log1p(processing_days).

        Returns:
            Fitted instance of SLARiskPredictor.
        """
        X_sub = self._select_features(X)
        self.cls_pipeline.fit(X_sub, y_cls)
        self.reg_pipeline.fit(X_sub, y_reg)
        self.is_fitted = True
        return self

    def predict_risk(self, X: pd.DataFrame) -> np.ndarray:
        """Predict binary SLA risk class (0 = Low Risk, 1 = High Risk)."""
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted yet. Call fit() first.")
        X_sub = self._select_features(X)
        return self.cls_pipeline.predict(X_sub)

    def predict_risk_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict probability of SLA breach risk (float 0.0 to 1.0)."""
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted yet. Call fit() first.")
        X_sub = self._select_features(X)
        return self.cls_pipeline.predict_proba(X_sub)[:, 1]

    def predict_cycle_time(self, X: pd.DataFrame) -> np.ndarray:
        """Predict expected processing days in original scale (days)."""
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted yet. Call fit() first.")
        X_sub = self._select_features(X)
        log_preds = self.reg_pipeline.predict(X_sub)
        days_preds = np.expm1(np.maximum(0.0, log_preds))
        return days_preds

    def cross_validate_training(
        self,
        X_train: pd.DataFrame,
        y_cls_train: pd.Series | np.ndarray,
        y_reg_days_train: pd.Series | np.ndarray,
        cv: int = 5,
    ) -> dict[str, float]:
        """Perform Stratified K-Fold cross-validation strictly on training set.

        Args:
            X_train: Training features DataFrame.
            y_cls_train: Binary classification target (training split).
            y_reg_days_train: Continuous processing days (training split).

        Returns:
            Dictionary containing mean CV metrics across folds.
        """
        X_sub = self._select_features(X_train)
        y_cls_arr = np.asarray(y_cls_train)
        y_days_arr = np.asarray(y_reg_days_train)
        y_log_arr = np.log1p(np.maximum(0.0, y_days_arr))

        skf = StratifiedKFold(n_splits=cv, shuffle=True, random_state=self.random_state)

        roc_aucs, pr_aucs, f1s, maes = [], [], [], []

        for train_idx, val_idx in skf.split(X_sub, y_cls_arr):
            X_tr, X_val = X_sub.iloc[train_idx], X_sub.iloc[val_idx]
            y_c_tr, y_c_val = y_cls_arr[train_idx], y_cls_arr[val_idx]
            y_l_tr, y_l_val = y_log_arr[train_idx], y_log_arr[val_idx]
            y_d_val = y_days_arr[val_idx]

            fold_cls = Pipeline(
                steps=[
                    ("preprocessor", build_preprocessor(feature_subset=getattr(self, "feature_subset", "full"))),
                    ("classifier", HistGradientBoostingClassifier(random_state=self.random_state, max_iter=100)),
                ]
            )
            fold_reg = Pipeline(
                steps=[
                    ("preprocessor", build_preprocessor(feature_subset=getattr(self, "feature_subset", "full"))),
                    ("regressor", HistGradientBoostingRegressor(random_state=self.random_state, max_iter=100)),
                ]
            )

            fold_cls.fit(X_tr, y_c_tr)
            fold_reg.fit(X_tr, y_l_tr)

            c_probas = fold_cls.predict_proba(X_val)[:, 1]
            c_preds = fold_cls.predict(X_val)
            r_log_preds = fold_reg.predict(X_val)
            r_days_preds = np.expm1(np.maximum(0.0, r_log_preds))

            roc_aucs.append(float(roc_auc_score(y_c_val, c_probas)))
            pr_aucs.append(float(average_precision_score(y_c_val, c_probas)))
            f1s.append(float(f1_score(y_c_val, c_preds, zero_division=0)))
            maes.append(float(mean_absolute_error(y_d_val, r_days_preds)))

        return {
            "cv_mean_roc_auc": round(float(np.mean(roc_aucs)), 4),
            "cv_mean_pr_auc": round(float(np.mean(pr_aucs)), 4),
            "cv_mean_f1_score": round(float(np.mean(f1s)), 4),
            "cv_mean_mae_days": round(float(np.mean(maes)), 4),
        }

    def evaluate(
        self,
        X_test: pd.DataFrame,
        y_cls_test: pd.Series | np.ndarray,
        y_reg_days_test: pd.Series | np.ndarray,
    ) -> dict[str, float]:
        """Evaluate classifier and regressor performance against ground truth test labels.

        Args:
            X_test: Feature DataFrame for test set.
            y_cls_test: True binary classification target.
            y_reg_days_test: True processing days (original scale).

        Returns:
            Dictionary containing ROC-AUC, PR-AUC, F1, Precision, Recall, MAE, RMSE, and R2 metrics.
        """
        if not self.is_fitted:
            raise RuntimeError("Model is not fitted yet. Call fit() first.")

        # Classification evaluation
        cls_preds = self.predict_risk(X_test)
        cls_probas = self.predict_risk_proba(X_test)

        roc_auc = float(roc_auc_score(y_cls_test, cls_probas))
        pr_auc = float(average_precision_score(y_cls_test, cls_probas))
        f1 = float(f1_score(y_cls_test, cls_preds, zero_division=0))
        precision = float(precision_score(y_cls_test, cls_preds, zero_division=0))
        recall = float(recall_score(y_cls_test, cls_preds, zero_division=0))

        # Regression evaluation
        days_preds = self.predict_cycle_time(X_test)
        mae = float(mean_absolute_error(y_reg_days_test, days_preds))
        rmse = float(np.sqrt(mean_squared_error(y_reg_days_test, days_preds)))
        r2 = float(r2_score(y_reg_days_test, days_preds))

        return {
            "roc_auc": round(roc_auc, 4),
            "pr_auc": round(pr_auc, 4),
            "f1_score": round(f1, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "mae_days": round(mae, 4),
            "rmse_days": round(rmse, 4),
            "r2_score": round(r2, 4),
        }

    def save(self, filepath: str | Path) -> Path:
        """Persist fitted model instance to disk.

        Args:
            filepath: Target file path (.joblib).

        Returns:
            Resolved Path object of saved artifact.
        """
        if not self.is_fitted:
            raise RuntimeError("Cannot save an unfitted model. Call fit() first.")

        target_path = Path(filepath)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, target_path)
        return target_path

    @classmethod
    def load(cls, filepath: str | Path) -> SLARiskPredictor:
        """Load a persisted SLARiskPredictor model instance from disk.

        Args:
            filepath: Path to .joblib artifact.

        Returns:
            Loaded SLARiskPredictor instance.
        """
        source_path = Path(filepath)
        if not source_path.exists():
            raise FileNotFoundError(f"Model artifact not found at: {source_path}")

        predictor = joblib.load(source_path)
        if not isinstance(predictor, cls):
            raise TypeError(f"Loaded object is not an instance of {cls.__name__}")
        return predictor
