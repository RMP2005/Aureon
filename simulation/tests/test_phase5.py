"""Tests for Phase 5: Real Bangalore Digital Twin components."""

import copy
import math
import random
import unittest

from simulation.src.maps.osm_provider import OSMProvider, BANGALORE_BBOX_NORTH, BANGALORE_BBOX_SOUTH
from simulation.src.maps.graph_processor import (
    OSMPatialIndex, OSMGraphProcessor, assign_zone, classify_road_type,
)
from simulation.src.maps.bangalore_hospitals import BangaloreHospitalDataset
from simulation.src.maps.ambulance_stations import (
    get_stations, generate_fleet, FleetConfig, FLEET_SMALL, FLEET_MEDIUM, FLEET_LARGE, FLEET_XLARGE,
)
from simulation.src.maps.traffic_model import SpatialTrafficModel
from simulation.src.maps.traffic_events import (
    TrafficEventManager, TrafficEvent, TrafficEventType,
)
from simulation.src.maps.intersection_model import IntersectionDelayModel, NoIntersectionDelay
from simulation.src.maps.benchmark_configs import BenchmarkScale, get_config, get_all_configs
from simulation.src.network.road_graph import RoadType, RoadNetwork, RoadNode, RoadEdge
from simulation.src.evaluation.phase5_benchmark import Phase5Benchmark


class TestOSMProvider(unittest.TestCase):
    """Tests for OSM graph loading and caching."""

    def test_provider_initializes(self) -> None:
        provider = OSMProvider()
        self.assertEqual(provider.source, "cache")
        self.assertIsNotNone(provider.cache_path)

    def test_provider_cache_info_when_missing(self) -> None:
        provider = OSMProvider(cache_dir="/tmp/aureon_test_nonexistent")
        info = provider.get_cache_info()
        self.assertFalse(info["exists"])

    def test_provider_bbox_defaults(self) -> None:
        provider = OSMProvider()
        self.assertEqual(provider.bbox[0], BANGALORE_BBOX_NORTH)
        self.assertEqual(provider.bbox[1], BANGALORE_BBOX_SOUTH)

    def test_cache_mode_raises_when_no_cache(self) -> None:
        provider = OSMProvider(cache_dir="/tmp/aureon_test_nonexistent")
        with self.assertRaises(FileNotFoundError):
            provider.load()


class TestGraphProcessor(unittest.TestCase):
    """Tests for spatial indexing and graph conversion."""

    def test_assign_zone_cbd(self) -> None:
        zone = assign_zone(12.9756, 77.6066)
        self.assertEqual(zone, "CBD")

    def test_assign_zone_electronic_city(self) -> None:
        zone = assign_zone(12.8399, 77.6770)
        self.assertEqual(zone, "South")

    def test_assign_zone_outside(self) -> None:
        zone = assign_zone(13.5, 78.0)
        self.assertEqual(zone, "General")

    def test_road_type_classification(self) -> None:
        self.assertEqual(classify_road_type("motorway"), RoadType.EXPRESSWAY)
        self.assertEqual(classify_road_type("primary"), RoadType.PRIMARY_ARTERIAL)
        self.assertEqual(classify_road_type("residential"), RoadType.RESIDENTIAL)
        self.assertEqual(classify_road_type("unknown"), RoadType.SECONDARY)

    def test_road_type_list_input(self) -> None:
        self.assertEqual(classify_road_type(["primary", "secondary"]), RoadType.PRIMARY_ARTERIAL)

    def test_spatial_index_builds(self) -> None:
        node_ids = ["n1", "n2", "n3"]
        lats = [12.97, 12.98, 12.99]
        lons = [77.60, 77.61, 77.62]
        idx = OSMPatialIndex(node_ids, lats, lons)
        self.assertGreater(idx.build_time_sec, 0)

    def test_spatial_index_nearest_node(self) -> None:
        node_ids = ["n1", "n2", "n3"]
        lats = [12.97, 12.98, 12.99]
        lons = [77.60, 77.61, 77.62]
        idx = OSMPatialIndex(node_ids, lats, lons)
        nearest = idx.nearest_node(12.971, 77.601)
        self.assertEqual(nearest, "n1")

    def test_spatial_index_batch_nearest(self) -> None:
        node_ids = ["n1", "n2", "n3"]
        lats = [12.97, 12.98, 12.99]
        lons = [77.60, 77.61, 77.62]
        idx = OSMPatialIndex(node_ids, lats, lons)
        result = idx.nearest_nodes([12.971, 12.991], [77.601, 77.621])
        self.assertEqual(result, ["n1", "n3"])

    def test_spatial_index_radius_query(self) -> None:
        node_ids = ["n1", "n2", "n3"]
        lats = [12.97, 12.98, 13.10]
        lons = [77.60, 77.61, 77.90]
        idx = OSMPatialIndex(node_ids, lats, lons)
        nearby = idx.nodes_within_radius(12.975, 77.605, radius_km=2.0)
        self.assertIn("n1", nearby)
        self.assertIn("n2", nearby)
        self.assertNotIn("n3", nearby)

    def test_processor_stats(self) -> None:
        processor = OSMGraphProcessor()
        self.assertIsNone(processor.stats)


class TestBangaloreHospitals(unittest.TestCase):
    """Tests for hospital dataset."""

    def test_small_scale(self) -> None:
        hospitals = BangaloreHospitalDataset.get_hospitals("small")
        self.assertEqual(len(hospitals), 6)

    def test_medium_scale(self) -> None:
        hospitals = BangaloreHospitalDataset.get_hospitals("medium")
        self.assertGreater(len(hospitals), 10)

    def test_large_scale(self) -> None:
        hospitals = BangaloreHospitalDataset.get_hospitals("large")
        self.assertGreater(len(hospitals), 20)

    def test_invalid_scale(self) -> None:
        with self.assertRaises(ValueError):
            BangaloreHospitalDataset.get_hospitals("xlarge")

    def test_all_hospitals_have_coordinates(self) -> None:
        for scale in ("small", "medium", "large"):
            hospitals = BangaloreHospitalDataset.get_hospitals(scale)
            for h in hospitals:
                self.assertGreater(h.latitude, 12.0, f"{h.name} lat too low")
                self.assertLess(h.latitude, 14.0, f"{h.name} lat too high")
                self.assertGreater(h.longitude, 77.0, f"{h.name} lon too low")
                self.assertLess(h.longitude, 78.0, f"{h.name} lon too high")

    def test_hospital_has_synthetic_capacity_marker(self) -> None:
        # Only large-scale hospitals built by BangaloreHospitalDataset have the marker.
        # Small-scale uses the legacy get_default_bangalore_hospitals() without it.
        large = BangaloreHospitalDataset.get_hospitals("large")
        marked = [h for h in large if "capacity_source" in h.metadata]
        self.assertGreater(len(marked), 0, "At least some large hospitals should have synthetic markers")
        for h in marked:
            self.assertEqual(h.metadata["capacity_source"], "SIMULATION CONFIGURATION")

    def test_get_hospital_by_node_id(self) -> None:
        hospitals = BangaloreHospitalDataset.get_hospitals("small")
        from simulation.src.maps.bangalore_hospitals import get_hospital_by_node_id
        if hospitals:
            found = get_hospital_by_node_id(hospitals, hospitals[0].node_id)
            self.assertIsNotNone(found)


class TestAmbulanceStations(unittest.TestCase):
    """Tests for ambulance stations and fleet generation."""

    def test_station_count(self) -> None:
        stations = get_stations()
        self.assertEqual(len(stations), 10)

    def test_station_coordinates(self) -> None:
        stations = get_stations()
        for s in stations:
            self.assertGreater(s.latitude, 12.0)
            self.assertLess(s.latitude, 14.0)
            self.assertGreater(s.longitude, 77.0)

    def test_fleet_small(self) -> None:
        fleet = generate_fleet(FLEET_SMALL)
        self.assertEqual(len(fleet), 14)
        als = sum(1 for a in fleet if a.capability.value == "ALS")
        self.assertGreater(als, 0)
        self.assertLess(als, len(fleet))

    def test_fleet_medium(self) -> None:
        fleet = generate_fleet(FLEET_MEDIUM)
        self.assertEqual(len(fleet), 30)

    def test_fleet_large(self) -> None:
        fleet = generate_fleet(FLEET_LARGE)
        self.assertEqual(len(fleet), 50)

    def test_fleet_xlarge(self) -> None:
        fleet = generate_fleet(FLEET_XLARGE)
        self.assertEqual(len(fleet), 100)

    def test_fleet_als_ratio(self) -> None:
        for cfg in [FLEET_SMALL, FLEET_MEDIUM, FLEET_LARGE, FLEET_XLARGE]:
            fleet = generate_fleet(cfg)
            als = sum(1 for a in fleet if a.capability.value == "ALS")
            ratio = als / len(fleet)
            self.assertGreater(ratio, 0.2, f"ALS ratio too low for fleet size {cfg.num_ambulances}")
            self.assertLess(ratio, 0.5, f"ALS ratio too high for fleet size {cfg.num_ambulances}")

    def test_fleet_unique_ids(self) -> None:
        fleet = generate_fleet(FLEET_LARGE)
        ids = [a.id for a in fleet]
        self.assertEqual(len(ids), len(set(ids)))

    def test_fleet_all_idle_at_base(self) -> None:
        fleet = generate_fleet(FLEET_SMALL)
        for a in fleet:
            self.assertEqual(a.status.value, "idle_at_base")


class TestSpatialTrafficModel(unittest.TestCase):
    """Tests for the spatially correlated traffic model."""

    def test_returns_congestion_factor(self) -> None:
        model = SpatialTrafficModel(seed=42)
        factor = model.get_edge_congestion(12.97, 77.60, 12.98, 77.61, RoadType.PRIMARY_ARTERIAL, 0.0)
        self.assertGreater(factor, 0.0)
        self.assertLess(factor, 5.0)

    def test_deterministic(self) -> None:
        m1 = SpatialTrafficModel(seed=42)
        m2 = SpatialTrafficModel(seed=42)
        f1 = m1.get_edge_congestion(12.97, 77.60, 12.98, 77.61, RoadType.SECONDARY, 3600.0)
        f2 = m2.get_edge_congestion(12.97, 77.60, 12.98, 77.61, RoadType.SECONDARY, 3600.0)
        self.assertAlmostEqual(f1, f2, places=6)

    def test_peak_hour_higher_congestion(self) -> None:
        model = SpatialTrafficModel(seed=42)
        night = model.get_edge_congestion(12.97, 77.60, 12.98, 77.61, RoadType.PRIMARY_ARTERIAL, 0.0)
        morning = model.get_edge_congestion(12.97, 77.60, 12.98, 77.61, RoadType.PRIMARY_ARTERIAL, 8 * 3600.0)
        self.assertGreater(morning, night)

    def test_expressway_lower_congestion(self) -> None:
        model = SpatialTrafficModel(seed=42)
        t = 8 * 3600.0
        exp = model.get_edge_congestion(12.97, 77.60, 12.98, 77.61, RoadType.EXPRESSWAY, t)
        res = model.get_edge_congestion(12.97, 77.60, 12.98, 77.61, RoadType.RESIDENTIAL, t)
        self.assertLessEqual(exp, res)

    def test_congestion_event(self) -> None:
        model = SpatialTrafficModel(seed=42)
        event_id = model.apply_congestion_event(12.97, 77.60, 2.0, 3.0, 300.0)
        self.assertIsNotNone(event_id)
        factor_before = model.get_edge_congestion(12.97, 77.60, 12.971, 77.601, RoadType.SECONDARY, 0.0)
        self.assertGreater(factor_before, 1.0)
        model.remove_congestion_event(event_id)


class TestTrafficEvents(unittest.TestCase):
    """Tests for traffic events (road closures, construction, etc.)."""

    def test_event_manager_creates(self) -> None:
        mgr = TrafficEventManager()
        self.assertIsNotNone(mgr)

    def test_add_event(self) -> None:
        mgr = TrafficEventManager()
        event = TrafficEvent(
            id="test_1",
            event_type=TrafficEventType.ROAD_CLOSURE,
            latitude=12.97,
            longitude=77.60,
            radius_km=1.0,
            congestion_factor=25.0,
            start_time_sec=0.0,
            duration_sec=300.0,
        )
        mgr.add_event(event)
        active = mgr.get_active_events(60.0)
        self.assertEqual(len(active), 1)

    def test_event_expires(self) -> None:
        mgr = TrafficEventManager()
        event = TrafficEvent(
            id="test_1",
            event_type=TrafficEventType.CONGESTION_SPIKE,
            latitude=12.97,
            longitude=77.60,
            radius_km=1.0,
            congestion_factor=3.0,
            start_time_sec=0.0,
            duration_sec=100.0,
        )
        mgr.add_event(event)
        active = mgr.get_active_events(200.0)
        self.assertEqual(len(active), 0)

    def test_update_network(self) -> None:
        mgr = TrafficEventManager()
        net = RoadNetwork("test")
        node_a = RoadNode("a", "A", 12.97, 77.60)
        node_b = RoadNode("b", "B", 12.971, 77.601)
        net.add_node(node_a)
        net.add_node(node_b)
        edge = RoadEdge("e1", "a", "b", 0.1, RoadType.SECONDARY, 30.0)
        net.add_edge(edge)

        event = TrafficEvent(
            id="test_1",
            event_type=TrafficEventType.ROAD_CLOSURE,
            latitude=12.97,
            longitude=77.60,
            radius_km=5.0,
            congestion_factor=25.0,
            start_time_sec=0.0,
            duration_sec=300.0,
        )
        mgr.add_event(event)
        affected = mgr.update_network(net, 60.0)
        self.assertGreater(affected, 0)

    def test_generate_random_events(self) -> None:
        mgr = TrafficEventManager()
        rng = random.Random(42)
        events = mgr.generate_random_events(10, 3600.0, rng)
        self.assertEqual(len(events), 10)
        for e in events:
            self.assertIn(e.event_type, list(TrafficEventType))


class TestIntersectionDelay(unittest.TestCase):
    """Tests for intersection/signal delay model."""

    def test_zero_delay_on_expressway(self) -> None:
        model = IntersectionDelayModel(seed=42)
        delay = model.estimate_total_delay(5, ["expressway"] * 5, is_emergency=False)
        self.assertEqual(delay, 0.0)

    def test_delay_on_arterial(self) -> None:
        model = IntersectionDelayModel(seed=42)
        delay = model.estimate_total_delay(5, ["arterial"] * 5, is_emergency=False)
        self.assertGreater(delay, 0.0)

    def test_emergency_reduces_delay(self) -> None:
        model = IntersectionDelayModel(seed=42)
        normal = model.estimate_total_delay(10, ["arterial"] * 10, is_emergency=False)
        emergency = model.estimate_total_delay(10, ["arterial"] * 10, is_emergency=True)
        self.assertLess(emergency, normal)

    def test_no_delay_model(self) -> None:
        model = NoIntersectionDelay()
        self.assertEqual(model.estimate_total_delay(10, ["arterial"] * 10), 0.0)
        self.assertEqual(model.per_intersection_delay("arterial"), 0.0)

    def test_deterministic(self) -> None:
        m1 = IntersectionDelayModel(seed=42)
        m2 = IntersectionDelayModel(seed=42)
        d1 = m1.estimate_total_delay(10, ["primary"] * 10)
        d2 = m2.estimate_total_delay(10, ["primary"] * 10)
        self.assertAlmostEqual(d1, d2, places=6)


class TestBenchmarkConfigs(unittest.TestCase):
    """Tests for benchmark configuration system."""

    def test_all_scales(self) -> None:
        configs = get_all_configs()
        self.assertIn(BenchmarkScale.SMALL, configs)
        self.assertIn(BenchmarkScale.MEDIUM, configs)
        self.assertIn(BenchmarkScale.LARGE, configs)

    def test_small_config(self) -> None:
        cfg = get_config(BenchmarkScale.SMALL)
        self.assertFalse(cfg.use_osm)
        self.assertEqual(cfg.fleet_size, 14)

    def test_medium_config(self) -> None:
        cfg = get_config(BenchmarkScale.MEDIUM)
        self.assertTrue(cfg.use_osm)
        self.assertIsNotNone(cfg.osm_subset_bbox)

    def test_large_config(self) -> None:
        cfg = get_config(BenchmarkScale.LARGE)
        self.assertTrue(cfg.use_osm)
        self.assertIsNone(cfg.osm_subset_bbox)


class TestPhase5Benchmark(unittest.TestCase):
    """Integration tests for the Phase 5 benchmark runner."""

    def test_small_benchmark_runs(self) -> None:
        report = Phase5Benchmark.run_scale_benchmark(
            scale="small", num_seeds=2, duration_minutes=15.0,
            incident_rate_per_hour=14.0,
        )
        self.assertEqual(report.scale, "small")
        self.assertEqual(report.num_seeds, 2)
        self.assertEqual(len(report.baseline_rts_min), 2)
        self.assertEqual(len(report.heuristic_rts_min), 2)
        self.assertGreater(report.baseline_rt_mean, 0)
        self.assertGreater(report.heuristic_rt_mean, 0)

    def test_medium_benchmark_falls_back(self) -> None:
        report = Phase5Benchmark.run_scale_benchmark(
            scale="medium", num_seeds=1, duration_minutes=15.0,
            incident_rate_per_hour=14.0,
        )
        self.assertFalse(report.osm_available)
        self.assertIn("OSM", report.limitation_note)

    def test_report_serialization(self) -> None:
        report = Phase5Benchmark.run_scale_benchmark(
            scale="small", num_seeds=1, duration_minutes=15.0,
            incident_rate_per_hour=14.0,
        )
        data = report.to_dict()
        self.assertIn("baseline", data)
        self.assertIn("heuristic_aureon", data)
        self.assertIn("performance", data)
        self.assertIn("network", data)

    def test_report_has_ci(self) -> None:
        report = Phase5Benchmark.run_scale_benchmark(
            scale="small", num_seeds=3, duration_minutes=15.0,
            incident_rate_per_hour=14.0,
        )
        data = report.to_dict()
        ci = data["baseline"]["rt_ci"]
        self.assertEqual(len(ci), 2)
        self.assertLessEqual(ci[0], ci[1])


if __name__ == "__main__":
    unittest.main()
