"""Tests for ML model interfaces."""

from typing import Any

import pytest

from src.models.base import BaseModel, ModelMetadata
from src.models.classifier import BaseClassifier, ClassificationResult
from src.models.optimizer import (
    BaseOptimizer,
    OptimizationConstraint,
    OptimizationResult,
)
from src.models.predictor import BasePredictor, PredictionResult
from src.pipelines.base import BasePipeline, PipelineResult
from src.inference.server import ModelRegistry


# --- Concrete test implementations ---

class MockClassifier(BaseClassifier):
    def load(self, path: str | None = None) -> None:
        self._is_loaded = True

    def classify(self, features: dict[str, Any]) -> ClassificationResult:
        return ClassificationResult(
            event_type="fire",
            confidence=0.95,
            probabilities={"fire": 0.95, "hazmat": 0.05},
        )


class MockPredictor(BasePredictor):
    def load(self, path: str | None = None) -> None:
        self._is_loaded = True

    def forecast(
        self, historical_data: dict[str, Any], horizon_steps: int = 10
    ) -> PredictionResult:
        return PredictionResult(
            predictions=[1.0] * horizon_steps,
            horizon=f"{horizon_steps} steps",
        )

    def detect_anomalies(
        self, data: dict[str, Any], threshold: float = 0.95
    ) -> list[dict[str, Any]]:
        return []


class MockOptimizer(BaseOptimizer):
    def load(self, path: str | None = None) -> None:
        self._is_loaded = True

    def optimize(
        self,
        objective: dict[str, Any],
        constraints: list[OptimizationConstraint],
        available_resources: dict[str, Any],
    ) -> OptimizationResult:
        return OptimizationResult(
            allocations={"ambulances": 5},
            objective_value=0.85,
            is_feasible=True,
            iterations=42,
        )


class MockPipeline(BasePipeline):
    def run(self, **kwargs: Any) -> PipelineResult:
        return PipelineResult(success=True, output="done")

    def validate_input(self, **kwargs: Any) -> bool:
        return True


# --- Tests ---

def test_classifier_interface() -> None:
    clf = MockClassifier()
    assert not clf.is_loaded
    clf.load()
    assert clf.is_loaded
    result = clf.classify({"sensor": 1.0})
    assert result.event_type == "fire"
    assert result.confidence == 0.95


def test_classifier_predict() -> None:
    clf = MockClassifier()
    clf.load()
    output = clf.predict({"sensor": 1.0})
    assert output["event_type"] == "fire"


def test_predictor_interface() -> None:
    pred = MockPredictor()
    pred.load()
    result = pred.forecast({"history": []}, horizon_steps=5)
    assert len(result.predictions) == 5


def test_predictor_anomaly_detection() -> None:
    pred = MockPredictor()
    pred.load()
    anomalies = pred.detect_anomalies({"values": []})
    assert isinstance(anomalies, list)


def test_optimizer_interface() -> None:
    opt = MockOptimizer()
    opt.load()
    constraints = [
        OptimizationConstraint(name="max_units", constraint_type="leq", value=10.0)
    ]
    result = opt.optimize({}, constraints, {"ambulances": 10})
    assert result.is_feasible
    assert result.iterations == 42


def test_model_metadata() -> None:
    clf = MockClassifier()
    meta = clf.metadata
    assert meta.model_id == "event-classifier"
    assert meta.name == "Event Classifier"
    assert not meta.is_loaded


def test_pipeline_interface() -> None:
    pipe = MockPipeline(name="test-pipe")
    assert pipe.validate_input()
    result = pipe.run()
    assert result.success


def test_model_registry() -> None:
    registry = ModelRegistry()
    clf = MockClassifier()
    registry.register(clf)
    assert len(registry.list_models()) == 1
    assert registry.get("event-classifier") is clf


def test_model_registry_predict() -> None:
    registry = ModelRegistry()
    clf = MockClassifier()
    clf.load()
    registry.register(clf)
    result = registry.predict("event-classifier", {"sensor": 1.0})
    assert result["event_type"] == "fire"


def test_model_registry_predict_not_loaded() -> None:
    registry = ModelRegistry()
    clf = MockClassifier()  # not loaded
    registry.register(clf)
    with pytest.raises(RuntimeError):
        registry.predict("event-classifier", {})
