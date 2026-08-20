"""Evaluation and side-by-side comparison system for emergency response strategies."""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass
from typing import Any

from ..dispatch.aureon_intelligence import AureonDecisionEngine
from ..dispatch.baseline import NearestAvailableStrategy
from ..engine.city_engine import CitySimulationEngine, SimulationMetrics
from ..generators.incident_generator import ScenarioGenerator
from ..models.ambulance import create_default_bangalore_fleet
from ..models.hospital import get_default_bangalore_hospitals
from ..network.bangalore_map import build_bangalore_network

logger = logging.getLogger("aureon.simulation.evaluator")


@dataclass
class ComparisonReport:
    """Side-by-side comparative analysis of Baseline vs Aureon strategies."""

    baseline_metrics: SimulationMetrics
    aureon_metrics: SimulationMetrics
    duration_minutes: float
    incident_count: int

    response_time_improvement_percent: float
    critical_response_time_improvement_percent: float
    target_compliance_delta_percent: float
    capability_match_improvement_percent: float
    hospital_suitability_improvement_percent: float
    fleet_distance_saved_km: float

    def to_dict(self) -> dict[str, Any]:
        """Convert comparison to serialized format."""
        return {
            "experiment_meta": {
                "duration_minutes": self.duration_minutes,
                "total_incidents": self.incident_count,
            },
            "baseline": self.baseline_metrics.to_dict(),
            "aureon_intelligence": self.aureon_metrics.to_dict(),
            "improvements": {
                "overall_response_time_improvement_percent": round(
                    self.response_time_improvement_percent, 2
                ),
                "critical_case_response_time_improvement_percent": round(
                    self.critical_response_time_improvement_percent, 2
                ),
                "golden_hour_compliance_gain_percent": round(
                    self.target_compliance_delta_percent, 2
                ),
                "clinical_capability_matching_gain_percent": round(
                    self.capability_match_improvement_percent, 2
                ),
                "hospital_suitability_gain_percent": round(
                    self.hospital_suitability_improvement_percent, 2
                ),
                "fleet_distance_saved_km": round(self.fleet_distance_saved_km, 2),
            },
        }


class SimulationEvaluator:
    """Orchestrates controlled experiments to benchmark dispatch strategies."""

    @staticmethod
    def run_benchmark(
        duration_minutes: float = 60.0,
        incident_rate_per_hour: float = 14.0,
        seed: int = 42,
    ) -> ComparisonReport:
        """Run identical scenario schedule through Baseline and Aureon engines."""
        road_network = build_bangalore_network()
        hospitals = get_default_bangalore_hospitals()
        candidate_nodes = [
            (n.id, n.name, n.latitude, n.longitude)
            for n in road_network.nodes.values()
            if not n.is_station and not n.is_hospital
        ]

        generator = ScenarioGenerator(node_ids_with_coords=candidate_nodes, seed=seed)
        schedule = generator.generate_scenario_schedule(
            duration_minutes=duration_minutes,
            incident_rate_per_hour=incident_rate_per_hour,
        )

        baseline_fleet = create_default_bangalore_fleet()
        baseline_hospitals = copy.deepcopy(hospitals)
        baseline_engine = CitySimulationEngine(
            road_network=road_network,
            hospitals=baseline_hospitals,
            ambulances=baseline_fleet,
            strategy=NearestAvailableStrategy(),
        )
        baseline_schedule = copy.deepcopy(schedule)
        baseline_metrics = baseline_engine.run_scenario(
            schedule=baseline_schedule,
            duration_minutes=duration_minutes,
        )

        aureon_fleet = create_default_bangalore_fleet()
        aureon_hospitals = copy.deepcopy(hospitals)
        aureon_engine = CitySimulationEngine(
            road_network=road_network,
            hospitals=aureon_hospitals,
            ambulances=aureon_fleet,
            strategy=AureonDecisionEngine(),
        )
        aureon_schedule = copy.deepcopy(schedule)
        aureon_metrics = aureon_engine.run_scenario(
            schedule=aureon_schedule,
            duration_minutes=duration_minutes,
        )

        base_rt = baseline_metrics.mean_response_time_sec
        aur_rt = aureon_metrics.mean_response_time_sec
        rt_impr = ((base_rt - aur_rt) / base_rt * 100.0) if base_rt > 0 else 0.0

        base_crit_rt = baseline_metrics.critical_mean_response_time_sec
        aur_crit_rt = aureon_metrics.critical_mean_response_time_sec
        crit_impr = (
            ((base_crit_rt - aur_crit_rt) / base_crit_rt * 100.0)
            if base_crit_rt > 0
            else 0.0
        )

        comp_gain = (
            (aureon_metrics.critical_target_compliance_rate - baseline_metrics.critical_target_compliance_rate)
            * 100.0
        )
        match_gain = (
            (aureon_metrics.capability_match_rate - baseline_metrics.capability_match_rate)
            * 100.0
        )
        suit_gain = (
            (aureon_metrics.mean_hospital_suitability - baseline_metrics.mean_hospital_suitability)
            / max(baseline_metrics.mean_hospital_suitability, 0.01)
            * 100.0
        )
        dist_saved = (
            baseline_metrics.total_fleet_distance_km - aureon_metrics.total_fleet_distance_km
        )

        return ComparisonReport(
            baseline_metrics=baseline_metrics,
            aureon_metrics=aureon_metrics,
            duration_minutes=duration_minutes,
            incident_count=len(schedule),
            response_time_improvement_percent=rt_impr,
            critical_response_time_improvement_percent=crit_impr,
            target_compliance_delta_percent=comp_gain,
            capability_match_improvement_percent=match_gain,
            hospital_suitability_improvement_percent=suit_gain,
            fleet_distance_saved_km=dist_saved,
        )
