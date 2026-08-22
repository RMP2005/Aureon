"""Unit tests for backend SimulationService integration."""

import unittest

from src.services.simulation_service import SimulationService


class TestSimulationService(unittest.TestCase):
    def setUp(self) -> None:
        self.svc = SimulationService.__new__(SimulationService)
        self.svc.road_network = SimulationService.__init__.__code__.co_consts  # not used here
        # Use the real singleton for integration tests
        from src.services.simulation_service import simulation_service
        self.svc = simulation_service

    def test_get_city_state(self) -> None:
        state = self.svc.get_city_state()
        self.assertIn("ambulances", state)
        self.assertIn("hospitals", state)
        self.assertGreater(len(state["ambulances"]), 0)
        self.assertGreater(len(state["hospitals"]), 0)

    def test_run_simulation_aureon(self) -> None:
        res = self.svc.run_simulation(
            strategy_name="aureon",
            duration_minutes=30.0,
            incident_rate_per_hour=10.0,
            seed=42,
        )
        self.assertIn("run_id", res)
        self.assertIn("metrics", res)
        metrics = res["metrics"]
        self.assertGreater(metrics["total_incidents_reported"], 0)
        self.assertGreater(metrics["total_incidents_dispatched"], 0)
        # "aureon" should now map to HybridAureonStrategy
        self.assertIn("Hybrid", res["strategy"])

    def test_run_comparison_benchmark(self) -> None:
        cmp_report = self.svc.run_comparison(
            duration_minutes=45.0,
            incident_rate_per_hour=12.0,
            seed=42,
        )
        self.assertIn("comparison_id", cmp_report)
        self.assertIn("baseline", cmp_report)
        self.assertIn("aureon_intelligence", cmp_report)
        self.assertIn("improvements", cmp_report)

        # Check improvements structure
        impr = cmp_report["improvements"]
        self.assertIn("overall_response_time_improvement_percent", impr)
        self.assertIn("critical_case_response_time_improvement_percent", impr)
        self.assertIn("clinical_capability_matching_gain_percent", impr)


class TestStrategyRouting(unittest.TestCase):
    """Verify that strategy name mapping works correctly."""

    def _make_svc(self) -> SimulationService:
        from src.services.simulation_service import simulation_service
        return simulation_service

    def test_aureon_maps_to_hybrid(self) -> None:
        svc = self._make_svc()
        res = svc.run_simulation(strategy_name="aureon", duration_minutes=10.0, seed=1)
        self.assertIn("Hybrid", res["strategy"])

    def test_hybrid_maps_to_hybrid(self) -> None:
        svc = self._make_svc()
        res = svc.run_simulation(strategy_name="hybrid", duration_minutes=10.0, seed=1)
        self.assertIn("Hybrid", res["strategy"])

    def test_baseline_maps_to_nearest(self) -> None:
        svc = self._make_svc()
        res = svc.run_simulation(strategy_name="baseline", duration_minutes=10.0, seed=1)
        self.assertIn("Nearest", res["strategy"])

    def test_adaptive_maps_to_adaptive(self) -> None:
        svc = self._make_svc()
        res = svc.run_simulation(strategy_name="adaptive", duration_minutes=10.0, seed=1)
        self.assertIn("Adaptive", res["strategy"])

    def test_unknown_strategy_defaults_to_hybrid(self) -> None:
        svc = self._make_svc()
        res = svc.run_simulation(strategy_name="nonexistent", duration_minutes=10.0, seed=1)
        self.assertIn("Hybrid", res["strategy"])


if __name__ == "__main__":
    unittest.main()
