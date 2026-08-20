"""Tests for Phase 2.2: Dynamic traffic model, zone-weighted incidents, multi-seed evaluation."""

from __future__ import annotations

import pytest

from simulation.src.evaluation.evaluator import MultiSeedReport, SimulationEvaluator
from simulation.src.generators.incident_generator import ScenarioGenerator
from simulation.src.models.dynamic_city import (
    CONGESTION_PROFILES,
    ZONE_WEIGHT_PROFILES,
    DynamicTrafficModel,
    TimePeriod,
    get_time_period,
    get_zone_weights,
)
from simulation.src.network.bangalore_map import build_bangalore_network
from simulation.src.network.road_graph import RoadType


# ---------------------------------------------------------------------------
# Time Period Detection
# ---------------------------------------------------------------------------

class TestTimePeriod:
    def test_0800_is_early_morning(self) -> None:
        assert get_time_period(0) == TimePeriod.EARLY_MORNING  # 08:00

    def test_0900_is_morning_peak(self) -> None:
        assert get_time_period(3600) == TimePeriod.MORNING_PEAK  # 09:00

    def test_1200_is_midday(self) -> None:
        assert get_time_period(14400) == TimePeriod.MIDDAY  # 12:00

    def test_1700_is_evening_peak(self) -> None:
        assert get_time_period(32400) == TimePeriod.EVENING_PEAK  # 17:00

    def test_2100_is_night(self) -> None:
        assert get_time_period(46800) == TimePeriod.NIGHT  # 21:00

    def test_0100_is_late_night(self) -> None:
        assert get_time_period(64800) == TimePeriod.LATE_NIGHT  # 01:00 next day


# ---------------------------------------------------------------------------
# Congestion Profiles
# ---------------------------------------------------------------------------

class TestCongestionProfiles:
    def test_all_periods_defined(self) -> None:
        for period in TimePeriod:
            assert period in CONGESTION_PROFILES

    def test_all_road_types_covered(self) -> None:
        for period in TimePeriod:
            for road_type in RoadType:
                assert road_type in CONGESTION_PROFILES[period]

    def test_morning_peak_congested(self) -> None:
        profile = CONGESTION_PROFILES[TimePeriod.MORNING_PEAK]
        assert profile[RoadType.CONGESTED_CORRIDOR] >= 2.5
        assert profile[RoadType.PRIMARY_ARTERIAL] >= 2.0

    def test_late_night_free_flow(self) -> None:
        profile = CONGESTION_PROFILES[TimePeriod.LATE_NIGHT]
        assert profile[RoadType.EXPRESSWAY] < 1.0
        assert profile[RoadType.PRIMARY_ARTERIAL] < 1.0

    def test_evening_peak_highest(self) -> None:
        evening = CONGESTION_PROFILES[TimePeriod.EVENING_PEAK]
        morning = CONGESTION_PROFILES[TimePeriod.MORNING_PEAK]
        assert evening[RoadType.CONGESTED_CORRIDOR] >= morning[RoadType.CONGESTED_CORRIDOR]


# ---------------------------------------------------------------------------
# Dynamic Traffic Model
# ---------------------------------------------------------------------------

class TestDynamicTrafficModel:
    def test_updates_congestion(self) -> None:
        net = build_bangalore_network()
        model = DynamicTrafficModel(net)
        model.update(3600)  # 09:00 morning peak
        for edges in net._adjacency.values():
            for edge in edges:
                if edge.road_type == RoadType.CONGESTED_CORRIDOR:
                    assert edge.congestion_factor == 3.0
                    return

    def test_no_update_same_period(self) -> None:
        net = build_bangalore_network()
        model = DynamicTrafficModel(net)
        model.update(3600)
        model.update(5000)  # Still morning peak
        assert model._last_update_sec == 3600  # Didn't update again

    def test_returns_correct_period(self) -> None:
        net = build_bangalore_network()
        model = DynamicTrafficModel(net)
        assert model.get_current_period(0) == TimePeriod.EARLY_MORNING
        assert model.get_current_period(32400) == TimePeriod.EVENING_PEAK


# ---------------------------------------------------------------------------
# Zone Weights
# ---------------------------------------------------------------------------

class TestZoneWeights:
    def test_all_periods_have_weights(self) -> None:
        for period in TimePeriod:
            assert period in ZONE_WEIGHT_PROFILES

    def test_weights_vary_by_zone(self) -> None:
        weights = get_zone_weights(3600)
        assert weights["Koramangala"] != weights["Electronic City"]

    def test_peak_zones_higher(self) -> None:
        morning = get_zone_weights(3600)  # 09:00
        night = get_zone_weights(46800)  # 21:00
        assert morning["Koramangala"] > night["Koramangala"]


# ---------------------------------------------------------------------------
# Dynamic Incident Generation
# ---------------------------------------------------------------------------

class TestDynamicIncidentGeneration:
    def test_zone_weighted_generation(self) -> None:
        net = build_bangalore_network()
        nodes = [(n.id, n.name, n.latitude, n.longitude)
                 for n in net.nodes.values() if not n.is_station and not n.is_hospital]
        gen = ScenarioGenerator(node_ids_with_coords=nodes, seed=42)
        zone_weights = get_zone_weights(3600)

        locations = []
        for _ in range(200):
            inc = gen.generate_incident(tick=0, sim_time_sec=3600, zone_weights=zone_weights)
            locations.append(inc.location_name)
        assert len(locations) == 200
        assert len(set(locations)) > 1  # Multiple zones represented

    def test_dynamic_schedule(self) -> None:
        net = build_bangalore_network()
        nodes = [(n.id, n.name, n.latitude, n.longitude)
                 for n in net.nodes.values() if not n.is_station and not n.is_hospital]
        gen = ScenarioGenerator(node_ids_with_coords=nodes, seed=42)
        schedule = gen.generate_scenario_schedule(
            duration_minutes=30, incident_rate_per_hour=14, use_dynamic_zones=True,
        )
        assert len(schedule) > 0
        assert all(inc[1].id.startswith("inc_") for inc in schedule)


# ---------------------------------------------------------------------------
# Benchmark with Dynamic Features
# ---------------------------------------------------------------------------

class TestDynamicBenchmark:
    def test_benchmark_with_dynamic_traffic(self) -> None:
        report = SimulationEvaluator.run_benchmark(
            duration_minutes=30, incident_rate_per_hour=14, seed=42,
            enable_dynamic_traffic=True, use_dynamic_zones=True,
        )
        d = report.to_dict()
        assert d["baseline"]["response_times_minutes"]["mean"] > 0
        assert d["aureon_intelligence"]["response_times_minutes"]["mean"] > 0

    def test_benchmark_without_dynamic_traffic(self) -> None:
        report = SimulationEvaluator.run_benchmark(
            duration_minutes=30, incident_rate_per_hour=14, seed=42,
            enable_dynamic_traffic=False, use_dynamic_zones=False,
        )
        d = report.to_dict()
        assert d["baseline"]["response_times_minutes"]["mean"] > 0


# ---------------------------------------------------------------------------
# Multi-Seed Benchmark
# ---------------------------------------------------------------------------

class TestMultiSeedBenchmark:
    def test_runs_multiple_seeds(self) -> None:
        report = SimulationEvaluator.run_multi_seed_benchmark(
            num_seeds=3, duration_minutes=15, incident_rate_per_hour=14, base_seed=42,
        )
        assert report.num_seeds == 3
        assert len(report.per_seed_results) == 3
        assert report.seeds_used == [42, 43, 44]

    def test_statistics_computed(self) -> None:
        report = SimulationEvaluator.run_multi_seed_benchmark(
            num_seeds=3, duration_minutes=15, incident_rate_per_hour=14, base_seed=42,
        )
        assert report.baseline_rt_mean > 0
        assert report.aureon_rt_mean > 0
        assert report.baseline_rt_ci_lower <= report.baseline_rt_mean <= report.baseline_rt_ci_upper

    def test_serialization(self) -> None:
        report = SimulationEvaluator.run_multi_seed_benchmark(
            num_seeds=3, duration_minutes=15, incident_rate_per_hour=14, base_seed=42,
        )
        d = report.to_dict()
        assert "experiment_meta" in d
        assert "baseline_statistics" in d
        assert "aureon_statistics" in d
        assert "improvement_statistics" in d
        assert "per_seed_results" in d
        assert len(d["per_seed_results"]) == 3
