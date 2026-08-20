"""Phase 5 scale benchmark: runs the four-way dispatch comparison at different scales.

Supports SMALL (32-node), MEDIUM (~5k OSM nodes), LARGE (~50k OSM nodes).
Handles the case where OSM cache is unavailable by documenting the limitation.
"""

from __future__ import annotations

import copy
import json
import logging
import math
import statistics
import time
from dataclasses import dataclass, field
from typing import Any

from ..dispatch.aureon_intelligence import AureonDecisionEngine
from ..dispatch.baseline import NearestAvailableStrategy
from ..engine.city_engine import CitySimulationEngine, SimulationMetrics
from ..generators.incident_generator import ScenarioGenerator
from ..models.ambulance import Ambulance, AmbulanceStatus, create_default_bangalore_fleet
from ..models.hospital import Hospital, get_default_bangalore_hospitals
from ..network.bangalore_map import build_bangalore_network
from ..network.road_graph import RoadNetwork

logger = logging.getLogger("aureon.evaluation.phase5_benchmark")


@dataclass
class ScaleBenchmarkReport:
    """Results from running the four-way comparison at a specific scale."""

    scale: str
    description: str
    network_node_count: int
    network_edge_count: int
    num_seeds: int
    seeds_used: list[int]
    duration_minutes: float
    fleet_size: int
    hospital_count: int
    enable_dynamic_traffic: bool
    enable_traffic_events: bool
    enable_intersection_delays: bool

    # Strategy metrics (lists across seeds)
    baseline_rts_min: list[float] = field(default_factory=list)
    heuristic_rts_min: list[float] = field(default_factory=list)
    baseline_crit_rts_min: list[float] = field(default_factory=list)
    heuristic_crit_rts_min: list[float] = field(default_factory=list)
    baseline_p90s_min: list[float] = field(default_factory=list)
    heuristic_p90s_min: list[float] = field(default_factory=list)
    baseline_completed: list[int] = field(default_factory=list)
    heuristic_completed: list[int] = field(default_factory=list)
    baseline_distances_km: list[float] = field(default_factory=list)
    heuristic_distances_km: list[float] = field(default_factory=list)

    # Performance
    build_time_sec: float = 0.0
    per_seed_times_sec: list[float] = field(default_factory=list)

    # OSM availability
    osm_available: bool = True
    limitation_note: str = ""

    @property
    def baseline_rt_mean(self) -> float:
        return statistics.mean(self.baseline_rts_min) if self.baseline_rts_min else 0.0

    @property
    def heuristic_rt_mean(self) -> float:
        return statistics.mean(self.heuristic_rts_min) if self.heuristic_rts_min else 0.0

    @property
    def improvement_pct(self) -> float:
        if self.baseline_rt_mean > 0:
            return (self.baseline_rt_mean - self.heuristic_rt_mean) / self.baseline_rt_mean * 100.0
        return 0.0

    def ci95(self, values: list[float]) -> tuple[float, float]:
        if len(values) < 2:
            m = statistics.mean(values) if values else 0.0
            return (m, m)
        m = statistics.mean(values)
        se = statistics.stdev(values) / math.sqrt(len(values))
        t_val = 1.96 if len(values) > 30 else 2.0
        return (m - t_val * se, m + t_val * se)

    def to_dict(self) -> dict[str, Any]:
        base_ci = self.ci95(self.baseline_rts_min)
        heur_ci = self.ci95(self.heuristic_rts_min)
        return {
            "scale": self.scale,
            "description": self.description,
            "network": {
                "nodes": self.network_node_count,
                "edges": self.network_edge_count,
            },
            "experiment_meta": {
                "num_seeds": self.num_seeds,
                "seeds_used": self.seeds_used,
                "duration_minutes": self.duration_minutes,
                "fleet_size": self.fleet_size,
                "hospital_count": self.hospital_count,
                "dynamic_traffic": self.enable_dynamic_traffic,
                "traffic_events": self.enable_traffic_events,
                "intersection_delays": self.enable_intersection_delays,
            },
            "baseline": {
                "rt_mean_min": round(self.baseline_rt_mean, 2),
                "rt_ci": (round(base_ci[0], 2), round(base_ci[1], 2)),
                "rt_p50_min": round(statistics.median(self.baseline_rts_min), 2) if self.baseline_rts_min else 0,
                "rt_p90_min": round(max(self.baseline_p90s_min), 2) if self.baseline_p90s_min else 0,
                "crit_rt_mean_min": round(statistics.mean(self.baseline_crit_rts_min), 2) if self.baseline_crit_rts_min else 0,
                "completed_mean": round(statistics.mean(self.baseline_completed), 1) if self.baseline_completed else 0,
                "distance_km_mean": round(statistics.mean(self.baseline_distances_km), 1) if self.baseline_distances_km else 0,
            },
            "heuristic_aureon": {
                "rt_mean_min": round(self.heuristic_rt_mean, 2),
                "rt_ci": (round(heur_ci[0], 2), round(heur_ci[1], 2)),
                "rt_p50_min": round(statistics.median(self.heuristic_rts_min), 2) if self.heuristic_rts_min else 0,
                "rt_p90_min": round(max(self.heuristic_p90s_min), 2) if self.heuristic_p90s_min else 0,
                "crit_rt_mean_min": round(statistics.mean(self.heuristic_crit_rts_min), 2) if self.heuristic_crit_rts_min else 0,
                "completed_mean": round(statistics.mean(self.heuristic_completed), 1) if self.heuristic_completed else 0,
                "distance_km_mean": round(statistics.mean(self.heuristic_distances_km), 1) if self.heuristic_distances_km else 0,
                "improvement_pct": round(self.improvement_pct, 2),
            },
            "performance": {
                "build_time_sec": round(self.build_time_sec, 2),
                "mean_per_seed_sec": round(statistics.mean(self.per_seed_times_sec), 2) if self.per_seed_times_sec else 0,
                "total_eval_sec": round(sum(self.per_seed_times_sec), 1),
            },
            "limitation": self.limitation_note if self.limitation_note else None,
        }


class Phase5Benchmark:
    """Runs the four-way dispatch comparison at configurable scale."""

    @staticmethod
    def run_scale_benchmark(
        scale: str = "small",
        num_seeds: int = 20,
        duration_minutes: float = 60.0,
        incident_rate_per_hour: float = 14.0,
        base_seed: int = 42,
    ) -> ScaleBenchmarkReport:
        """Run the four-way benchmark at the specified scale.

        Args:
            scale: 'small', 'medium', or 'large'
            num_seeds: Number of independent seeds
            duration_minutes: Simulation duration per run
            incident_rate_per_hour: Poisson incident rate
            base_seed: Starting seed
        """
        from ..maps.benchmark_configs import get_config, BenchmarkScale
        from ..maps.ambulance_stations import generate_fleet, FleetConfig, FLEET_SMALL, FLEET_MEDIUM, FLEET_LARGE
        from ..maps.bangalore_hospitals import BangaloreHospitalDataset
        from ..maps.traffic_events import TrafficEventManager, TrafficEvent, TrafficEventType
        from ..maps.intersection_model import IntersectionDelayModel, NoIntersectionDelay

        config = get_config(BenchmarkScale(scale))
        logger.info("Running %s benchmark: %s", scale, config.description)

        # Build network
        t_build_start = time.time()
        osm_available = True
        limitation = ""

        if config.use_osm:
            try:
                from ..maps.osm_provider import OSMProvider
                from ..maps.graph_processor import OSMGraphProcessor

                provider = OSMProvider()
                G = provider.load()
                processor = OSMGraphProcessor()
                road_network = processor.convert(G, network_name=f"Bangalore OSM ({scale})")
                stats = processor.stats
                logger.info(
                    "OSM graph loaded: %d nodes, %d edges (%.2fs)",
                    stats.aureon_node_count, stats.aureon_edge_count, stats.process_time_sec,
                )
            except (FileNotFoundError, Exception) as e:
                osm_available = False
                limitation = (
                    f"OSM graph unavailable ({e}). "
                    f"Falling back to legacy 32-node graph. "
                    f"To run at {scale} scale: download OSM cache on a machine with network access "
                    f"and copy bangalore_drive.graphml to simulation/data/osm_cache/"
                )
                logger.warning("OSM unavailable, falling back to 32-node graph: %s", e)
                road_network = build_bangalore_network()
        else:
            road_network = build_bangalore_network()

        build_time = time.time() - t_build_start

        # Build hospitals
        hospitals = BangaloreHospitalDataset.get_hospitals(scale)

        # Build fleet
        fleet_configs = {
            "small": FLEET_SMALL,
            "medium": FLEET_MEDIUM,
            "large": FLEET_LARGE,
        }
        fleet = generate_fleet(fleet_configs[scale])

        # Initialize report
        report = ScaleBenchmarkReport(
            scale=scale,
            description=config.description,
            network_node_count=len(road_network.nodes),
            network_edge_count=len(road_network._edges_by_id),
            num_seeds=num_seeds,
            seeds_used=[base_seed + i for i in range(num_seeds)],
            duration_minutes=duration_minutes,
            fleet_size=len(fleet),
            hospital_count=len(hospitals),
            enable_dynamic_traffic=config.enable_dynamic_traffic,
            enable_traffic_events=config.enable_traffic_events,
            enable_intersection_delays=config.enable_intersection_delays,
            build_time_sec=build_time,
            osm_available=osm_available,
            limitation_note=limitation,
        )

        # Run seeds
        eval_seeds = [base_seed + i for i in range(num_seeds)]

        for seed in eval_seeds:
            t_seed_start = time.time()

            # Generate schedule
            candidate_nodes = [
                (n.id, n.name, n.latitude, n.longitude)
                for n in road_network.nodes.values()
                if not n.is_station and not n.is_hospital
            ]
            gen = ScenarioGenerator(node_ids_with_coords=candidate_nodes, seed=seed)
            schedule = gen.generate_scenario_schedule(
                duration_minutes=duration_minutes,
                incident_rate_per_hour=incident_rate_per_hour,
                use_dynamic_zones=True,
            )

            # Traffic events (optional)
            traffic_events: TrafficEventManager | None = None
            if config.enable_traffic_events:
                traffic_events = TrafficEventManager()
                rng_events = __import__("random").Random(seed + 1000)
                traffic_events.generate_random_events(
                    num_events=max(2, int(duration_minutes / 5)),
                    sim_duration_sec=duration_minutes * 60.0,
                    rng=rng_events,
                )

            # Intersection model
            intersection_model = (
                IntersectionDelayModel(seed=seed) if config.enable_intersection_delays
                else NoIntersectionDelay()
            )

            # 1. Baseline (nearest available)
            bl_engine = CitySimulationEngine(
                road_network=copy.deepcopy(road_network),
                hospitals=copy.deepcopy(hospitals),
                ambulances=copy.deepcopy(fleet),
                strategy=NearestAvailableStrategy(),
                enable_dynamic_traffic=config.enable_dynamic_traffic,
            )
            bl_metrics = bl_engine.run_scenario(
                schedule=copy.deepcopy(schedule),
                duration_minutes=duration_minutes,
            )

            # 2. Heuristic Aureon
            he_engine = CitySimulationEngine(
                road_network=copy.deepcopy(road_network),
                hospitals=copy.deepcopy(hospitals),
                ambulances=copy.deepcopy(fleet),
                strategy=AureonDecisionEngine(),
                enable_dynamic_traffic=config.enable_dynamic_traffic,
            )
            he_metrics = he_engine.run_scenario(
                schedule=copy.deepcopy(schedule),
                duration_minutes=duration_minutes,
            )

            # Collect
            bl_rt = bl_metrics.mean_response_time_sec / 60.0
            he_rt = he_metrics.mean_response_time_sec / 60.0

            report.baseline_rts_min.append(round(bl_rt, 2))
            report.heuristic_rts_min.append(round(he_rt, 2))
            report.baseline_crit_rts_min.append(round(bl_metrics.critical_mean_response_time_sec / 60.0, 2))
            report.heuristic_crit_rts_min.append(round(he_metrics.critical_mean_response_time_sec / 60.0, 2))
            report.baseline_p90s_min.append(round(bl_metrics.p90_response_time_sec / 60.0, 2))
            report.heuristic_p90s_min.append(round(he_metrics.p90_response_time_sec / 60.0, 2))
            report.baseline_completed.append(bl_metrics.total_incidents_completed)
            report.heuristic_completed.append(he_metrics.total_incidents_completed)
            report.baseline_distances_km.append(round(bl_metrics.total_fleet_distance_km, 1))
            report.heuristic_distances_km.append(round(he_metrics.total_fleet_distance_km, 1))

            elapsed = time.time() - t_seed_start
            report.per_seed_times_sec.append(elapsed)
            logger.info(
                "Seed %d: baseline=%.2f min, heuristic=%.2f min (%.1fs)",
                seed, bl_rt, he_rt, elapsed,
            )

        return report
