"""Unit tests for the Scenario Library (Phase 10E-2)."""

import dataclasses
import unittest

from src.services.scenario_library import (
    DEFAULT_SCENARIO,
    apply_scenario,
    list_scenarios,
    scenario_display,
)


def _fresh_hospitals() -> list:
    from src.services.simulation_service import get_simulation_service

    return [dataclasses.replace(h) for h in get_simulation_service().hospitals[:3]]


def _minimal_engine_stub(traffic: bool = True):
    """Duck-typed engine stub — only what scenario modifiers touch."""

    class _Model:
        def __init__(self) -> None:
            self.override_period = None

    class _Node:
        def __init__(self, nid: str, name: str) -> None:
            self.id = nid
            self.name = name
            self.latitude = 12.97
            self.longitude = 77.59
            self.is_station = False
            self.is_hospital = False

    class _Net:
        def __init__(self) -> None:
            from collections import OrderedDict

            self.nodes = OrderedDict(
                (n.id, n)
                for n in [  # unsorted names on purpose
                    _Node("n2", "Whitefield"),
                    _Node("n1", "Indiranagar"),
                ]
            )

    class _Engine:
        def __init__(self) -> None:
            self.road_network = _Net()
            self.traffic_model = _Model() if traffic else None

    return _Engine()


class TestScenarioRegistry(unittest.TestCase):
    def test_registry_has_expected_keys(self) -> None:
        scenarios = {s["key"] for s in list_scenarios()}
        self.assertEqual(
            scenarios,
            {
                "normal_operations",
                "hospital_congestion",
                "traffic_surge",
                "mass_casualty_event",
            },
        )

    def test_registry_entries_complete(self) -> None:
        for s in list_scenarios():
            for field_name in ("name", "tagline", "description", "stress_vector"):
                self.assertTrue(
                    s[field_name], f"{s['key']}.{field_name} must be non-empty"
                )

    def test_unknown_scenario_falls_back_to_baseline_name(self) -> None:
        self.assertEqual(scenario_display("nope"), scenario_display(None))
        self.assertEqual(scenario_display(None), "Normal Operations")


class TestScenarioModifiers(unittest.TestCase):
    def test_normal_operations_is_noop(self) -> None:
        engine = _minimal_engine_stub()
        hospitals = _fresh_hospitals()
        before = [(h.occupied_er_beds, h.occupied_icu_beds) for h in hospitals]
        schedule: list = [(0.0, object())]
        apply_scenario(DEFAULT_SCENARIO, engine, schedule, hospitals)
        after = [(h.occupied_er_beds, h.occupied_icu_beds) for h in hospitals]
        self.assertEqual(before, after)
        self.assertIsNone(engine.traffic_model.override_period)
        self.assertEqual(len(schedule), 1)

    def test_hospital_congestion_preloads_beds(self) -> None:
        engine = _minimal_engine_stub()
        hospitals = _fresh_hospitals()
        apply_scenario("hospital_congestion", engine, [], hospitals)
        for h in hospitals:
            er_ratio = h.occupied_er_beds / h.total_er_beds
            self.assertGreater(er_ratio, 0.7)
            self.assertLess(h.occupied_er_beds, h.total_er_beds)

    def test_traffic_surge_pins_evening_peak(self) -> None:
        engine = _minimal_engine_stub()
        apply_scenario("traffic_surge", engine, [], [])
        override = engine.traffic_model.override_period
        self.assertIsNotNone(override)
        self.assertEqual(getattr(override, "value", override), "evening_peak")

    def test_traffic_surge_skips_gracefully_without_model(self) -> None:
        engine = _minimal_engine_stub(traffic=False)
        apply_scenario("traffic_surge", engine, [], [])  # must not raise

    def test_mass_casualty_injects_clustered_schedule(self) -> None:
        from simulation.src.generators.incident_generator import Incident

        engine = _minimal_engine_stub()
        schedule: list[tuple[float, Incident]] = [(60.0, _dummy_incident())]
        apply_scenario("mass_casualty_event", engine, schedule, [])
        injected = [inc for _, inc in schedule if inc.id.startswith("mce_")]
        self.assertEqual(len(injected), 6)
        # All at one site.
        sites = {inc.location_node_id for inc in injected}
        self.assertEqual(len(sites), 1)
        # Sorted into place inside a tight window.
        mce_times = [t for t, inc in schedule if inc.id.startswith("mce_")]
        self.assertEqual(mce_times, sorted(mce_times))
        self.assertLessEqual(max(mce_times) - min(mce_times), 150.0)
        self.assertEqual(len(schedule), 7)
        severities = {
            getattr(inc.severity, "value", str(inc.severity)) for inc in injected
        }
        self.assertIn("critical", severities)


def _dummy_incident():
    from simulation.src.generators.incident_generator import (
        Incident,
        IncidentCategory,
        IncidentSeverity,
    )
    from simulation.src.models.ambulance import AmbulanceCapability

    return Incident(
        id="inc_0001",
        category=IncidentCategory.GENERAL_MEDICAL,
        severity=IncidentSeverity.LOW,
        required_capability=AmbulanceCapability.BLS,
        location_node_id="n1",
        location_name="Indiranagar",
        latitude=12.97,
        longitude=77.59,
        reported_at_tick=60,
        reported_at_sim_time_sec=60.0,
    )


class TestServiceIntegration(unittest.TestCase):
    """Scenario flows through service creation into persisted params."""

    def test_scenario_recorded_in_params_and_result(self) -> None:
        from src.services.simulation_service import get_simulation_service

        res = get_simulation_service().run_simulation(
            strategy_name="aureon",
            duration_minutes=8.0,
            incident_rate_per_hour=6.0,
            seed=7,
            scenario="hospital_congestion",
        )
        self.assertEqual(res["parameters"]["scenario"], "hospital_congestion")
        self.assertEqual(res["scenario"]["name"], "Hospital Congestion")

    def test_default_scenario_is_normal(self) -> None:
        from src.services.simulation_service import get_simulation_service

        res = get_simulation_service().run_simulation(
            strategy_name="aureon",
            duration_minutes=6.0,
            incident_rate_per_hour=4.0,
            seed=3,
        )
        self.assertEqual(res["parameters"]["scenario"], DEFAULT_SCENARIO)


if __name__ == "__main__":
    unittest.main()
