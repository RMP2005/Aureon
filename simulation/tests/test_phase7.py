"""Phase 7 tests — Adaptive Scenario Intelligence."""

import copy
import math
import unittest

try:
    from simulation.src.dispatch.scenario_detector import (
        ScenarioDetector, ScenarioState, DispatchMode,
    )
    from simulation.src.dispatch.adaptive_policy import (
        AdaptiveAureonStrategy, BatchAssignment,
    )
    from simulation.src.dispatch.hybrid_intelligence import (
        HybridAureonStrategy, HybridDispatchConfig,
    )
    from simulation.src.dispatch.baseline import NearestAvailableStrategy
    from simulation.src.engine.city_engine import CitySimulationEngine
    from simulation.src.generators.incident_generator import (
        Incident, IncidentCategory, IncidentSeverity, ScenarioGenerator, INCIDENT_PROFILES,
    )
    from simulation.src.models.ambulance import (
        Ambulance, AmbulanceCapability, AmbulanceStatus, create_default_bangalore_fleet,
    )
    from simulation.src.models.hospital import (
        Hospital, HospitalSpecialty, get_default_bangalore_hospitals,
    )
    from simulation.src.network.bangalore_map import build_bangalore_network
    from simulation.src.network.road_graph import RoadNetwork, RoadNode, RoadEdge, RoadType
    from simulation.src.evaluation.phase7_scenarios import (
        ScenarioConfig, run_scenario_single, run_scenario_comparison, summarize_results,
        create_fleet_scarcity_scenario, create_critical_cluster_scenario,
        create_hospital_congestion_scenario, create_road_disruption_scenario,
        create_combined_disaster_scenario,
    )
except ImportError:
    from src.dispatch.scenario_detector import ScenarioDetector, ScenarioState, DispatchMode
    from src.dispatch.adaptive_policy import AdaptiveAureonStrategy, BatchAssignment
    from src.dispatch.hybrid_intelligence import HybridAureonStrategy, HybridDispatchConfig
    from src.dispatch.baseline import NearestAvailableStrategy
    from src.engine.city_engine import CitySimulationEngine
    from src.generators.incident_generator import (
        Incident, IncidentCategory, IncidentSeverity, ScenarioGenerator, INCIDENT_PROFILES,
    )
    from src.models.ambulance import (
        Ambulance, AmbulanceCapability, AmbulanceStatus, create_default_bangalore_fleet,
    )
    from src.models.hospital import Hospital, HospitalSpecialty, get_default_bangalore_hospitals
    from src.network.bangalore_map import build_bangalore_network
    from src.network.road_graph import RoadNetwork, RoadNode, RoadEdge, RoadType
    from src.evaluation.phase7_scenarios import (
        ScenarioConfig, run_scenario_single, run_scenario_comparison, summarize_results,
        create_fleet_scarcity_scenario, create_critical_cluster_scenario,
        create_hospital_congestion_scenario, create_road_disruption_scenario,
        create_combined_disaster_scenario,
    )


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


def _make_incident(inc_id="inc_001", location="C", category=IncidentCategory.CARDIAC_ARREST,
                   severity=IncidentSeverity.CRITICAL, tick=1, time_sec=10.0):
    profile = INCIDENT_PROFILES[category]
    return Incident(
        id=inc_id, category=category, severity=severity,
        required_capability=profile.required_capability,
        location_node_id=location, location_name=f"Test {location}",
        latitude=12.972, longitude=77.620,
        reported_at_tick=tick, reported_at_sim_time_sec=time_sec,
        target_response_time_sec=profile.target_response_time_sec,
        base_on_scene_time_sec=profile.base_on_scene_time_sec,
    )


def _make_ambulances(net, positions):
    return [
        Ambulance(id=f"amb_{i}", callsign=f"C{i:02d}", capability=cap,
                  base_station_id=pos, current_node_id=pos,
                  latitude=12.97, longitude=77.60)
        for i, (pos, cap) in enumerate(positions)
    ]


class TestScenarioDetector(unittest.TestCase):
    def setUp(self):
        self.net, self.node_ids = _build_test_network()

    def test_normal_state(self):
        ambulances = _make_ambulances(self.net, [("A", AmbulanceCapability.BLS)] * 5)
        detector = ScenarioDetector(network=self.net, all_ambulances=ambulances)
        state = detector.detect(
            available_ambulances=ambulances,
            pending_incidents=[],
            hospitals=[],
            road_network=self.net,
        )
        self.assertEqual(state.recommended_mode(), DispatchMode.NORMAL)
        self.assertAlmostEqual(state.fleet_pressure, 0.0)

    def test_fleet_scarcity_detection(self):
        ambulances = _make_ambulances(self.net, [("A", AmbulanceCapability.BLS)] * 5)
        detector = ScenarioDetector(network=self.net, all_ambulances=ambulances)
        state = detector.detect(
            available_ambulances=ambulances[:1],
            pending_incidents=[],
            hospitals=[],
            road_network=self.net,
        )
        self.assertGreater(state.fleet_pressure, 0.7)
        self.assertEqual(state.recommended_mode(), DispatchMode.FLEET_SCARCITY)

    def test_critical_surge_detection(self):
        ambulances = _make_ambulances(self.net, [("A", AmbulanceCapability.BLS)] * 4)
        detector = ScenarioDetector(network=self.net, all_ambulances=ambulances)
        pending = [_make_incident(f"inc_{i}", "C", severity=IncidentSeverity.CRITICAL) for i in range(3)]
        state = detector.detect(
            available_ambulances=ambulances,
            pending_incidents=pending,
            hospitals=[],
        )
        self.assertGreater(state.critical_pressure, 0.4)
        self.assertEqual(state.recommended_mode(), DispatchMode.CRITICAL_SURGE)

    def test_multi_incident_detection(self):
        ambulances = _make_ambulances(self.net, [("A", AmbulanceCapability.BLS)] * 5)
        detector = ScenarioDetector(network=self.net, all_ambulances=ambulances)
        pending = [_make_incident(f"inc_{i}", "C") for i in range(4)]
        state = detector.detect(
            available_ambulances=ambulances,
            pending_incidents=pending,
            hospitals=[],
        )
        self.assertGreaterEqual(state.pending_incident_count, 3)

    def test_spatial_clustering(self):
        ambulances = _make_ambulances(self.net, [("A", AmbulanceCapability.BLS)] * 3)
        detector = ScenarioDetector(network=self.net, all_ambulances=ambulances)
        incidents = [
            _make_incident("inc_1", "C", category=IncidentCategory.GENERAL_MEDICAL, severity=IncidentSeverity.MODERATE),
            _make_incident("inc_2", "C", category=IncidentCategory.GENERAL_MEDICAL, severity=IncidentSeverity.MODERATE),
            _make_incident("inc_3", "C", category=IncidentCategory.GENERAL_MEDICAL, severity=IncidentSeverity.MODERATE),
        ]
        state = detector.detect(
            available_ambulances=ambulances,
            pending_incidents=incidents,
            hospitals=[],
            road_network=self.net,
        )
        self.assertGreater(state.spatial_cluster_score, 0.5)

    def test_hospital_pressure_detection(self):
        ambulances = _make_ambulances(self.net, [("A", AmbulanceCapability.BLS)] * 3)
        detector = ScenarioDetector(network=self.net, all_ambulances=ambulances)
        hosp = Hospital(id="h1", name="Test", node_id="C",
                        latitude=12.972, longitude=77.62,
                        total_er_beds=10, total_icu_beds=5)
        hosp.occupied_er_beds = 9
        hosp.occupied_icu_beds = 4
        state = detector.detect(
            available_ambulances=ambulances,
            pending_incidents=[],
            hospitals=[hosp],
        )
        self.assertGreater(state.hospital_pressure, 0.8)
        self.assertEqual(state.recommended_mode(), DispatchMode.HOSPITAL_CONGESTION)

    def test_network_disruption_detection(self):
        ambulances = _make_ambulances(self.net, [("A", AmbulanceCapability.BLS)] * 3)
        self.net._edges_by_id["e_A_B"].congestion_factor = 3.0
        detector = ScenarioDetector(network=self.net, all_ambulances=ambulances)
        state = detector.detect(
            available_ambulances=ambulances,
            pending_incidents=[],
            hospitals=[],
            road_network=self.net,
        )
        self.assertTrue(state.network_disruption)
        self.assertEqual(state.recommended_mode(), DispatchMode.ROAD_DISRUPTION)

    def test_no_future_information(self):
        ambulances = _make_ambulances(self.net, [("A", AmbulanceCapability.BLS)] * 3)
        detector = ScenarioDetector(network=self.net, all_ambulances=ambulances)
        state = detector.detect(
            available_ambulances=ambulances,
            pending_incidents=[],
            hospitals=[],
        )
        self.assertEqual(state.pending_incident_count, 0)
        self.assertEqual(state.recommended_mode(), DispatchMode.NORMAL)


class TestAdaptivePolicy(unittest.TestCase):
    def setUp(self):
        self.net, self.node_ids = _build_test_network()
        self.hospitals = get_default_bangalore_hospitals()
        self.strategy = AdaptiveAureonStrategy()

    def test_normal_mode_uses_hybrid(self):
        ambulances = _make_ambulances(self.net, [("A", AmbulanceCapability.BLS)] * 5)
        incident = _make_incident()
        decision = self.strategy.dispatch(incident, ambulances, self.hospitals, self.net)
        self.assertIsNotNone(decision.ambulance_id)
        self.assertIn("Hybrid", decision.rationale)

    def test_batch_dispatch_returns_results(self):
        ambulances = _make_ambulances(self.net, [
            ("A", AmbulanceCapability.ALS), ("B", AmbulanceCapability.ALS),
            ("C", AmbulanceCapability.BLS), ("D", AmbulanceCapability.BLS),
        ])
        incidents = [_make_incident(f"inc_{i}", "C", severity=IncidentSeverity.CRITICAL) for i in range(3)]
        results = self.strategy.dispatch_batch(incidents, ambulances, self.hospitals, self.net)
        self.assertGreater(len(results), 0)

    def test_batch_unique_assignments(self):
        ambulances = _make_ambulances(self.net, [
            ("A", AmbulanceCapability.ALS), ("B", AmbulanceCapability.ALS),
            ("C", AmbulanceCapability.BLS), ("D", AmbulanceCapability.BLS),
        ])
        incidents = [_make_incident(f"inc_{i}", "C", severity=IncidentSeverity.CRITICAL) for i in range(3)]
        results = self.strategy.dispatch_batch(incidents, ambulances, self.hospitals, self.net)
        amb_ids = [d.ambulance_id for _, d in results]
        self.assertEqual(len(amb_ids), len(set(amb_ids)))

    def test_no_future_information_leakage(self):
        ambulances = _make_ambulances(self.net, [("A", AmbulanceCapability.BLS)] * 3)
        incident = _make_incident()
        decision = self.strategy.dispatch(incident, ambulances, self.hospitals, self.net)
        self.assertIsNotNone(decision.ambulance_id)
        self.assertNotIn("future", decision.rationale.lower())

    def test_deterministic_same_seed(self):
        ambulances = _make_ambulances(self.net, [("A", AmbulanceCapability.BLS)] * 5)
        incident1 = _make_incident("inc_a", "C")
        incident2 = _make_incident("inc_a", "C")
        d1 = self.strategy.dispatch(incident1, ambulances, self.hospitals, self.net)
        d2 = self.strategy.dispatch(incident2, ambulances, self.hospitals, self.net)
        self.assertEqual(d1.ambulance_id, d2.ambulance_id)

    def test_mode_stats_tracking(self):
        ambulances = _make_ambulances(self.net, [("A", AmbulanceCapability.BLS)] * 5)
        incident = _make_incident()
        self.strategy.dispatch(incident, ambulances, self.hospitals, self.net)
        stats = self.strategy.get_mode_stats()
        self.assertEqual(stats["total_dispatches"], 1)
        self.assertIn("mode_counts", stats)

    def test_supports_batch(self):
        self.assertTrue(self.strategy.supports_batch)


class TestBatchDispatch(unittest.TestCase):
    def setUp(self):
        self.net, self.node_ids = _build_test_network()
        self.hospitals = get_default_bangalore_hospitals()
        self.strategy = AdaptiveAureonStrategy()

    def test_batch_prefers_als_for_critical(self):
        ambulances = _make_ambulances(self.net, [
            ("A", AmbulanceCapability.BLS),
            ("B", AmbulanceCapability.ALS),
            ("C", AmbulanceCapability.BLS),
        ])
        critical = _make_incident("inc_crit", "C", severity=IncidentSeverity.CRITICAL)
        mild = _make_incident("inc_mild", "A", severity=IncidentSeverity.LOW,
                              category=IncidentCategory.GENERAL_MEDICAL)
        results = self.strategy.dispatch_batch(
            [critical, mild], ambulances, self.hospitals, self.net,
        )
        if results:
            decisions = dict(results)
            if "inc_crit" in decisions:
                amb = next(a for a in ambulances if a.id == decisions["inc_crit"].ambulance_id)
                self.assertTrue(amb.can_handle(critical.required_capability))

    def test_batch_empty_incidents(self):
        ambulances = _make_ambulances(self.net, [("A", AmbulanceCapability.BLS)] * 3)
        results = self.strategy.dispatch_batch([], ambulances, self.hospitals, self.net)
        self.assertEqual(len(results), 0)

    def test_batch_single_incident(self):
        ambulances = _make_ambulances(self.net, [("A", AmbulanceCapability.BLS)] * 3)
        incident = _make_incident()
        results = self.strategy.dispatch_batch([incident], ambulances, self.hospitals, self.net)
        self.assertEqual(len(results), 0)

    def test_batch_insufficient_ambulances(self):
        ambulances = _make_ambulances(self.net, [("A", AmbulanceCapability.BLS)] * 1)
        incidents = [_make_incident(f"inc_{i}", "C") for i in range(3)]
        results = self.strategy.dispatch_batch(incidents, ambulances, self.hospitals, self.net)
        self.assertEqual(len(results), 0)


class TestEngineBatchIntegration(unittest.TestCase):
    def test_engine_runs_adaptive(self):
        net = build_bangalore_network()
        hospitals = get_default_bangalore_hospitals()
        fleet = create_default_bangalore_fleet()
        engine = CitySimulationEngine(
            road_network=net, hospitals=hospitals, ambulances=fleet,
            strategy=AdaptiveAureonStrategy(),
        )
        candidates = [(n.id, n.name, n.latitude, n.longitude) for n in net.nodes.values()
                      if not n.is_station and not n.is_hospital]
        gen = ScenarioGenerator(node_ids_with_coords=candidates, seed=42)
        schedule = gen.generate_scenario_schedule(duration_minutes=30.0, incident_rate_per_hour=12.0)
        metrics = engine.run_scenario(schedule=schedule, duration_minutes=30.0)
        self.assertGreater(metrics.total_incidents_reported, 0)
        self.assertGreater(metrics.total_incidents_dispatched, 0)

    def test_engine_paired_baseline_vs_adaptive(self):
        net = build_bangalore_network()
        hospitals = get_default_bangalore_hospitals()
        fleet = create_default_bangalore_fleet()
        candidates = [(n.id, n.name, n.latitude, n.longitude) for n in net.nodes.values()
                      if not n.is_station and not n.is_hospital]
        gen = ScenarioGenerator(node_ids_with_coords=candidates, seed=42)
        schedule = gen.generate_scenario_schedule(duration_minutes=30.0, incident_rate_per_hour=12.0)

        e1 = CitySimulationEngine(copy.deepcopy(net), copy.deepcopy(hospitals), copy.deepcopy(fleet),
                                  NearestAvailableStrategy())
        e2 = CitySimulationEngine(copy.deepcopy(net), copy.deepcopy(hospitals), copy.deepcopy(fleet),
                                  AdaptiveAureonStrategy())
        m1 = e1.run_scenario(copy.deepcopy(schedule), 30.0)
        m2 = e2.run_scenario(copy.deepcopy(schedule), 30.0)
        self.assertEqual(m1.total_incidents_reported, m2.total_incidents_reported)


class TestScenarioConfigs(unittest.TestCase):
    def test_fleet_scarcity_config(self):
        config = create_fleet_scarcity_scenario()
        self.assertLessEqual(config.fleet_size, 5)
        self.assertGreater(config.incident_rate_per_hour, 12.0)

    def test_hospital_congestion_config(self):
        config = create_hospital_congestion_scenario()
        self.assertIn("occupancy_by_id", config.hospital_modifications)
        occ = config.hospital_modifications["occupancy_by_id"]
        self.assertGreater(occ["hosp_st_johns"], 0.9)
        self.assertLess(occ["hosp_vydehi"], 0.5)

    def test_road_disruption_config(self):
        config = create_road_disruption_scenario()
        self.assertGreater(len(config.road_modifications), 0)

    def test_combined_disaster_config(self):
        config = create_combined_disaster_scenario()
        self.assertLess(config.fleet_size, 14)
        self.assertIn("occupancy_by_id", config.hospital_modifications)
        self.assertGreater(len(config.road_modifications), 0)


class TestScenarioRunner(unittest.TestCase):
    def test_run_single_scenario(self):
        config = create_fleet_scarcity_scenario(seed=42)
        strategy = NearestAvailableStrategy()
        result = run_scenario_single(config, strategy, seed=42)
        self.assertEqual(result.scenario_name, "fleet_scarcity")
        self.assertGreater(result.metrics.total_incidents_reported, 0)

    def test_summarize_results(self):
        config = create_fleet_scarcity_scenario(seed=42)
        results = run_scenario_comparison(config, seeds=[42])
        summary = summarize_results(results)
        self.assertIn("Baseline", summary)
        self.assertIn("Hybrid Aureon", summary)
        self.assertIn("Adaptive Aureon", summary)


class TestRoadDisruptionScenario(unittest.TestCase):
    def test_disruption_increases_eta(self):
        net = build_bangalore_network()
        route_before = net.calculate_route("node_mg_road", "node_indiranagar", "time")
        self.assertTrue(route_before.found)

        net._edges_by_id["e_mg_indiranagar"].congestion_factor = 3.0
        net.invalidate_route_cache()

        route_after = net.calculate_route("node_mg_road", "node_indiranagar", "time")
        self.assertTrue(route_after.found)
        self.assertGreater(route_after.estimated_time_seconds, route_before.estimated_time_seconds)

    def test_ambulance_route_uses_disrupted_edge(self):
        net = build_bangalore_network()
        route = net.calculate_route("station_central_cbd", "node_indiranagar", "time")
        self.assertTrue(route.found)
        edge_ids = [e.id for e in route.edges]
        self.assertIn("e_mg_indiranagar", edge_ids)

    def test_disruption_materially_increases_ambulance_eta(self):
        net = build_bangalore_network()
        route_before = net.calculate_route("station_central_cbd", "node_indiranagar", "time")
        self.assertTrue(route_before.found)

        net._edges_by_id["e_mg_indiranagar"].congestion_factor = 3.0
        net.invalidate_route_cache()

        route_after = net.calculate_route("station_central_cbd", "node_indiranagar", "time")
        self.assertTrue(route_after.found)
        self.assertGreater(
            route_after.estimated_time_seconds,
            route_before.estimated_time_seconds * 1.5,
        )

    def test_scenario_g_config_applies_disruption(self):
        from simulation.src.evaluation.phase7_scenarios import SCENARIO_G_CONFIGS
        config = list(SCENARIO_G_CONFIGS.values())[0]
        net = build_bangalore_network()
        base_congestion = net._edges_by_id["e_mg_indiranagar"].congestion_factor

        for mod in config.road_modifications:
            if mod["edge_id"] in net._edges_by_id:
                net._edges_by_id[mod["edge_id"]].congestion_factor = mod["congestion_factor"]
        net.invalidate_route_cache()

        self.assertEqual(net._edges_by_id["e_mg_indiranagar"].congestion_factor, 3.0)
        route = net.calculate_route("station_central_cbd", "node_indiranagar", "time")
        self.assertTrue(route.found)
        self.assertGreater(route.estimated_time_seconds, 600.0)

    def test_cache_invalidation_prevents_stale_routes(self):
        net = build_bangalore_network()
        r1 = net.calculate_route("station_central_cbd", "node_indiranagar", "time")
        self.assertTrue(r1.found)
        eta_before = r1.estimated_time_seconds

        net._edges_by_id["e_mg_indiranagar"].congestion_factor = 3.0
        net.invalidate_route_cache()

        r2 = net.calculate_route("station_central_cbd", "node_indiranagar", "time")
        self.assertTrue(r2.found)
        self.assertGreater(r2.estimated_time_seconds, eta_before)


class TestRouteCacheInvalidation(unittest.TestCase):
    def test_invalidation_clears_cache(self):
        net = build_bangalore_network()
        r1 = net.calculate_route("node_mg_road", "node_indiranagar", "time")
        self.assertTrue(r1.found)
        self.assertIn(("node_mg_road", "node_indiranagar", "time"), net._route_cache)
        net.invalidate_route_cache()
        self.assertEqual(len(net._route_cache), 0)


class TestHospitalCongestionRouting(unittest.TestCase):
    def test_asymmetric_congestion_changes_hospital_selection(self):
        net = build_bangalore_network()
        hospitals = get_default_bangalore_hospitals()
        strategy = AdaptiveAureonStrategy()

        for h in hospitals:
            if h.id in ("hosp_st_johns", "hosp_manipal_hal",
                        "hosp_narayana_health", "hosp_apollo_bannerghatta"):
                h.occupied_er_beds = int(h.total_er_beds * 0.92)
                h.occupied_icu_beds = int(h.total_icu_beds * 0.92)
            elif h.id == "hosp_aster_cmi":
                h.occupied_er_beds = int(h.total_er_beds * 0.65)
                h.occupied_icu_beds = int(h.total_icu_beds * 0.65)
            elif h.id == "hosp_vydehi":
                h.occupied_er_beds = int(h.total_er_beds * 0.45)
                h.occupied_icu_beds = int(h.total_icu_beds * 0.45)

        profile = INCIDENT_PROFILES[IncidentCategory.CARDIAC_ARREST]
        inc = Incident(
            id="test_congestion", category=IncidentCategory.CARDIAC_ARREST,
            severity=IncidentSeverity.CRITICAL,
            required_capability=profile.required_capability,
            location_node_id="node_silk_board", location_name="Silk Board",
            latitude=12.92, longitude=77.65,
            reported_at_tick=0, reported_at_sim_time_sec=60.0,
            target_response_time_sec=profile.target_response_time_sec,
            base_on_scene_time_sec=profile.base_on_scene_time_sec,
        )

        normal_hospital, _, _ = strategy._select_hospital(inc, hospitals, net)
        capacity_hospital, _, _ = strategy._select_hospital_with_capacity(
            inc, hospitals, net,
        )

        self.assertIsNotNone(normal_hospital)
        self.assertIsNotNone(capacity_hospital)
        self.assertNotEqual(
            normal_hospital.id, capacity_hospital.id,
            "Capacity-aware selection should differ from normal under asymmetric congestion",
        )

        for h in hospitals:
            h.occupied_er_beds = 0
            h.occupied_icu_beds = 0

    def test_batch_uses_capacity_aware_hospital_selection(self):
        net = build_bangalore_network()
        hospitals = get_default_bangalore_hospitals()

        for h in hospitals:
            if h.id in ("hosp_st_johns", "hosp_manipal_hal",
                        "hosp_narayana_health", "hosp_apollo_bannerghatta"):
                h.occupied_er_beds = int(h.total_er_beds * 0.92)
                h.occupied_icu_beds = int(h.total_icu_beds * 0.92)
            elif h.id == "hosp_aster_cmi":
                h.occupied_er_beds = int(h.total_er_beds * 0.65)
                h.occupied_icu_beds = int(h.total_icu_beds * 0.65)
            elif h.id == "hosp_vydehi":
                h.occupied_er_beds = int(h.total_er_beds * 0.45)
                h.occupied_icu_beds = int(h.total_icu_beds * 0.45)

        strategy = AdaptiveAureonStrategy()
        hosp_id, _ = strategy._select_hospital_for_incident(
            _make_incident("inc_test", "node_silk_board",
                           category=IncidentCategory.CARDIAC_ARREST,
                           severity=IncidentSeverity.CRITICAL),
            hospitals, net,
        )
        self.assertEqual(hosp_id, "hosp_vydehi")

        for h in hospitals:
            h.occupied_er_beds = 0
            h.occupied_icu_beds = 0


class TestCoverageAwareDispatch(unittest.TestCase):
    """Coverage-aware dispatch chooses a slightly farther ambulance when
    dispatching the nearest would leave an isolated zone uncovered.

    Topology (one-way edges, both directions added):
        stn_A --600s--> INC --700s--> stn_B --400s--> stn_C

    - amb_A at stn_A (nearest to incident, 600s ETA)
    - amb_B at stn_B (second, 700s ETA — within 1.3x threshold)
    - amb_C at stn_C (available, in all_ambulances)

    Dispatching amb_A: remaining=[amb_B, amb_C]
      StationA nearest ETA = min(1300s from B, 1700s from C) = 1300s > 1200s → GAP
    Dispatching amb_B: remaining=[amb_A, amb_C]
      StationB nearest ETA = min(1300s from A, 400s from C) = 400s → OK
    """

    @staticmethod
    def _build_coverage_net():
        net = RoadNetwork("Coverage Test")
        for nid in ("stn_A", "INC", "stn_B", "stn_C"):
            net.add_node(RoadNode(id=nid, name=nid, latitude=12.97, longitude=77.60))
        # edge lengths for target travel times at 50 km/h
        edges = [
            ("e_A_inc", "stn_A", "INC", 8.333),   # 600s
            ("e_inc_B", "INC", "stn_B", 9.722),    # 700s
            ("e_B_C", "stn_B", "stn_C", 5.556),    # 400s
        ]
        for eid, src, dst, km in edges:
            net.add_edge(RoadEdge(id=eid, source_id=src, target_id=dst,
                                  length_km=km, road_type=RoadType.PRIMARY_ARTERIAL,
                                  base_speed_kmh=50.0, one_way=True))
            net.add_edge(RoadEdge(id=f"{eid}_rev", source_id=dst, target_id=src,
                                  length_km=km, road_type=RoadType.PRIMARY_ARTERIAL,
                                  base_speed_kmh=50.0, one_way=True))
        return net

    @staticmethod
    def _make_amb(cap=AmbulanceCapability.BLS):
        def _make(cid, pos):
            return Ambulance(
                id=cid, callsign=cid.upper(), capability=cap,
                base_station_id=pos, current_node_id=pos,
                latitude=12.97, longitude=77.60,
            )
        return _make

    def _incident(self):
        profile = INCIDENT_PROFILES[IncidentCategory.MINOR_INJURY]
        return Incident(
            id="inc_cov", category=IncidentCategory.MINOR_INJURY,
            severity=IncidentSeverity.MODERATE,
            required_capability=profile.required_capability,
            location_node_id="INC", location_name="Incident Node",
            latitude=12.97, longitude=77.60,
            reported_at_tick=1, reported_at_sim_time_sec=10.0,
            target_response_time_sec=profile.target_response_time_sec,
            base_on_scene_time_sec=profile.base_on_scene_time_sec,
        )

    def test_coverage_aware_picks_farther_ambulance(self):
        net = self._build_coverage_net()
        mk = self._make_amb()
        amb_a = mk("amb_A", "stn_A")
        amb_b = mk("amb_B", "stn_B")
        amb_c = mk("amb_C", "stn_C")
        available = [amb_a, amb_b, amb_c]
        hospitals = get_default_bangalore_hospitals()

        strategy = AdaptiveAureonStrategy()
        decision = strategy._dispatch_coverage_aware(
            self._incident(), available, hospitals, net, all_amb=available,
        )
        self.assertEqual(decision.ambulance_id, "amb_B",
                         f"Expected amb_B to avoid gap, got {decision.ambulance_id}: "
                         f"{decision.rationale}")

    def test_hybrid_picks_nearest(self):
        net = self._build_coverage_net()
        mk = self._make_amb()
        amb_a = mk("amb_A", "stn_A")
        amb_b = mk("amb_B", "stn_B")
        amb_c = mk("amb_C", "stn_C")
        available = [amb_a, amb_b, amb_c]
        hospitals = get_default_bangalore_hospitals()

        strategy = AdaptiveAureonStrategy()
        decision = strategy._dispatch_hybrid(
            self._incident(), available, hospitals, net, all_amb=available,
        )
        self.assertEqual(decision.ambulance_id, "amb_A",
                         f"Hybrid expected nearest amb_A, got {decision.ambulance_id}")

    def test_no_gap_uses_nearest(self):
        net = self._build_coverage_net()
        mk = self._make_amb()
        amb_a = mk("amb_A", "stn_A")
        amb_b = mk("amb_B", "stn_B")
        amb_c = mk("amb_C", "stn_C")
        amb_d = mk("amb_D", "stn_A")
        available = [amb_a, amb_b, amb_c, amb_d]
        hospitals = get_default_bangalore_hospitals()

        strategy = AdaptiveAureonStrategy()
        decision = strategy._dispatch_coverage_aware(
            self._incident(), available, hospitals, net, all_amb=available,
        )
        self.assertEqual(decision.ambulance_id, "amb_A",
                         "When no gap exists, coverage-aware should pick nearest")

    def test_single_candidate_fallback(self):
        net = self._build_coverage_net()
        mk = self._make_amb()
        amb_a = mk("amb_A", "stn_A")
        hospitals = get_default_bangalore_hospitals()

        strategy = AdaptiveAureonStrategy()
        decision = strategy._dispatch_coverage_aware(
            self._incident(), [amb_a], hospitals, net, all_amb=[amb_a],
        )
        self.assertEqual(decision.ambulance_id, "amb_A")

    def test_capability_compatibility(self):
        net = self._build_coverage_net()
        mk = self._make_amb
        amb_a = mk(AmbulanceCapability.BLS)("amb_A", "stn_A")
        amb_b = mk(AmbulanceCapability.BLS)("amb_B", "stn_B")
        amb_c = mk(AmbulanceCapability.BLS)("amb_C", "stn_C")
        hospitals = get_default_bangalore_hospitals()
        profile = INCIDENT_PROFILES[IncidentCategory.MINOR_INJURY]
        self.assertTrue(amb_a.can_handle(profile.required_capability))

        strategy = AdaptiveAureonStrategy()
        decision = strategy._dispatch_coverage_aware(
            self._incident(), [amb_a, amb_b, amb_c], hospitals, net,
            all_amb=[amb_a, amb_b, amb_c],
        )
        self.assertTrue(decision.metadata.get("capability_matched"))


class TestScenarioDetectorCoveragePressure(unittest.TestCase):
    def test_high_coverage_deficit_computed(self):
        net = RoadNetwork("Test")
        for nid in ("A", "B", "C"):
            net.add_node(RoadNode(id=nid, name=nid, latitude=12.97, longitude=77.60))
        for eid, s, d in [("e1", "A", "B"), ("e2", "B", "C")]:
            net.add_edge(RoadEdge(id=eid, source_id=s, target_id=d,
                                  length_km=20.0, road_type=RoadType.PRIMARY_ARTERIAL,
                                  base_speed_kmh=50.0, one_way=True))
            net.add_edge(RoadEdge(id=f"{eid}_r", source_id=d, target_id=s,
                                  length_km=20.0, road_type=RoadType.PRIMARY_ARTERIAL,
                                  base_speed_kmh=50.0, one_way=True))
        amb_a = Ambulance(id="a1", callsign="A1", capability=AmbulanceCapability.BLS,
                          base_station_id="A", current_node_id="A",
                          latitude=12.97, longitude=77.60)
        amb_b = Ambulance(id="a2", callsign="A2", capability=AmbulanceCapability.BLS,
                          base_station_id="B", current_node_id="B",
                          latitude=12.97, longitude=77.60)
        amb_c = Ambulance(id="a3", callsign="A3", capability=AmbulanceCapability.BLS,
                          base_station_id="C", current_node_id="C",
                          latitude=12.97, longitude=77.60)
        detector = ScenarioDetector(
            network=net, all_ambulances=[amb_a, amb_b, amb_c],
        )
        state = detector.detect(
            available_ambulances=[amb_a],
            pending_incidents=[],
            hospitals=[],
        )
        self.assertGreater(state.coverage_deficit, 0.0,
                           "With 1 of 3 ambulances available and far-apart stations, "
                           "coverage_deficit should be positive")
        mode = state.recommended_mode()
        self.assertIn(mode, (DispatchMode.NORMAL, DispatchMode.HIGH_DEMAND,
                             DispatchMode.FLEET_SCARCITY))

    def test_full_fleet_zero_deficit(self):
        net = RoadNetwork("Test")
        for nid in ("A", "B"):
            net.add_node(RoadNode(id=nid, name=nid, latitude=12.97, longitude=77.60))
        net.add_edge(RoadEdge(id="e1", source_id="A", target_id="B",
                              length_km=1.0, road_type=RoadType.PRIMARY_ARTERIAL,
                              base_speed_kmh=50.0, one_way=True))
        net.add_edge(RoadEdge(id="e1_r", source_id="B", target_id="A",
                              length_km=1.0, road_type=RoadType.PRIMARY_ARTERIAL,
                              base_speed_kmh=50.0, one_way=True))
        amb_a = Ambulance(id="a1", callsign="A1", capability=AmbulanceCapability.BLS,
                          base_station_id="A", current_node_id="A",
                          latitude=12.97, longitude=77.60)
        amb_b = Ambulance(id="a2", callsign="A2", capability=AmbulanceCapability.BLS,
                          base_station_id="B", current_node_id="B",
                          latitude=12.97, longitude=77.60)
        detector = ScenarioDetector(
            network=net, all_ambulances=[amb_a, amb_b],
        )
        state = detector.detect(
            available_ambulances=[amb_a, amb_b],
            pending_incidents=[],
            hospitals=[],
        )
        self.assertEqual(state.coverage_deficit, 0.0,
                         "Full fleet available → no coverage deficit")


if __name__ == "__main__":
    unittest.main()
