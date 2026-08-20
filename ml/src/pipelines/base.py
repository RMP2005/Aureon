"""Base pipeline interface for all Aureon ML pipelines."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger("aureon.ml.pipeline")


@dataclass
class PipelineResult:
    """Result container for pipeline execution.

    Attributes:
        success: Whether the pipeline completed successfully.
        output: Pipeline output data.
        metrics: Performance metrics from the run.
        errors: List of errors encountered.
        started_at: Pipeline start timestamp.
        completed_at: Pipeline completion timestamp.
    """

    success: bool = False
    output: Any = None
    metrics: dict[str, float] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @property
    def duration_seconds(self) -> float | None:
        """Pipeline execution duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class BasePipeline(ABC):
    """Abstract base class for ML pipelines.

    All pipelines must implement the `run` method which defines
    the end-to-end execution flow.
    """

    def __init__(self, name: str = "unnamed") -> None:
        self.name = name
        logger.info("Pipeline initialized: %s", name)

    @abstractmethod
    def run(self, **kwargs: Any) -> PipelineResult:
        """Execute the pipeline.

        Args:
            **kwargs: Pipeline-specific parameters.

        Returns:
            PipelineResult with output, metrics, and status.
        """
        ...

    @abstractmethod
    def validate_input(self, **kwargs: Any) -> bool:
        """Validate pipeline inputs before execution.

        Args:
            **kwargs: Pipeline-specific input data.

        Returns:
            True if inputs are valid.

        Raises:
            ValueError: If inputs are invalid.
        """
        ...
