"""Phase 6 tests — Hybrid Aureon Intelligence."""

import copy
import math
import unittest

try:
    from simulation.src.dispatch.hybrid_intelligence import (
        HybridAureonStrategy,
        HybridDispatchConfig,
    )
    from simulation.src.dispatch.coverage import FleetCoverageAnalyzer
    from simulation.src.dispatch.outcome_score import EmergencyOutcomeScore, OutcomeComponents
    from simulation.src.dispatch.aureon_intelligence import AureonDecisionEngine
    from simulation.src.dispatch.baseline import NearestAvailableStrategy
    from simulation.src.engine.city_engine import CitySimulationEngine
    from simulation.src.generators.incident_generator import (
        Incident,
        IncidentCategory,
        IncidentSeverity,
        ScenarioGenerator,
        INCIDENT_PROFILES,
    )
    from simulation.src.models.ambulance import (
        Ambulance,
        AmbulanceCapability,
        create_default_bangalore_fleet,
    )
    from simulation.src.models.hospital import (
        Hospital,
        HospitalSpecialty,
        get_default_bangalore_hospitals,
    )
    from simulation.src.network.bangalore_map import build_bangalore_network
    from simulation.src.network.road_graph import RoadNetwork, RoadNode, RoadEdge, RoadType
except ImportError:
    from src.dispatch.hybrid_intelligence import HybridAureonStrategy, HybridDispatchConfig  # type: ignore
    from src.dispatch.coverage import FleetCoverageAnalyzer  # type: ignore
    from src.dispatch.outcome_score import EmergencyOutcomeScore, OutcomeComponents  # type: ignore
    from src.dispatch.aureon_intelligence import AureonDecisionEngine  # type: ignore
    from src.dispatch.baseline import NearestAvailableStrategy  # type: ignore
    from src.engine.city_engine import CitySimulationEngine  # type: ignore
    from src.generators.incident_generator import (  # type: ignore
        Incident, IncidentCategory, IncidentSeverity, ScenarioGenerator, INCIDENT_PROFILES,
    )
    from src.models.ambulance import Ambulance, AmbulanceCapability, create_default_bangalore_fleet  # type: ignore
    from src.models.hospital import Hospital, HospitalSpecialty, get_default_bangalore_hospitals  # type: ignore
    from src.network.bangalore_map import build_bangalore_network  # type: ignore
    from src.network.road_graph import RoadNetwork, RoadNode, RoadEdge, RoadType  # type: ignore


def _build_test_network():
    net = RoadNetwork("Test Network")
    node_ids = ["A", "B", "C", "D", "E"]
    coords = [
        (12.970, 77.600), (12.971, 77.610), (12.972, 77.620),
        (12.973, 77.630), (12.974, 77.640),
    ]
    for nid, (lat, lon) in zip(node_ids, coords):
        net.add_node(RoadNode(id=nid, name=nid, latitude=lat, longitude=lon))
    for i in range(len(node_ids) - 1):
        net.add_edge(RoadEdge(
            id=f"e_{node_ids[i]}_{node_ids[i+1]}",
            source_id=node_ids[i], target_id=node_ids[i+1],
            length_km=1.0, road_type=RoadType.PRIMARY_ARTERIAL, base_speed_kmh=50.0,
        ))
    return net, node_ids


def _make_incident(location="C", category=IncidentCategory.CARDIAC_ARREST,
                   severity=IncidentSeverity.CRITICAL):
    profile = INCIDENT_PROFILES[category]
    return Incident(
        id="inc_test_001", category=category, severity=severity,
        required_capability=profile.required_capability,
        location_node_id=location, location_name=f"Test {location}",
        latitude=12.972, longitude=77.620,
        reported_at_tick=1, reported_at_sim_time_sec=10.0,
        target_response_time_sec=profile.target_response_time_sec,
        base_on_scene_time_sec=profile.base_on_scene_time_sec,
    )


class TestHybridDispatchConfig(unittest.TestCase):
    def test_default_config(self):
        config = HybridDispatchConfig()
        self.assertEqual(config.capability_eta_tolerance_pct, 0.15)
        self.assertEqual(config.max_eta_factor, 1.5)
        self.assertTrue(config.enable_coverage_analysis)

    def test_custom_config(self):
        config = HybridDispatchConfig(
            capability_eta_tolerance_pct=0.25, max_eta_factor=2.0,
            enable_coverage_analysis=False,
        )
        self.assertEqual(config.capability_eta_tolerance_pct, 0.25)
        self.assertFalse(config.enable_coverage_analysis)


class TestHybridDispatch(unittest.TestCase):
    def setUp(self):
        self.net, self.node_ids = _build_test_network()
        self.hospitals = get_default_bangalore_hospitals()
        self.strategy = HybridAureonStrategy(
            config=HybridDispatchConfig(enable_coverage_analysis=False),
        )

    def _make_ambulances(self, positions):
        return [
            Ambulance(id=f"amb_{i}", callsign=f"C{i:02d}", capability=cap,
                      base_station_id=pos, current_node_id=pos,
                      latitude=12.97, longitude=77.60)
            for i, (pos, cap) in enumerate(positions)
        ]

    def test_nearest_chosen_for_bls_incident(self):
        incident = _make_incident("C", IncidentCategory.GENERAL_MEDICAL, IncidentSeverity.MODERATE)
        ambulances = self._make_ambulances([("A", AmbulanceCapability.BLS), ("C", AmbulanceCapability.ALS)])
        decision = self.strategy.dispatch(incident, ambulances, self.hospitals, self.net)
        self.assertEqual(decision.ambulance_id, "amb_1")

    def test_nearest_when_nearest_is_als(self):
        incident = _make_incident("C")
        ambulances = self._make_ambulances([("C", AmbulanceCapability.ALS), ("E", AmbulanceCapability.BLS)])
        decision = self.strategy.dispatch(incident, ambulances, self.hospitals, self.net)
        self.assertEqual(decision.ambulance_id, "amb_0")

    def test_capability_override_within_tolerance(self):
        incident = _make_incident("C")
        ambulances = self._make_ambulances([("B", AmbulanceCapability.BLS), ("C", AmbulanceCapability.ALS)])
        decision = self.strategy.dispatch(incident, ambulances, self.hospitals, self.net)
        self.assertEqual(decision.ambulance_id, "amb_1")

    def test_nearest_when_cap_too_far(self):
        incident = _make_incident("B")
        ambulances = self._make_ambulances([("A", AmbulanceCapability.BLS), ("E", AmbulanceCapability.ALS)])
        decision = self.strategy.dispatch(incident, ambulances, self.hospitals, self.net)
        self.assertEqual(decision.ambulance_id, "amb_0")

    def test_no_ambulances_returns_empty(self):
        decision = self.strategy.dispatch(_make_incident(), [], self.hospitals, self.net)
        self.assertIsNone(decision.ambulance_id)

    def test_hospital_selected_independently(self):
        incident = _make_incident("C")
        ambulances = self._make_ambulances([("A", AmbulanceCapability.ALS)])
        decision = self.strategy.dispatch(incident, ambulances, self.hospitals, self.net)
        self.assertIsNotNone(decision.target_hospital_id)
        self.assertGreaterEqual(decision.estimated_hospital_eta_sec, 0)

    def test_dispatch_has_metadata(self):
        incident = _make_incident()
        ambulances = self._make_ambulances([("C", AmbulanceCapability.BLS)])
        decision = self.strategy.dispatch(incident, ambulances, self.hospitals, self.net)
        self.assertIn("nearest_eta_sec", decision.metadata)
        self.assertIn("eta_gap_sec", decision.metadata)
        self.assertIn("decision_reason", decision.metadata)

    def test_critical_allows_wider_tolerance(self):
        incident = _make_incident("C", IncidentCategory.CARDIAC_ARREST, IncidentSeverity.CRITICAL)
        ambulances = self._make_ambulances([("A", AmbulanceCapability.BLS), ("B", AmbulanceCapability.ALS)])
        decision = self.strategy.dispatch(incident, ambulances, self.hospitals, self.net)
        self.assertEqual(decision.ambulance_id, "amb_1")


class TestCoverageAnalyzer(unittest.TestCase):
    def setUp(self):
        self.net, _ = _build_test_network()
        self.analyzer = FleetCoverageAnalyzer(coverage_threshold_sec=300.0, gap_penalty_threshold_sec=600.0)

    def _make_ambulances(self, positions):
        return [
            Ambulance(id=f"amb_{i}", callsign=f"C{i}", capability=AmbulanceCapability.BLS,
                      base_station_id=p, current_node_id=p, latitude=12.97, longitude=77.60)
            for i, p in enumerate(positions)
        ]

    def test_single_ambulance_no_concern(self):
        ambulances = self._make_ambulances(["C"])
        a = self.analyzer.assess_dispatch_impact(ambulances[0], ambulances, ambulances, self.net)
        self.assertEqual(a.coverage_score, 1.0)

    def test_dense_cluster_ok(self):
        ambulances = self._make_ambulances(["A", "B", "C", "D", "E"])
        a = self.analyzer.assess_dispatch_impact(ambulances[2], ambulances, ambulances, self.net)
        self.assertGreater(a.coverage_score, 0.5)

    def test_sparse_creates_gap(self):
        self.net, _ = _build_test_network()
        analyzer = FleetCoverageAnalyzer(coverage_threshold_sec=100.0, gap_penalty_threshold_sec=200.0)
        ambulances = self._make_ambulances(["A", "E"])
        a = analyzer.assess_dispatch_impact(ambulances[1], ambulances, ambulances, self.net)
        self.assertTrue(a.creates_gap or a.coverage_score < 1.0)


class TestOutcomeScoring(unittest.TestCase):
    def setUp(self):
        self.net, _ = _build_test_network()
        self.scorer = EmergencyOutcomeScore()

    def test_components_total(self):
        c = OutcomeComponents(proximity_score=0.9, capability_score=0.3,
                              hospital_match_score=0.15, coverage_score=0.2,
                              distance_penalty=0.1)
        self.assertAlmostEqual(c.total, 1.45, places=2)

    def test_penalties_can_negative(self):
        c = OutcomeComponents(proximity_score=0.3, distance_penalty=0.8, capability_gap_penalty=0.5)
        self.assertLess(c.total, 0)

    def test_nearest_scores_higher_than_far(self):
        amb_near = Ambulance("a1", "N", AmbulanceCapability.BLS, "A", "A", 12.97, 77.60)
        amb_far = Ambulance("a2", "F", AmbulanceCapability.BLS, "E", "E", 12.97, 77.64)
        incident = _make_incident("B")
        r_near = self.net.calculate_route("A", "B", "time")
        r_far = self.net.calculate_route("E", "B", "time")
        s_near = self.scorer.score_dispatch_simple(amb_near, r_near.estimated_time_seconds, incident, r_near.estimated_time_seconds, False)
        s_far = self.scorer.score_dispatch_simple(amb_far, r_far.estimated_time_seconds, incident, r_near.estimated_time_seconds, False)
        self.assertGreater(s_near, s_far)

    def test_to_dict(self):
        c = OutcomeComponents(proximity_score=0.9, capability_score=0.3)
        d = c.to_dict()
        self.assertIn("total", d)


class TestDecoupledHospital(unittest.TestCase):
    def setUp(self):
        self.net, _ = _build_test_network()
        self.strategy = HybridAureonStrategy(config=HybridDispatchConfig(enable_coverage_analysis=False))

    def test_hospital_same_regardless_of_ambulance(self):
        incident = _make_incident("C")
        hospitals = get_default_bangalore_hospitals()
        amb_a = Ambulance("a1", "A", AmbulanceCapability.ALS, "A", "A", 12.97, 77.60)
        amb_e = Ambulance("a2", "E", AmbulanceCapability.ALS, "E", "E", 12.97, 77.64)
        d1 = self.strategy.dispatch(incident, [amb_a], hospitals, self.net)
        d2 = self.strategy.dispatch(incident, [amb_e], hospitals, self.net)
        self.assertEqual(d1.target_hospital_id, d2.target_hospital_id)

    def test_cardiac_prefers_cath_lab(self):
        incident = _make_incident("C", IncidentCategory.CARDIAC_ARREST, IncidentSeverity.CRITICAL)
        hosp_cardiac = Hospital(id="h_c", name="Cardiac", node_id="C",
                                latitude=12.972, longitude=77.62,
                                specialties=[HospitalSpecialty.CARDIAC_CATH_LAB])
        hosp_gen = Hospital(id="h_g", name="General", node_id="C",
                            latitude=12.972, longitude=77.62,
                            specialties=[HospitalSpecialty.GENERAL_EMERGENCY])
        amb = Ambulance("a1", "A", AmbulanceCapability.ALS, "A", "A", 12.97, 77.60)
        d = self.strategy.dispatch(incident, [amb], [hosp_cardiac, hosp_gen], self.net)
        self.assertEqual(d.target_hospital_id, "h_c")


class TestEngineIntegration(unittest.TestCase):
    def test_engine_runs_hybrid(self):
        net = build_bangalore_network()
        hospitals = get_default_bangalore_hospitals()
        fleet = create_default_bangalore_fleet()
        engine = CitySimulationEngine(
            road_network=net, hospitals=hospitals, ambulances=fleet,
            strategy=HybridAureonStrategy(config=HybridDispatchConfig(enable_coverage_analysis=False)),
        )
        candidates = [(n.id, n.name, n.latitude, n.longitude) for n in net.nodes.values()
                      if not n.is_station and not n.is_hospital]
        gen = ScenarioGenerator(node_ids_with_coords=candidates, seed=42)
        schedule = gen.generate_scenario_schedule(duration_minutes=30.0, incident_rate_per_hour=12.0)
        metrics = engine.run_scenario(schedule=schedule, duration_minutes=30.0)
        self.assertGreater(metrics.total_incidents_reported, 0)
        self.assertGreater(metrics.total_incidents_dispatched, 0)

    def test_paired_comparison_same_incidents(self):
        net = build_bangalore_network()
        hospitals = get_default_bangalore_hospitals()
        fleet = create_default_bangalore_fleet()
        candidates = [(n.id, n.name, n.latitude, n.longitude) for n in net.nodes.values()
                      if not n.is_station and not n.is_hospital]
        gen = ScenarioGenerator(node_ids_with_coords=candidates, seed=42)
        schedule = gen.generate_scenario_schedule(duration_minutes=30.0, incident_rate_per_hour=10.0)
        e1 = CitySimulationEngine(copy.deepcopy(net), copy.deepcopy(hospitals), copy.deepcopy(fleet),
                                  NearestAvailableStrategy())
        e2 = CitySimulationEngine(copy.deepcopy(net), copy.deepcopy(hospitals), copy.deepcopy(fleet),
                                  HybridAureonStrategy(config=HybridDispatchConfig(enable_coverage_analysis=False)))
        m1 = e1.run_scenario(copy.deepcopy(schedule), 30.0)
        m2 = e2.run_scenario(copy.deepcopy(schedule), 30.0)
        self.assertEqual(m1.total_incidents_reported, m2.total_incidents_reported)
        self.assertGreater(m1.total_incidents_dispatched, 0)
        self.assertGreater(m2.total_incidents_dispatched, 0)


class TestStressScenarios(unittest.TestCase):
    def _run(self, fleet_size=14, duration=30.0, rate=12.0, seed=42):
        net = build_bangalore_network()
        hospitals = get_default_bangalore_hospitals()
        fleet = create_default_bangalore_fleet()[:fleet_size]
        candidates = [(n.id, n.name, n.latitude, n.longitude) for n in net.nodes.values()
                      if not n.is_station and not n.is_hospital]
        gen = ScenarioGenerator(node_ids_with_coords=candidates, seed=seed)
        schedule = gen.generate_scenario_schedule(duration_minutes=duration, incident_rate_per_hour=rate)
        e_bl = CitySimulationEngine(copy.deepcopy(net), copy.deepcopy(hospitals), copy.deepcopy(fleet),
                                    NearestAvailableStrategy())
        e_hy = CitySimulationEngine(copy.deepcopy(net), copy.deepcopy(hospitals), copy.deepcopy(fleet),
                                    HybridAureonStrategy(config=HybridDispatchConfig(enable_coverage_analysis=False)))
        m_bl = e_bl.run_scenario(copy.deepcopy(schedule), duration)
        m_hy = e_hy.run_scenario(copy.deepcopy(schedule), duration)
        return m_bl, m_hy

    def test_scenario_a_low_fleet_high_rate(self):
        m_bl, m_hy = self._run(fleet_size=5, rate=18.0, seed=42)
        self.assertEqual(m_bl.total_incidents_reported, m_hy.total_incidents_reported)

    def test_scenario_b_critical_focus(self):
        m_bl, m_hy = self._run(fleet_size=10, rate=15.0, seed=7)
        self.assertEqual(m_bl.total_incidents_reported, m_hy.total_incidents_reported)

    def test_scenario_c_medium_fleet(self):
        m_bl, m_hy = self._run(fleet_size=7, rate=14.0, seed=99)
        self.assertEqual(m_bl.total_incidents_reported, m_hy.total_incidents_reported)

    def test_scenario_d_long_horizon(self):
        m_bl, m_hy = self._run(fleet_size=14, duration=60.0, rate=12.0, seed=42)
        self.assertEqual(m_bl.total_incidents_reported, m_hy.total_incidents_reported)


if __name__ == "__main__":
    unittest.main()
