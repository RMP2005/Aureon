"""Phase 7 Scenario Definitions and Benchmark Runner.

Defines 8 controlled scenarios that stress different weaknesses of
nearest-available dispatch. Each scenario is designed to reveal conditions
where intelligent dispatch provides measurable value.

All scenarios use the small (32-node) Bangalore network for fast validation.
No XLARGE runs. No multi-hour benchmarks.

Schedule design:
  Poisson arrivals at configured rates produce ~1 incident per 5 min.
  With dt=10s ticks, batch dispatch (requires 2+ pending) never fires.
  Scenarios B-H use deterministic schedules with simultaneous arrivals to
  guarantee batch dispatch activation and mode switching.
"""

from __future__ import annotations

import copy
import logging
import math
import random
from dataclasses import dataclass, field
from typing import Any, Callable

from ..dispatch.base import BaseDispatchStrategy
from ..dispatch.baseline import NearestAvailableStrategy
from ..dispatch.hybrid_intelligence import HybridAureonStrategy, HybridDispatchConfig
from ..dispatch.adaptive_policy import AdaptiveAureonStrategy
from ..engine.city_engine import CitySimulationEngine, SimulationMetrics
from ..generators.incident_generator import (
    Incident,
    IncidentCategory,
    IncidentSeverity,
    ScenarioGenerator,
    INCIDENT_PROFILES,
)
from ..models.ambulance import (
    Ambulance,
    AmbulanceCapability,
    create_default_bangalore_fleet,
)
from ..models.hospital import Hospital, get_default_bangalore_hospitals
from ..network.bangalore_map import build_bangalore_network
from ..network.road_graph import RoadNetwork

logger = logging.getLogger("aureon.evaluation.phase7")


@dataclass
class ScenarioConfig:
    name: str
    description: str
    fleet_size: int = 14
    duration_minutes: float = 30.0
    incident_rate_per_hour: float = 12.0
    seed: int = 42
    hospital_modifications: dict[str, Any] = field(default_factory=dict)
    road_modifications: list[dict[str, Any]] = field(default_factory=list)
    custom_schedule: list[tuple[float, Incident]] | None = None
    use_dynamic_zones: bool = False
    schedule_builder: Callable[..., list[tuple[float, Incident]]] | None = field(
        default=None, repr=False,
    )


@dataclass
class ScenarioResult:
    scenario_name: str
    strategy_name: str
    seed: int
    metrics: SimulationMetrics
    mode_stats: dict[str, Any] | None = None


def _mk(inc_id, net, nid, t, category):
    n = net.nodes[nid]
    p = INCIDENT_PROFILES[category]
    return Incident(
        id=inc_id, category=category, severity=p.severity,
        required_capability=p.required_capability,
        location_node_id=n.id, location_name=n.name,
        latitude=n.latitude, longitude=n.longitude,
        reported_at_tick=0, reported_at_sim_time_sec=t,
        target_response_time_sec=p.target_response_time_sec,
        base_on_scene_time_sec=p.base_on_scene_time_sec,
    )


def _build_a(net, config, **kw):
    candidates = [
        (n.id, n.name, n.latitude, n.longitude)
        for n in net.nodes.values()
        if not n.is_station and not n.is_hospital
    ]
    gen = ScenarioGenerator(node_ids_with_coords=candidates, seed=config.seed)
    return gen.generate_scenario_schedule(
        duration_minutes=config.duration_minutes,
        incident_rate_per_hour=config.incident_rate_per_hour,
    )


def _build_b(net, config, **kw):
    locs = [
        ("node_mg_road", IncidentCategory.CARDIAC_ARREST),
        ("node_electronic_city", IncidentCategory.TRAFFIC_COLLISION),
        ("node_indiranagar", IncidentCategory.RESPIRATORY_DISTRESS),
        ("node_hebbal_flyover", IncidentCategory.GENERAL_MEDICAL),
        ("node_koramangala_sony", IncidentCategory.MAJOR_TRAUMA),
        ("node_whitefield_itpl", IncidentCategory.ACUTE_STROKE),
        ("node_btm_layout", IncidentCategory.MINOR_INJURY),
        ("node_shivajinagar", IncidentCategory.TRAFFIC_COLLISION),
    ]
    times = [60.0, 60.0, 120.0, 120.0, 200.0, 200.0, 300.0, 300.0]
    return [(t, _mk(f"inc_b{i+1:02d}", net, nid, t, cat))
            for i, ((nid, cat), t) in enumerate(zip(locs, times))]


def _build_c(net, config, **kw):
    crit = [
        ("node_mg_road", IncidentCategory.CARDIAC_ARREST),
        ("node_indiranagar", IncidentCategory.ACUTE_STROKE),
        ("node_koramangala_sony", IncidentCategory.MAJOR_TRAUMA),
        ("node_hebbal_flyover", IncidentCategory.CARDIAC_ARREST),
    ]
    mod = [
        ("node_btm_layout", IncidentCategory.GENERAL_MEDICAL),
        ("node_whitefield_itpl", IncidentCategory.MINOR_INJURY),
    ]
    out = []
    for i, (nid, cat) in enumerate(crit):
        out.append(_mk(f"inc_c{i+1:02d}", net, nid, 60.0, cat))
    for i, (nid, cat) in enumerate(mod):
        out.append(_mk(f"inc_c{i+5:02d}", net, nid, 180.0, cat))
    return [(i.reported_at_sim_time_sec, i) for i in out]


def _build_d(net, config, **kw):
    """4 incidents at t=60s with fleet_size=3. Genuine simultaneous competition."""
    locs = [
        "node_mg_road", "node_indiranagar", "node_koramangala_sony",
        "node_btm_layout",
    ]
    cats = [
        IncidentCategory.CARDIAC_ARREST, IncidentCategory.MAJOR_TRAUMA,
        IncidentCategory.TRAFFIC_COLLISION, IncidentCategory.GENERAL_MEDICAL,
    ]
    out = [_mk(f"inc_d{i+1:02d}", net, nid, 60.0, cat)
           for i, (nid, cat) in enumerate(zip(locs, cats))]
    return [(i.reported_at_sim_time_sec, i) for i in out]


def _build_e(net, config, **kw):
    hotspot = [
        ("node_silk_board", IncidentCategory.MINOR_INJURY),
        ("node_hsr_layout", IncidentCategory.GENERAL_MEDICAL),
        ("node_koramangala_sony", IncidentCategory.MINOR_INJURY),
        ("node_btm_layout", IncidentCategory.GENERAL_MEDICAL),
    ]
    dispersed = [
        ("node_hebbal_flyover", IncidentCategory.GENERAL_MEDICAL),
        ("node_whitefield_itpl", IncidentCategory.MINOR_INJURY),
    ]
    out = []
    for i, (nid, cat) in enumerate(hotspot):
        out.append(_mk(f"inc_e{i+1:02d}", net, nid, 60.0, cat))
    for i, (nid, cat) in enumerate(dispersed):
        out.append(_mk(f"inc_e{i+5:02d}", net, nid, 180.0, cat))
    return [(i.reported_at_sim_time_sec, i) for i in out]


def _build_f(net, config, **kw):
    locs = [
        ("node_koramangala_sony", IncidentCategory.CARDIAC_ARREST),
        ("node_silk_board", IncidentCategory.MAJOR_TRAUMA),
        ("node_btm_layout", IncidentCategory.CARDIAC_ARREST),
        ("node_domlur", IncidentCategory.ACUTE_STROKE),
        ("node_richmond", IncidentCategory.TRAFFIC_COLLISION),
        ("node_jayanagar_4th", IncidentCategory.RESPIRATORY_DISTRESS),
    ]
    out = []
    for i, (nid, cat) in enumerate(locs):
        t = 60.0 if i < 3 else 120.0
        out.append(_mk(f"inc_f{i+1:02d}", net, nid, t, cat))
    return [(i.reported_at_sim_time_sec, i) for i in out]


def _build_g(net, config, **kw):
    locs = [
        ("node_mg_road", IncidentCategory.CARDIAC_ARREST),
        ("node_indiranagar", IncidentCategory.MAJOR_TRAUMA),
        ("node_domlur", IncidentCategory.TRAFFIC_COLLISION),
        ("node_shivajinagar", IncidentCategory.ACUTE_STROKE),
    ]
    out = []
    for i, (nid, cat) in enumerate(locs):
        t = 60.0 if i < 2 else 120.0
        out.append(_mk(f"inc_g{i+1:02d}", net, nid, t, cat))
    return [(i.reported_at_sim_time_sec, i) for i in out]


def _build_h(net, config, **kw):
    locs = [
        ("node_mg_road", IncidentCategory.CARDIAC_ARREST),
        ("node_koramangala_sony", IncidentCategory.MAJOR_TRAUMA),
        ("node_indiranagar", IncidentCategory.CARDIAC_ARREST),
        ("node_btm_layout", IncidentCategory.TRAFFIC_COLLISION),
        ("node_hebbal_flyover", IncidentCategory.ACUTE_STROKE),
        ("node_whitefield_itpl", IncidentCategory.RESPIRATORY_DISTRESS),
    ]
    out = []
    for i, (nid, cat) in enumerate(locs):
        t = 60.0 if i < 3 else 120.0
        out.append(_mk(f"inc_h{i+1:02d}", net, nid, t, cat))
    return [(i.reported_at_sim_time_sec, i) for i in out]


SCHEDULE_BUILDERS = {
    "A": _build_a, "B": _build_b, "C": _build_c, "D": _build_d,
    "E": _build_e, "F": _build_f, "G": _build_g, "H": _build_h,
}

SCENARIO_A_CONFIGS = {
    "normal_random": ScenarioConfig(
        name="normal_random",
        description="Standard random demand. Baseline should be competitive.",
        fleet_size=14, duration_minutes=30.0, incident_rate_per_hour=12.0,
        schedule_builder=_build_a,
    ),
}

SCENARIO_B_CONFIGS = {
    "fleet_scarcity": ScenarioConfig(
        name="fleet_scarcity",
        description="Fleet=4, 8 incidents in bursts of 2. Forces coverage tradeoffs.",
        fleet_size=4, duration_minutes=30.0, incident_rate_per_hour=18.0,
        schedule_builder=_build_b,
    ),
}

SCENARIO_C_CONFIGS = {
    "critical_cluster": ScenarioConfig(
        name="critical_cluster",
        description="4 critical incidents simultaneously. Tests batch + ALS override.",
        fleet_size=14, duration_minutes=30.0, incident_rate_per_hour=24.0,
        schedule_builder=_build_c,
    ),
}

SCENARIO_D_CONFIGS = {
    "simultaneous_incidents": ScenarioConfig(
        name="simultaneous_incidents",
        description="4 incidents all at t=60s with fleet=3. Forces allocation competition.",
        fleet_size=3, duration_minutes=30.0, incident_rate_per_hour=20.0,
        schedule_builder=_build_d,
    ),
}

SCENARIO_E_CONFIGS = {
    "spatial_hotspot": ScenarioConfig(
        name="spatial_hotspot",
        description="4 incidents clustered in South-East corridor at t=60s, 2 dispersed at t=180s. Fleet=5.",
        fleet_size=5, duration_minutes=30.0, incident_rate_per_hour=15.0,
        schedule_builder=_build_e,
    ),
}

SCENARIO_F_CONFIGS = {
    "hospital_congestion": ScenarioConfig(
        name="hospital_congestion",
        description="4 hospitals congested (92pct), 2 partial. Tests capacity-aware routing.",
        fleet_size=14, duration_minutes=30.0, incident_rate_per_hour=12.0,
        hospital_modifications={
            "occupancy_by_id": {
                "hosp_st_johns": 0.92, "hosp_manipal_hal": 0.92,
                "hosp_narayana_health": 0.92, "hosp_apollo_bannerghatta": 0.92,
                "hosp_aster_cmi": 0.65, "hosp_vydehi": 0.45,
            },
        },
        schedule_builder=_build_f,
    ),
}

SCENARIO_G_CONFIGS = {
    "road_disruption": ScenarioConfig(
        name="road_disruption",
        description="MG Road-Indiranagar at 3x congestion. Tests rerouting.",
        fleet_size=14, duration_minutes=30.0, incident_rate_per_hour=12.0,
        road_modifications=[
            {"edge_id": "e_mg_indiranagar", "congestion_factor": 3.0},
        ],
        schedule_builder=_build_g,
    ),
}

SCENARIO_H_CONFIGS = {
    "combined_disaster": ScenarioConfig(
        name="combined_disaster",
        description="Fleet=7, hospital congestion, road disruption. Compound stress.",
        fleet_size=7, duration_minutes=30.0, incident_rate_per_hour=18.0,
        hospital_modifications={
            "occupancy_by_id": {
                "hosp_st_johns": 0.92, "hosp_manipal_hal": 0.92,
                "hosp_narayana_health": 0.92, "hosp_apollo_bannerghatta": 0.92,
                "hosp_aster_cmi": 0.65, "hosp_vydehi": 0.45,
            },
        },
        road_modifications=[
            {"edge_id": "e_mg_indiranagar", "congestion_factor": 2.5},
        ],
        schedule_builder=_build_h,
    ),
}

ALL_SCENARIOS = {
    "A": SCENARIO_A_CONFIGS,
    "B": SCENARIO_B_CONFIGS,
    "C": SCENARIO_C_CONFIGS,
    "D": SCENARIO_D_CONFIGS,
    "E": SCENARIO_E_CONFIGS,
    "F": SCENARIO_F_CONFIGS,
    "G": SCENARIO_G_CONFIGS,
    "H": SCENARIO_H_CONFIGS,
}


def create_normal_random_scenario(seed=42):
    return ScenarioConfig(
        name="normal_random", description="Standard random demand.",
        fleet_size=14, duration_minutes=30.0, incident_rate_per_hour=12.0,
        seed=seed, schedule_builder=_build_a,
    )


def create_fleet_scarcity_scenario(seed=42, fleet_size=4, rate=18.0):
    return ScenarioConfig(
        name="fleet_scarcity",
        description="Fleet=4, 8 incidents in bursts. Tests coverage-aware dispatch.",
        fleet_size=fleet_size, duration_minutes=30.0,
        incident_rate_per_hour=rate, seed=seed, schedule_builder=_build_b,
    )


def create_critical_cluster_scenario(seed=42):
    return ScenarioConfig(
        name="critical_cluster",
        description="4 critical incidents simultaneously. Tests batch + ALS.",
        fleet_size=14, duration_minutes=30.0, incident_rate_per_hour=24.0,
        seed=seed, schedule_builder=_build_c,
    )


def create_simultaneous_incidents_scenario(seed=42):
    return ScenarioConfig(
        name="simultaneous_incidents",
        description="6 incidents at t=60s with fleet=6. Forces allocation tradeoffs.",
        fleet_size=6, duration_minutes=30.0, incident_rate_per_hour=20.0,
        seed=seed, schedule_builder=_build_d,
    )


def create_spatial_hotspot_scenario(seed=42):
    return ScenarioConfig(
        name="spatial_hotspot",
        description="4 incidents in South-East corridor, 2 dispersed.",
        fleet_size=14, duration_minutes=30.0, incident_rate_per_hour=15.0,
        seed=seed, schedule_builder=_build_e,
    )


def create_hospital_congestion_scenario(seed=42):
    return ScenarioConfig(
        name="hospital_congestion",
        description="4 hospitals congested (92pct), 2 partial. Tests capacity-aware routing.",
        fleet_size=14, duration_minutes=30.0, incident_rate_per_hour=12.0,
        seed=seed,
        hospital_modifications={
            "occupancy_by_id": {
                "hosp_st_johns": 0.92, "hosp_manipal_hal": 0.92,
                "hosp_narayana_health": 0.92, "hosp_apollo_bannerghatta": 0.92,
                "hosp_aster_cmi": 0.65, "hosp_vydehi": 0.45,
            },
        },
        schedule_builder=_build_f,
    )


def create_road_disruption_scenario(seed=42):
    return ScenarioConfig(
        name="road_disruption",
        description="MG Road-Indiranagar at 3x congestion.",
        fleet_size=14, duration_minutes=30.0, incident_rate_per_hour=12.0,
        seed=seed,
        road_modifications=[
            {"edge_id": "e_mg_indiranagar", "congestion_factor": 3.0},
        ],
        schedule_builder=_build_g,
    )


def create_combined_disaster_scenario(seed=42):
    return ScenarioConfig(
        name="combined_disaster",
        description="Fleet=7, hospital congestion, road disruption.",
        fleet_size=7, duration_minutes=30.0, incident_rate_per_hour=18.0,
        seed=seed,
        hospital_modifications={
            "occupancy_by_id": {
                "hosp_st_johns": 0.92, "hosp_manipal_hal": 0.92,
                "hosp_narayana_health": 0.92, "hosp_apollo_bannerghatta": 0.92,
                "hosp_aster_cmi": 0.65, "hosp_vydehi": 0.45,
            },
        },
        road_modifications=[
            {"edge_id": "e_mg_indiranagar", "congestion_factor": 2.5},
        ],
        schedule_builder=_build_h,
    )


def _setup_engine(config, strategy):
    net = build_bangalore_network()
    hospitals = get_default_bangalore_hospitals()
    fleet = create_default_bangalore_fleet()[:config.fleet_size]

    occ_map = config.hospital_modifications.get("occupancy_by_id", {})
    for h in hospitals:
        if h.id in occ_map:
            occ = occ_map[h.id]
        elif h.id in config.hospital_modifications.get("congested_hospitals", []):
            occ = config.hospital_modifications["congested_occupancy"]
        else:
            continue
        h.occupied_er_beds = int(h.total_er_beds * occ)
        h.occupied_icu_beds = int(h.total_icu_beds * occ)

    for mod in config.road_modifications:
        edge_id = mod["edge_id"]
        cf = mod["congestion_factor"]
        if edge_id in net._edges_by_id:
            net._edges_by_id[edge_id].congestion_factor = cf
    net.invalidate_route_cache()

    return CitySimulationEngine(
        road_network=net, hospitals=hospitals, ambulances=fleet, strategy=strategy,
    )


def _generate_schedule(engine, config):
    if config.custom_schedule is not None:
        return config.custom_schedule

    builder = config.schedule_builder
    if builder is not None:
        return builder(engine.road_network, config)

    candidates = [
        (n.id, n.name, n.latitude, n.longitude)
        for n in engine.road_network.nodes.values()
        if not n.is_station and not n.is_hospital
    ]
    gen = ScenarioGenerator(node_ids_with_coords=candidates, seed=config.seed)
    return gen.generate_scenario_schedule(
        duration_minutes=config.duration_minutes,
        incident_rate_per_hour=config.incident_rate_per_hour,
        use_dynamic_zones=config.use_dynamic_zones,
    )


def run_scenario_single(config, strategy, seed):
    engine = _setup_engine(config, strategy)
    schedule = _generate_schedule(engine, config)

    if hasattr(strategy, '_detector'):
        strategy._detector = None
        strategy._mode_counts = {}
        strategy._total_dispatches = 0
        strategy._batch_dispatches = 0

    metrics = engine.run_scenario(schedule=schedule, duration_minutes=config.duration_minutes)

    mode_stats = None
    if hasattr(strategy, 'get_mode_stats'):
        mode_stats = strategy.get_mode_stats()

    return ScenarioResult(
        scenario_name=config.name,
        strategy_name=strategy.name,
        seed=seed,
        metrics=metrics,
        mode_stats=mode_stats,
    )


def run_scenario_comparison(config, seeds=None):
    if seeds is None:
        seeds = [42, 123, 777, 2024, 9999]

    results = {
        "Baseline": [],
        "Hybrid Aureon": [],
        "Adaptive Aureon": [],
    }

    for seed in seeds:
        logger.info("Running scenario %s with seed %d", config.name, seed)

        base = NearestAvailableStrategy()
        hybrid = HybridAureonStrategy(
            config=HybridDispatchConfig(enable_coverage_analysis=True),
        )
        adaptive = AdaptiveAureonStrategy()

        results["Baseline"].append(run_scenario_single(config, base, seed))
        results["Hybrid Aureon"].append(run_scenario_single(config, hybrid, seed))
        results["Adaptive Aureon"].append(run_scenario_single(config, adaptive, seed))

    return results


def summarize_results(results):
    summary = {}
    for strategy_name, runs in results.items():
        n = len(runs)
        if n == 0:
            continue
        mean_rt = sum(r.metrics.mean_response_time_sec for r in runs) / n / 60.0
        p90_rt = sum(r.metrics.p90_response_time_sec for r in runs) / n / 60.0
        completed = sum(r.metrics.total_incidents_completed for r in runs) / n
        critical_rt = sum(r.metrics.critical_mean_response_time_sec for r in runs) / n / 60.0
        capability = sum(r.metrics.capability_match_rate for r in runs) / n * 100.0
        suitability = sum(r.metrics.mean_hospital_suitability for r in runs) / n
        unserviced = sum(r.metrics.unserviced_incidents_count for r in runs) / n
        dispatched = sum(r.metrics.total_incidents_dispatched for r in runs) / n
        reported = sum(r.metrics.total_incidents_reported for r in runs) / n

        summary[strategy_name] = {
            "mean_response_time_min": round(mean_rt, 2),
            "p90_response_time_min": round(p90_rt, 2),
            "critical_mean_rt_min": round(critical_rt, 2),
            "capability_match_pct": round(capability, 1),
            "hospital_suitability": round(suitability, 3),
            "completed_incidents": round(completed, 1),
            "dispatched_incidents": round(dispatched, 1),
            "reported_incidents": round(reported, 1),
            "unserviced": round(unserviced, 1),
            "n_seeds": n,
        }

        batch_total = sum(
            r.mode_stats.get("batch_dispatches", 0) if r.mode_stats else 0
            for r in runs
        )
        mode_counts = {}
        for r in runs:
            if r.mode_stats and "mode_counts" in r.mode_stats:
                for k, v in r.mode_stats["mode_counts"].items():
                    mode_counts[k] = mode_counts.get(k, 0) + v
        summary[strategy_name]["batch_dispatches"] = batch_total
        summary[strategy_name]["mode_counts"] = mode_counts

    return summary
