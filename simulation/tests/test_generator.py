"""Tests for incident generator and scenario schedules."""

import unittest

try:
    from simulation.src.generators.incident_generator import (
        INCIDENT_PROFILES,
        IncidentCategory,
        IncidentSeverity,
        ScenarioGenerator,
    )
    from simulation.src.models.ambulance import AmbulanceCapability
except ImportError:
    from src.generators.incident_generator import (  # type: ignore
        INCIDENT_PROFILES,
        IncidentCategory,
        IncidentSeverity,
        ScenarioGenerator,
    )
    from src.models.ambulance import AmbulanceCapability  # type: ignore


class TestGenerator(unittest.TestCase):
    def test_incident_profiles_validity(self) -> None:
        for cat, profile in INCIDENT_PROFILES.items():
            self.assertEqual(profile.category, cat)
            self.assertGreater(profile.target_response_time_sec, 0)
            self.assertGreater(profile.base_on_scene_time_sec, 0)

        cardiac = INCIDENT_PROFILES[IncidentCategory.CARDIAC_ARREST]
        self.assertEqual(cardiac.required_capability, AmbulanceCapability.ALS)
        self.assertEqual(cardiac.severity, IncidentSeverity.CRITICAL)

        minor = INCIDENT_PROFILES[IncidentCategory.MINOR_INJURY]
        self.assertEqual(minor.required_capability, AmbulanceCapability.BLS)
        self.assertEqual(minor.severity, IncidentSeverity.LOW)

    def test_scenario_generator_deterministic_seeding(self) -> None:
        nodes = [
            ("node_1", "Node 1", 12.97, 77.59),
            ("node_2", "Node 2", 12.93, 77.62),
            ("node_3", "Node 3", 12.98, 77.73),
        ]

        gen1 = ScenarioGenerator(node_ids_with_coords=nodes, seed=123)
        sched1 = gen1.generate_scenario_schedule(duration_minutes=30.0, incident_rate_per_hour=10.0)

        gen2 = ScenarioGenerator(node_ids_with_coords=nodes, seed=123)
        sched2 = gen2.generate_scenario_schedule(duration_minutes=30.0, incident_rate_per_hour=10.0)

        self.assertEqual(len(sched1), len(sched2))
        self.assertGreater(len(sched1), 0)
        for (t1, inc1), (t2, inc2) in zip(sched1, sched2):
            self.assertAlmostEqual(t1, t2, places=4)
            self.assertEqual(inc1.id, inc2.id)
            self.assertEqual(inc1.category, inc2.category)
            self.assertEqual(inc1.location_node_id, inc2.location_node_id)


if __name__ == "__main__":
    unittest.main()
