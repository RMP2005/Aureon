"""Inference serving interface.

Defines the contract for serving ML models via the backend API.
"""

from __future__ import annotations

import logging
from typing import Any

from src.models.base import BaseModel

logger = logging.getLogger("aureon.ml.inference")


class ModelRegistry:
    """Registry for managing loaded ML models."""

    def __init__(self) -> None:
        self._models: dict[str, BaseModel] = {}
        logger.info("ModelRegistry initialized")

    def register(self, model: BaseModel) -> None:
        """Register a model in the registry."""
        self._models[model.model_id] = model
        logger.info("Registered model: %s", model.model_id)

    def get(self, model_id: str) -> BaseModel | None:
        """Get a model by ID."""
        return self._models.get(model_id)

    def list_models(self) -> list[dict[str, Any]]:
        """List all registered models with metadata."""
        return [
            {
                "model_id": m.model_id,
                "name": m.name,
                "version": m.version,
                "is_loaded": m.is_loaded,
                "type": type(m).__name__,
            }
            for m in self._models.values()
        ]

    def predict(self, model_id: str, input_data: dict[str, Any]) -> dict[str, Any]:
        """Run inference on a registered model.

        Args:
            model_id: ID of the model to use.
            input_data: Input features.

        Returns:
            Prediction results.

        Raises:
            KeyError: If model_id is not registered.
            RuntimeError: If model is not loaded.
        """
        model = self._models.get(model_id)
        if model is None:
            raise KeyError(f"Model '{model_id}' not found in registry")
        if not model.is_loaded:
            raise RuntimeError(f"Model '{model_id}' is not loaded")
        return model.predict(input_data)


# Global registry instance
registry = ModelRegistry()
