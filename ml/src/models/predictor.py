"""Prediction model interface.

Defines the contract for models that generate forecasts
and predictions for urban simulation scenarios.
"""

from __future__ import annotations

import logging
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any

from src.models.base import BaseModel

logger = logging.getLogger("aureon.ml.predictor")


@dataclass
class PredictionResult:
    """Result of a prediction.

    Attributes:
        predictions: List of predicted values (time-series or single).
        confidence_interval: Optional lower/upper bounds.
        horizon: Prediction horizon description.
        features_used: List of feature names used.
        metadata: Additional prediction metadata.
    """

    predictions: list[float] = field(default_factory=list)
    confidence_interval: dict[str, list[float]] | None = None
    horizon: str = ""
    features_used: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class BasePredictor(BaseModel):
    """Abstract base class for prediction models.

    Subclasses implement specific prediction algorithms for:
        - Event occurrence likelihood
        - Resource demand forecasting
        - Infrastructure failure prediction
        - Population movement patterns
        - Environmental condition forecasting
    """

    def __init__(self, model_id: str = "predictor", version: str = "0.1.0") -> None:
        super().__init__(model_id=model_id, name="Prediction Engine", version=version)

    @abstractmethod
    def forecast(
        self,
        historical_data: dict[str, Any],
        horizon_steps: int = 10,
    ) -> PredictionResult:
        """Generate predictions for future time steps.

        Args:
            historical_data: Historical feature data for context.
            horizon_steps: Number of future steps to predict.

        Returns:
            PredictionResult with forecasted values.
        """
        ...

    @abstractmethod
    def detect_anomalies(
        self,
        data: dict[str, Any],
        threshold: float = 0.95,
    ) -> list[dict[str, Any]]:
        """Detect anomalies in input data.

        Args:
            data: Input data to analyze.
            threshold: Anomaly detection threshold.

        Returns:
            List of detected anomalies with metadata.
        """
        ...

    def predict(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Run inference — delegates to forecast()."""
        horizon = input_data.get("horizon_steps", 10)
        result = self.forecast(input_data, horizon_steps=horizon)
        return {
            "predictions": result.predictions,
            "confidence_interval": result.confidence_interval,
            "horizon": result.horizon,
        }
