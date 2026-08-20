"""Tests for ML model interfaces."""

import unittest
from typing import Any

from src.inference.server import ModelRegistry
from src.models.base import BaseModel, ModelMetadata
from src.models.classifier import BaseClassifier, ClassificationResult
from src.models.optimizer import (
    BaseOptimizer,
    OptimizationConstraint,
    OptimizationResult,
)
from src.models.predictor import BasePredictor, PredictionResult
from src.pipelines.base import BasePipeline, PipelineResult


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


class TestMLInterfaces(unittest.TestCase):
    def test_classifier_interface(self) -> None:
        clf = MockClassifier()
        self.assertFalse(clf.is_loaded)
        clf.load()
        self.assertTrue(clf.is_loaded)
        result = clf.classify({"sensor": 1.0})
        self.assertEqual(result.event_type, "fire")
        self.assertEqual(result.confidence, 0.95)

    def test_classifier_predict(self) -> None:
        clf = MockClassifier()
        clf.load()
        output = clf.predict({"sensor": 1.0})
        self.assertEqual(output["event_type"], "fire")

    def test_predictor_interface(self) -> None:
        pred = MockPredictor()
        pred.load()
        result = pred.forecast({"history": []}, horizon_steps=5)
        self.assertEqual(len(result.predictions), 5)

    def test_predictor_anomaly_detection(self) -> None:
        pred = MockPredictor()
        pred.load()
        anomalies = pred.detect_anomalies({"values": []})
        self.assertIsInstance(anomalies, list)

    def test_optimizer_interface(self) -> None:
        opt = MockOptimizer()
        opt.load()
        constraints = [
            OptimizationConstraint(name="max_units", constraint_type="leq", value=10.0)
        ]
        result = opt.optimize({}, constraints, {"ambulances": 10})
        self.assertTrue(result.is_feasible)
        self.assertEqual(result.iterations, 42)

    def test_model_metadata(self) -> None:
        clf = MockClassifier()
        meta = clf.metadata
        self.assertEqual(meta.model_id, "event-classifier")
        self.assertEqual(meta.name, "Event Classifier")
        self.assertFalse(meta.is_loaded)

    def test_pipeline_interface(self) -> None:
        pipe = MockPipeline(name="test-pipe")
        self.assertTrue(pipe.validate_input())
        result = pipe.run()
        self.assertTrue(result.success)

    def test_model_registry(self) -> None:
        reg = ModelRegistry()
        clf = MockClassifier()
        reg.register(clf)
        self.assertEqual(len(reg.list_models()), 1)
        self.assertIs(reg.get("event-classifier"), clf)

    def test_model_registry_predict(self) -> None:
        reg = ModelRegistry()
        clf = MockClassifier()
        clf.load()
        reg.register(clf)
        result = reg.predict("event-classifier", {"sensor": 1.0})
        self.assertEqual(result["event_type"], "fire")

    def test_model_registry_predict_not_loaded(self) -> None:
        reg = ModelRegistry()
        clf = MockClassifier()
        reg.register(clf)
        with self.assertRaises(RuntimeError):
            reg.predict("event-classifier", {})


if __name__ == "__main__":
    unittest.main()
