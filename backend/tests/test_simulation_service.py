"""Unit tests for backend SimulationService integration."""

import unittest

from src.services.simulation_service import simulation_service


class TestSimulationService(unittest.TestCase):
    def test_get_city_state(self) -> None:
        state = simulation_service.get_city_state()
        self.assertIn("ambulances", state)
        self.assertIn("hospitals", state)
        self.assertGreater(len(state["ambulances"]), 0)
        self.assertGreater(len(state["hospitals"]), 0)

    def test_run_simulation_aureon(self) -> None:
        res = simulation_service.run_simulation(
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

    def test_run_comparison_benchmark(self) -> None:
        cmp_report = simulation_service.run_comparison(
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


if __name__ == "__main__":
    unittest.main()
