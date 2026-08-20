"""Model training orchestrator.

Provides the interface for training ML models with
experiment tracking and checkpointing.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("aureon.ml.training")


@dataclass
class TrainingConfig:
    """Configuration for a training run."""

    epochs: int = 100
    batch_size: int = 32
    learning_rate: float = 1e-3
    validation_split: float = 0.2
    early_stopping_patience: int = 10
    checkpoint_dir: str = "./checkpoints"
    experiment_name: str = "default"
    hyperparameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class TrainingResult:
    """Result of a training run."""

    model_id: str
    epochs_completed: int = 0
    best_metric: float | None = None
    metric_name: str = ""
    training_loss_history: list[float] = field(default_factory=list)
    validation_loss_history: list[float] = field(default_factory=list)
    artifact_path: str | None = None


class BaseTrainer(ABC):
    """Abstract trainer for ML models."""

    def __init__(self, config: TrainingConfig | None = None) -> None:
        self.config = config or TrainingConfig()
        logger.info("Trainer initialized: %s", self.config.experiment_name)

    @abstractmethod
    def train(
        self,
        train_data: Any,
        val_data: Any | None = None,
    ) -> TrainingResult:
        """Execute a training run.

        Args:
            train_data: Training dataset.
            val_data: Optional validation dataset.

        Returns:
            TrainingResult with metrics and artifact paths.
        """
        ...

    @abstractmethod
    def evaluate(self, test_data: Any) -> dict[str, float]:
        """Evaluate a trained model on test data.

        Args:
            test_data: Test dataset.

        Returns:
            Dictionary of metric name to metric value.
        """
        ...
