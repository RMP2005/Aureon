"""Optimization model interface.

Defines the contract for models that optimize resource allocation,
routing, and emergency response strategies.
"""

from __future__ import annotations

import logging
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any

from src.models.base import BaseModel

logger = logging.getLogger("aureon.ml.optimizer")


@dataclass
class OptimizationConstraint:
    """A constraint for the optimization problem.

    Attributes:
        name: Constraint identifier.
        constraint_type: Type of constraint (e.g., 'max', 'min', 'eq').
        value: Constraint bound value.
        resource: Resource the constraint applies to.
    """

    name: str
    constraint_type: str  # "max", "min", "eq", "leq", "geq"
    value: float
    resource: str = ""


@dataclass
class OptimizationResult:
    """Result of an optimization run.

    Attributes:
        allocations: Optimal resource allocations.
        objective_value: Value of the objective function.
        is_feasible: Whether a feasible solution was found.
        iterations: Number of solver iterations.
        metadata: Additional solver metadata.
    """

    allocations: dict[str, Any] = field(default_factory=dict)
    objective_value: float | None = None
    is_feasible: bool = False
    iterations: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseOptimizer(BaseModel):
    """Abstract base class for optimization models.

    Subclasses implement specific optimization strategies for:
        - Emergency resource allocation
        - Response unit routing
        - Evacuation planning
        - Supply chain logistics
        - Infrastructure repair scheduling
    """

    def __init__(self, model_id: str = "optimizer", version: str = "0.1.0") -> None:
        super().__init__(model_id=model_id, name="Response Optimizer", version=version)

    @abstractmethod
    def optimize(
        self,
        objective: dict[str, Any],
        constraints: list[OptimizationConstraint],
        available_resources: dict[str, Any],
    ) -> OptimizationResult:
        """Solve the optimization problem.

        Args:
            objective: Objective function definition.
            constraints: List of constraints to satisfy.
            available_resources: Available resources for allocation.

        Returns:
            OptimizationResult with optimal allocations.
        """
        ...

    def predict(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Run inference — extracts parameters and delegates to optimize()."""
        constraints = [
            OptimizationConstraint(**c)
            for c in input_data.get("constraints", [])
        ]
        result = self.optimize(
            objective=input_data.get("objective", {}),
            constraints=constraints,
            available_resources=input_data.get("resources", {}),
        )
        return {
            "allocations": result.allocations,
            "objective_value": result.objective_value,
            "is_feasible": result.is_feasible,
        }
