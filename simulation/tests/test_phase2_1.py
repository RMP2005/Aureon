"""Tests for Phase 2.1 correctness fixes: hospital lifecycle, reset, priority queue, fallback."""

from __future__ import annotations

import pytest

from simulation.src.dispatch.aureon_intelligence import AureonDecisionEngine
from simulation.src.dispatch.baseline import NearestAvailableStrategy
from simulation.src.engine.city_engine import CitySimulationEngine
from simulation.src.evaluation.evaluator import SimulationEvaluator
from simulation.src.generators.incident_generator import (
    Incident,
    IncidentCategory,
    IncidentSeverity,
    ScenarioGenerator,
)
from simulation.src.models.ambulance import (
    AmbulanceCapability,
    create_default_bangalore_fleet,
)
from simulation.src.models.hospital import Hospital, get_default_bangalore_hospitals
from simulation.src.network.bangalore_map import build_bangalore_network
from simulation.src.network.road_graph import RoadNetwork, RoadNode
from simulation.src.scenarios.default import create_default_city


# ---------------------------------------------------------------------------
# Hospital Patient Lifecycle
# ---------------------------------------------------------------------------

class TestHospitalLifecycle:
    def test_admit_increases_beds(self) -> None:
        hosp = Hospital(
            id="h1", name="Test", node_id="n1", latitude=12.97, longitude=77.60,
            total_er_beds=10, occupied_er_beds=2, total_icu_beds=5, occupied_icu_beds=1,
        )
        assert hosp.admit_patient("inc_001", "er", 0.0) is True
        assert hosp.occupied_er_beds == 3
        assert hosp.active_patient_count == 1

    def test_admit_icu_bed(self) -> None:
        hosp = Hospital(
            id="h1", name="Test", node_id="n1", latitude=12.97, longitude=77.60,
            total_er_beds=10, occupied_er_beds=2, total_icu_beds=5, occupied_icu_beds=1,
        )
        assert hosp.admit_patient("inc_001", "icu", 0.0) is True
        assert hosp.occupied_icu_beds == 2

    def test_er_overflow_rejected(self) -> None:
        hosp = Hospital(
            id="h1", name="Test", node_id="n1", latitude=12.97, longitude=77.60,
            total_er_beds=10, occupied_er_beds=10, total_icu_beds=5, occupied_icu_beds=1,
        )
        assert hosp.admit_patient("inc_001", "er", 0.0) is False
        assert hosp.occupied_er_beds == 10

    def test_icu_overflow_rejected(self) -> None:
        hosp = Hospital(
            id="h1", name="Test", node_id="n1", latitude=12.97, longitude=77.60,
            total_er_beds=10, occupied_er_beds=2, total_icu_beds=5, occupied_icu_beds=5,
        )
        assert hosp.admit_patient("inc_001", "icu", 0.0) is False

    def test_discharge_releases_beds(self) -> None:
        hosp = Hospital(
            id="h1", name="Test", node_id="n1", latitude=12.97, longitude=77.60,
            total_er_beds=10, occupied_er_beds=2, total_icu_beds=5, occupied_icu_beds=1,
            avg_stay_duration_seconds=100.0,
        )
        hosp.admit_patient("inc_001", "er", 0.0)
        hosp.admit_patient("inc_002", "icu", 0.0)
        assert hosp.active_patient_count == 2

        # Before stay completes — no discharge
        discharged = hosp.process_discharges(50.0)
        assert discharged == 0
        assert hosp.active_patient_count == 2

        # After stay completes
        discharged = hosp.process_discharges(150.0)
        assert discharged == 2
        assert hosp.occupied_er_beds == 2  # original
        assert hosp.occupied_icu_beds == 1  # original
        assert hosp.active_patient_count == 0

    def test_partial_discharge(self) -> None:
        hosp = Hospital(
            id="h1", name="Test", node_id="n1", latitude=12.97, longitude=77.60,
            total_er_beds=10, occupied_er_beds=0, total_icu_beds=5, occupied_icu_beds=0,
        )
        hosp.admit_patient("short", "er", 0.0, stay_duration_sec=60.0)
        hosp.admit_patient("long", "er", 0.0, stay_duration_sec=300.0)

        discharged = hosp.process_discharges(100.0)
        assert discharged == 1
        assert hosp.active_patient_count == 1
        assert hosp.occupied_er_beds == 1  # long-stay patient still here


# ---------------------------------------------------------------------------
# Simulation Reset
# ---------------------------------------------------------------------------

class TestSimulationReset:
    def test_reset_preserves_hospital_state(self) -> None:
        hospitals = get_default_bangalore_hospitals()
        original = [(h.occupied_er_beds, h.occupied_icu_beds) for h in hospitals]
        engine = CitySimulationEngine(
            hospitals=hospitals, ambulances=create_default_bangalore_fleet(),
        )

        net = build_bangalore_network()
        nodes = [(n.id, n.name, n.latitude, n.longitude)
                 for n in net.nodes.values() if not n.is_station and not n.is_hospital]
        gen = ScenarioGenerator(node_ids_with_coords=nodes, seed=42)
        schedule = gen.generate_scenario_schedule(duration_minutes=10, incident_rate_per_hour=14)
        engine.run_scenario(schedule=schedule, duration_minutes=10)

        engine.reset()
        after = [(h.occupied_er_beds, h.occupied_icu_beds) for h in engine.hospitals]
        assert after == original

    def test_reset_clears_incidents(self) -> None:
        engine = CitySimulationEngine(ambulances=create_default_bangalore_fleet())
        net = build_bangalore_network()
        nodes = [(n.id, n.name, n.latitude, n.longitude)
                 for n in net.nodes.values() if not n.is_station and not n.is_hospital]
        gen = ScenarioGenerator(node_ids_with_coords=nodes, seed=42)
        schedule = gen.generate_scenario_schedule(duration_minutes=5, incident_rate_per_hour=20)
        engine.run_scenario(schedule=schedule, duration_minutes=5)

        engine.reset()
        assert len(engine.active_incidents) == 0
        assert len(engine.completed_incidents) == 0
        assert len(engine.pending_queue) == 0
        assert len(engine.dispatch_log) == 0


# ---------------------------------------------------------------------------
# Priority Queue
# ---------------------------------------------------------------------------

class TestPriorityQueue:
    def _make_incident(self, id: str, severity: IncidentSeverity, cap: AmbulanceCapability) -> Incident:
        return Incident(
            id=id, category=IncidentCategory.CARDIAC_ARREST, severity=severity,
            required_capability=cap, location_node_id="node_mg_road", location_name="MG Road",
            latitude=12.97, longitude=77.60, reported_at_tick=0, reported_at_sim_time_sec=0.0,
        )

    def test_severity_ordering(self) -> None:
        engine = CitySimulationEngine(ambulances=create_default_bangalore_fleet())
        engine.pending_queue = [
            self._make_incident("low", IncidentSeverity.LOW, AmbulanceCapability.BLS),
            self._make_incident("critical", IncidentSeverity.CRITICAL, AmbulanceCapability.ALS),
            self._make_incident("moderate", IncidentSeverity.MODERATE, AmbulanceCapability.BLS),
        ]
        engine._sort_pending_by_priority()
        assert [i.id for i in engine.pending_queue] == ["critical", "moderate", "low"]

    def test_critical_before_high(self) -> None:
        engine = CitySimulationEngine(ambulances=create_default_bangalore_fleet())
        engine.pending_queue = [
            self._make_incident("high", IncidentSeverity.HIGH, AmbulanceCapability.ALS),
            self._make_incident("critical", IncidentSeverity.CRITICAL, AmbulanceCapability.ALS),
        ]
        engine._sort_pending_by_priority()
        assert engine.pending_queue[0].id == "critical"

    def test_same_severity_als_first(self) -> None:
        engine = CitySimulationEngine(ambulances=create_default_bangalore_fleet())
        engine.pending_queue = [
            self._make_incident("bls", IncidentSeverity.HIGH, AmbulanceCapability.BLS),
            self._make_incident("als", IncidentSeverity.HIGH, AmbulanceCapability.ALS),
        ]
        engine._sort_pending_by_priority()
        assert engine.pending_queue[0].id == "als"


# ---------------------------------------------------------------------------
# No-Route Fallback
# ---------------------------------------------------------------------------

class TestNoRouteFallback:
    def _disjoint_network(self) -> RoadNetwork:
        net = RoadNetwork()
        net.add_node(RoadNode("a", "A", 12.97, 77.60))
        net.add_node(RoadNode("b", "B", 12.98, 77.61))
        return net

    def test_baseline_returns_none(self) -> None:
        net = self._disjoint_network()
        amb = create_default_bangalore_fleet()
        hosp = get_default_bangalore_hospitals()
        inc = Incident(
            id="test", category=IncidentCategory.CARDIAC_ARREST, severity=IncidentSeverity.CRITICAL,
            required_capability=AmbulanceCapability.ALS, location_node_id="nonexistent",
            location_name="X", latitude=12.97, longitude=77.60, reported_at_tick=0,
            reported_at_sim_time_sec=0.0,
        )
        decision = NearestAvailableStrategy().dispatch(inc, amb[:1], hosp[:1], net)
        assert decision.ambulance_id is None

    def test_aureon_returns_none(self) -> None:
        net = self._disjoint_network()
        amb = create_default_bangalore_fleet()
        hosp = get_default_bangalore_hospitals()
        inc = Incident(
            id="test", category=IncidentCategory.CARDIAC_ARREST, severity=IncidentSeverity.CRITICAL,
            required_capability=AmbulanceCapability.ALS, location_node_id="nonexistent",
            location_name="X", latitude=12.97, longitude=77.60, reported_at_tick=0,
            reported_at_sim_time_sec=0.0,
        )
        decision = AureonDecisionEngine().dispatch(inc, amb[:1], hosp[:1], net)
        assert decision.ambulance_id is None


# ---------------------------------------------------------------------------
# Bangalore Defaults
# ---------------------------------------------------------------------------

class TestBangaloreDefaults:
    def test_city_is_bangalore(self) -> None:
        city = create_default_city()
        assert city.name == "Bangalore"

    def test_zones_in_bangalore_range(self) -> None:
        city = create_default_city()
        for z in city.zones:
            assert 12.0 < z.center.latitude < 14.0
            assert 77.0 < z.center.longitude < 78.0

    def test_zone_names(self) -> None:
        city = create_default_city()
        names = {z.name for z in city.zones}
        expected = {"Indiranagar", "Koramangala", "Whitefield", "Electronic City", "Hebbal", "Yeshwanthpur"}
        assert names == expected


# ---------------------------------------------------------------------------
# Benchmark Integration
# ---------------------------------------------------------------------------

class TestBenchmark:
    def test_benchmark_runs(self) -> None:
        report = SimulationEvaluator.run_benchmark(
            duration_minutes=30, incident_rate_per_hour=14, seed=42,
        )
        d = report.to_dict()
        assert d["baseline"]["total_incidents_reported"] > 0
        assert d["aureon_intelligence"]["total_incidents_reported"] > 0

    def test_response_times_positive(self) -> None:
        report = SimulationEvaluator.run_benchmark(
            duration_minutes=30, incident_rate_per_hour=14, seed=42,
        )
        d = report.to_dict()
        assert d["baseline"]["response_times_minutes"]["mean"] > 0
        assert d["aureon_intelligence"]["response_times_minutes"]["mean"] > 0
