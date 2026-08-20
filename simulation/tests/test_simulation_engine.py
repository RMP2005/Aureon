"""Tests for the City Digital Twin Simulation Engine and Evaluation system."""

import unittest

try:
    from simulation.src.dispatch.aureon_intelligence import AureonDecisionEngine
    from simulation.src.engine.city_engine import CitySimulationEngine
    from simulation.src.evaluation.evaluator import SimulationEvaluator
    from simulation.src.generators.incident_generator import ScenarioGenerator
    from simulation.src.models.ambulance import create_default_bangalore_fleet
    from simulation.src.models.hospital import get_default_bangalore_hospitals
    from simulation.src.network.bangalore_map import build_bangalore_network
except ImportError:
    from src.dispatch.aureon_intelligence import AureonDecisionEngine  # type: ignore
    from src.engine.city_engine import CitySimulationEngine  # type: ignore
    from src.evaluation.evaluator import SimulationEvaluator  # type: ignore
    from src.generators.incident_generator import ScenarioGenerator  # type: ignore
    from src.models.ambulance import create_default_bangalore_fleet  # type: ignore
    from src.models.hospital import get_default_bangalore_hospitals  # type: ignore
    from src.network.bangalore_map import build_bangalore_network  # type: ignore


class TestSimulationEngine(unittest.TestCase):
    def test_full_simulation_run(self) -> None:
        net = build_bangalore_network()
        hospitals = get_default_bangalore_hospitals()
        fleet = create_default_bangalore_fleet()

        engine = CitySimulationEngine(
            road_network=net,
            hospitals=hospitals,
            ambulances=fleet,
            strategy=AureonDecisionEngine(),
            dt_seconds=10.0,
        )

        candidate_nodes = [
            (n.id, n.name, n.latitude, n.longitude)
            for n in net.nodes.values()
            if not n.is_station and not n.is_hospital
        ]
        gen = ScenarioGenerator(node_ids_with_coords=candidate_nodes, seed=42)
        schedule = gen.generate_scenario_schedule(duration_minutes=45.0, incident_rate_per_hour=10.0)

        metrics = engine.run_scenario(schedule=schedule, duration_minutes=45.0)

        self.assertGreater(metrics.total_incidents_reported, 0)
        self.assertGreater(metrics.total_incidents_dispatched, 0)
        self.assertGreater(metrics.mean_response_time_sec, 0.0)
        self.assertGreater(metrics.total_fleet_distance_km, 0.0)

        state = engine.get_current_state()
        self.assertEqual(len(state["ambulances"]), len(fleet))
        self.assertEqual(len(state["hospitals"]), len(hospitals))

    def test_evaluator_side_by_side_benchmark(self) -> None:
        report = SimulationEvaluator.run_benchmark(
            duration_minutes=60.0,
            incident_rate_per_hour=12.0,
            seed=100,
        )

        self.assertGreater(report.incident_count, 0)
        self.assertGreater(report.baseline_metrics.mean_response_time_sec, 0.0)
        self.assertGreater(report.aureon_metrics.mean_response_time_sec, 0.0)

        # Aureon should achieve superior or equal capability matching over baseline
        self.assertGreaterEqual(
            report.aureon_metrics.capability_match_rate,
            report.baseline_metrics.capability_match_rate,
        )

        rep_dict = report.to_dict()
        self.assertIn("improvements", rep_dict)
        self.assertIn("baseline", rep_dict)
        self.assertIn("aureon_intelligence", rep_dict)


if __name__ == "__main__":
    unittest.main()
