"""Base pipeline interface for all Aureon ML pipelines."""

from abc import ABC, abstractmethod
from typing import Any


class BasePipeline(ABC):
    """Abstract base class for ML pipelines.

    All pipelines must implement the `run` method which defines
    the end-to-end execution flow.
    """

    @abstractmethod
    def run(self, **kwargs: Any) -> Any:
        """Execute the pipeline.

        Args:
            **kwargs: Pipeline-specific parameters.

        Returns:
            Pipeline output (metrics, predictions, artifacts, etc.).
        """
        ...
