"""Demand prediction model: XGBoost-based zone-level incident forecasting.

Predicts emergency incident counts per zone per future time window
using temporal, spatial, operational, and historical features.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from .data_pipeline import ALL_ZONES, TIME_WINDOW_SEC, TrainingDataset, TimeWindowFeatures

logger = logging.getLogger("aureon.ml.demand_model")


@dataclass
class DemandPrediction:
    """Predicted demand for a single zone."""

    zone: str
    predicted_incidents: float
    confidence_lower: float
    confidence_upper: float


@dataclass
class DemandForecast:
    """Forecast across all zones for a time window."""

    predictions: list[DemandPrediction]
    forecast_time_sec: float
    total_predicted_incidents: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "forecast_time_sec": self.forecast_time_sec,
            "total_predicted": round(self.total_predicted_incidents, 2),
            "by_zone": {p.zone: round(p.predicted_incidents, 3) for p in self.predictions},
        }


@dataclass
class ModelMetrics:
    """Training and evaluation metrics for the demand model."""

    rmse: float = 0.0
    mae: float = 0.0
    r2: float = 0.0
    cv_rmse_mean: float = 0.0
    cv_rmse_std: float = 0.0
    feature_importance: dict[str, float] = field(default_factory=dict)
    training_samples: int = 0
    feature_names: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rmse": round(self.rmse, 4),
            "mae": round(self.mae, 4),
            "r2": round(self.r2, 4),
            "cv_rmse_mean": round(self.cv_rmse_mean, 4),
            "cv_rmse_std": round(self.cv_rmse_std, 4),
            "feature_importance": {
                k: round(v, 4) for k, v in sorted(
                    self.feature_importance.items(), key=lambda x: -x[1]
                )
            },
            "training_samples": self.training_samples,
            "num_features": len(self.feature_names),
        }


class DemandPredictionModel:
    """XGBoost-based emergency demand prediction model.

    Predicts incident count per zone per 30-minute time window.
    """

    FEATURE_NAMES = [
        "hour_of_day",
        "is_weekend",
        "tp_early_morning",
        "tp_morning_peak",
        "tp_midday",
        "tp_evening_peak",
        "tp_night",
        "tp_late_night",
        "zone_latitude",
        "zone_longitude",
        "zone_road_density",
        "avg_congestion",
        "available_ambulances",
        "busy_ambulances",
        "er_occupancy",
        "icu_occupancy",
        "active_incidents_zone",
        "prev_window_zone_incidents",
        "prev_2windows_zone_incidents",
        "prev_window_total_incidents",
        "prev_window_avg_rt",
    ]

    def __init__(self) -> None:
        self.model: XGBRegressor | None = None
        self.scaler: StandardScaler = StandardScaler()
        self.metrics: ModelMetrics = ModelMetrics()
        self._is_trained: bool = False

    @property
    def is_trained(self) -> bool:
        return self._is_trained

    def train(self, dataset: TrainingDataset) -> ModelMetrics:
        """Train the demand prediction model on collected simulation data.

        Args:
            dataset: Training dataset from SimulationDataExtractor.

        Returns:
            ModelMetrics with training results and feature importance.
        """
        X_raw, y = dataset.to_X_y()
        if not X_raw:
            raise ValueError("Empty training dataset")

        X = np.array(X_raw, dtype=np.float32)
        y_arr = np.array(y, dtype=np.float32)

        self.FEATURE_NAMES = dataset.feature_names

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Train XGBoost
        self.model = XGBRegressor(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=3,
            reg_alpha=0.1,
            reg_lambda=1.0,
            random_state=42,
            objective="reg:squarederror",
        )

        self.model.fit(X_scaled, y_arr)
        self._is_trained = True

        # Compute metrics
        y_pred = self.model.predict(X_scaled)
        residuals = y_arr - y_pred

        rmse = float(np.sqrt(np.mean(residuals ** 2)))
        mae = float(np.mean(np.abs(residuals)))
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((y_arr - np.mean(y_arr)) ** 2)
        r2 = float(1.0 - ss_res / max(ss_tot, 1e-10))

        # Cross-validation
        n_splits = min(5, len(X_scaled) // max(len(ALL_ZONES), 1))
        if n_splits >= 2:
            cv_scores = cross_val_score(
                self.model, X_scaled, y_arr,
                cv=n_splits, scoring="neg_root_mean_squared_error",
            )
            cv_rmse_mean = float(-cv_scores.mean())
            cv_rmse_std = float(cv_scores.std())
        else:
            cv_rmse_mean = rmse
            cv_rmse_std = 0.0

        # Feature importance
        importances = self.model.feature_importances_
        feature_importance = {
            name: float(imp)
            for name, imp in zip(self.FEATURE_NAMES, importances)
        }

        self.metrics = ModelMetrics(
            rmse=rmse,
            mae=mae,
            r2=r2,
            cv_rmse_mean=cv_rmse_mean,
            cv_rmse_std=cv_rmse_std,
            feature_importance=feature_importance,
            training_samples=len(X),
            feature_names=self.FEATURE_NAMES,
        )

        logger.info(
            "Demand model trained: RMSE=%.4f, MAE=%.4f, R²=%.4f (n=%d)",
            rmse, mae, r2, len(X),
        )
        return self.metrics

    def predict(self, features: TimeWindowFeatures) -> DemandPrediction:
        """Predict demand for a single zone given current features."""
        if not self._is_trained or self.model is None:
            raise RuntimeError("Model not trained. Call train() first.")

        feat_dict = features.to_feature_dict()
        X = np.array([[feat_dict.get(name, 0.0) for name in self.FEATURE_NAMES]], dtype=np.float32)
        X_scaled = self.scaler.transform(X)

        pred = float(self.model.predict(X_scaled)[0])
        pred = max(0.0, pred)  # Incidents can't be negative

        # Simple confidence interval based on model RMSE
        rmse = self.metrics.rmse
        return DemandPrediction(
            zone=features.zone,
            predicted_incidents=pred,
            confidence_lower=max(0.0, pred - 1.96 * rmse),
            confidence_upper=pred + 1.96 * rmse,
        )

    def forecast(
        self,
        current_features: list[TimeWindowFeatures],
    ) -> DemandForecast:
        """Forecast demand across all zones.

        Args:
            current_features: Feature snapshots for each zone at current time.

        Returns:
            DemandForecast with per-zone predictions.
        """
        predictions = []
        total = 0.0

        for feat in current_features:
            pred = self.predict(feat)
            predictions.append(pred)
            total += pred.predicted_incidents

        return DemandForecast(
            predictions=predictions,
            forecast_time_sec=current_features[0].window_end_sec if current_features else 0.0,
            total_predicted_incidents=total,
        )
