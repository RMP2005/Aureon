"""Tests for Baseline vs Aureon dispatch strategies."""

import unittest

try:
    from simulation.src.dispatch.aureon_intelligence import AureonDecisionEngine
    from simulation.src.dispatch.baseline import NearestAvailableStrategy
    from simulation.src.generators.incident_generator import (
        Incident,
        IncidentCategory,
        IncidentSeverity,
    )
    from simulation.src.models.ambulance import Ambulance, AmbulanceCapability
    from simulation.src.models.hospital import get_default_bangalore_hospitals
    from simulation.src.network.bangalore_map import build_bangalore_network
except ImportError:
    from src.dispatch.aureon_intelligence import AureonDecisionEngine  # type: ignore
    from src.dispatch.baseline import NearestAvailableStrategy  # type: ignore
    from src.generators.incident_generator import (  # type: ignore
        Incident,
        IncidentCategory,
        IncidentSeverity,
    )
    from src.models.ambulance import Ambulance, AmbulanceCapability  # type: ignore
    from src.models.hospital import get_default_bangalore_hospitals  # type: ignore
    from src.network.bangalore_map import build_bangalore_network  # type: ignore


class TestDispatch(unittest.TestCase):
    def test_baseline_nearest_dispatch(self) -> None:
        net = build_bangalore_network()
        hospitals = get_default_bangalore_hospitals()

        amb_close = Ambulance("a1", "BLS-CBD", AmbulanceCapability.BLS, "station_central_cbd", "station_central_cbd", 12.973, 77.608)
        amb_far = Ambulance("a2", "ALS-ECITY", AmbulanceCapability.ALS, "station_ecity", "station_ecity", 12.842, 77.675)

        incident = Incident(
            id="inc_test",
            category=IncidentCategory.CARDIAC_ARREST,
            severity=IncidentSeverity.CRITICAL,
            required_capability=AmbulanceCapability.ALS,
            location_node_id="node_indiranagar",
            location_name="Indiranagar",
            latitude=12.9719,
            longitude=77.6412,
            reported_at_tick=1,
            reported_at_sim_time_sec=10.0,
        )

        baseline = NearestAvailableStrategy()
        decision = baseline.dispatch(
            incident=incident,
            available_ambulances=[amb_close, amb_far],
            hospitals=hospitals,
            road_network=net,
        )

        self.assertEqual(decision.ambulance_id, "a1")

    def test_aureon_intelligence_clinical_triage(self) -> None:
        net = build_bangalore_network()
        hospitals = get_default_bangalore_hospitals()

        amb_bls = Ambulance("a_bls", "BLS-CBD", AmbulanceCapability.BLS, "station_central_cbd", "station_central_cbd", 12.973, 77.608)
        amb_als = Ambulance("a_als", "ALS-IND", AmbulanceCapability.ALS, "station_indiranagar", "station_indiranagar", 12.970, 77.639)

        cardiac_incident = Incident(
            id="inc_cardiac",
            category=IncidentCategory.CARDIAC_ARREST,
            severity=IncidentSeverity.CRITICAL,
            required_capability=AmbulanceCapability.ALS,
            location_node_id="node_indiranagar",
            location_name="Indiranagar",
            latitude=12.9719,
            longitude=77.6412,
            reported_at_tick=1,
            reported_at_sim_time_sec=10.0,
        )

        aureon = AureonDecisionEngine()
        decision = aureon.dispatch(
            incident=cardiac_incident,
            available_ambulances=[amb_bls, amb_als],
            hospitals=hospitals,
            road_network=net,
        )

        self.assertEqual(decision.ambulance_id, "a_als")
        self.assertIsNotNone(decision.target_hospital_id)


if __name__ == "__main__":
    unittest.main()
