"""Base model interface for all Aureon ML models."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("aureon.ml.models")


@dataclass
class ModelMetadata:
    """Metadata for a trained model."""

    model_id: str
    name: str
    version: str
    model_type: str
    is_loaded: bool = False
    parameters: dict[str, Any] | None = None


class BaseModel(ABC):
    """Abstract base class for ML models.

    All models must implement load, predict, and metadata methods.
    """

    def __init__(self, model_id: str, name: str, version: str = "0.1.0") -> None:
        self.model_id = model_id
        self.name = name
        self.version = version
        self._is_loaded = False
        logger.info("Model registered: %s (%s v%s)", name, model_id, version)

    @abstractmethod
    def load(self, path: str | None = None) -> None:
        """Load model weights and configuration.

        Args:
            path: Optional path to model artifacts.
        """
        ...

    @abstractmethod
    def predict(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Run inference on input data.

        Args:
            input_data: Model input features.

        Returns:
            Prediction results with confidence scores.
        """
        ...

    @property
    def is_loaded(self) -> bool:
        """Check if the model is loaded and ready for inference."""
        return self._is_loaded

    @property
    def metadata(self) -> ModelMetadata:
        """Get model metadata."""
        return ModelMetadata(
            model_id=self.model_id,
            name=self.name,
            version=self.version,
            model_type=type(self).__name__,
            is_loaded=self._is_loaded,
        )
