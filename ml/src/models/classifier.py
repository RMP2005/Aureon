"""Event classification model interface.

Defines the contract for models that classify urban events
(emergencies, incidents, anomalies) from input data.
"""

from __future__ import annotations

import logging
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any

from src.models.base import BaseModel

logger = logging.getLogger("aureon.ml.classifier")


@dataclass
class ClassificationResult:
    """Result of event classification.

    Attributes:
        event_type: Predicted event type label.
        confidence: Prediction confidence score (0.0 to 1.0).
        probabilities: Per-class probability distribution.
        metadata: Additional classification metadata.
    """

    event_type: str
    confidence: float
    probabilities: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseClassifier(BaseModel):
    """Abstract base class for event classifiers.

    Subclasses implement specific classification algorithms
    (e.g., neural networks, gradient boosted trees, etc.).

    Expected input features may include:
        - sensor_readings: dict of sensor data
        - location: geographic coordinates
        - timestamp: event timestamp
        - environmental_context: weather, time of day, etc.
    """

    SUPPORTED_EVENT_TYPES: list[str] = [
        "fire",
        "flood",
        "earthquake",
        "hazmat",
        "medical",
        "traffic_accident",
        "structural_collapse",
        "power_outage",
        "civil_unrest",
        "weather_emergency",
    ]

    def __init__(self, model_id: str = "event-classifier", version: str = "0.1.0") -> None:
        super().__init__(model_id=model_id, name="Event Classifier", version=version)

    @abstractmethod
    def classify(self, features: dict[str, Any]) -> ClassificationResult:
        """Classify an event based on input features.

        Args:
            features: Feature dictionary containing sensor data,
                     location, timestamp, and context.

        Returns:
            ClassificationResult with predicted type and confidence.
        """
        ...

    def predict(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Run inference — delegates to classify()."""
        result = self.classify(input_data)
        return {
            "event_type": result.event_type,
            "confidence": result.confidence,
            "probabilities": result.probabilities,
        }
