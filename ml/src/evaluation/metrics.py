"""Evaluation metrics for ML models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ClassificationMetrics:
    """Metrics for classification models."""

    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    confusion_matrix: list[list[int]] = field(default_factory=list)
    per_class_metrics: dict[str, dict[str, float]] = field(default_factory=dict)


@dataclass
class RegressionMetrics:
    """Metrics for regression/prediction models."""

    mae: float = 0.0
    mse: float = 0.0
    rmse: float = 0.0
    r2_score: float = 0.0
    mape: float = 0.0


@dataclass
class OptimizationMetrics:
    """Metrics for optimization models."""

    objective_value: float = 0.0
    constraint_violations: int = 0
    solution_quality: float = 0.0
    solve_time_seconds: float = 0.0
    gap_percent: float = 0.0
