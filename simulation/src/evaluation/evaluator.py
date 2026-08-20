"""Evaluation and side-by-side comparison system for emergency response strategies."""

from __future__ import annotations

import copy
import logging
import math
import statistics
from dataclasses import dataclass, field
from typing import Any

from ..dispatch.aureon_intelligence import AureonDecisionEngine
from ..dispatch.baseline import NearestAvailableStrategy
from ..dispatch.predictive import AureonPredictiveDispatcher
from ..engine.city_engine import CitySimulationEngine, SimulationMetrics
from ..generators.incident_generator import ScenarioGenerator
from ..ml.data_pipeline import SimulationDataExtractor, TIME_WINDOW_SEC
from ..ml.demand_model import DemandPredictionModel
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


@dataclass
class MultiSeedReport:
    """Statistical aggregation across multiple simulation seeds."""

    num_seeds: int
    seeds_used: list[int]
    duration_minutes: float
    incident_rate_per_hour: float
    use_dynamic_traffic: bool
    use_dynamic_zones: bool

    # Baseline statistics
    baseline_rt_mean: float = 0.0
    baseline_rt_std: float = 0.0
    baseline_rt_ci_lower: float = 0.0
    baseline_rt_ci_upper: float = 0.0
    baseline_completed_mean: float = 0.0

    # Aureon statistics
    aureon_rt_mean: float = 0.0
    aureon_rt_std: float = 0.0
    aureon_rt_ci_lower: float = 0.0
    aureon_rt_ci_upper: float = 0.0
    aureon_completed_mean: float = 0.0

    # Improvement statistics
    improvement_rt_mean: float = 0.0
    improvement_rt_std: float = 0.0
    improvement_rt_ci_lower: float = 0.0
    improvement_rt_ci_upper: float = 0.0

    # Critical case statistics
    baseline_crit_rt_mean: float = 0.0
    aureon_crit_rt_mean: float = 0.0
    improvement_crit_rt_mean: float = 0.0

    # Raw per-seed results
    per_seed_results: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to serialized format."""
        return {
            "experiment_meta": {
                "num_seeds": self.num_seeds,
                "seeds_used": self.seeds_used,
                "duration_minutes": self.duration_minutes,
                "incident_rate_per_hour": self.incident_rate_per_hour,
                "dynamic_traffic": self.use_dynamic_traffic,
                "dynamic_zones": self.use_dynamic_zones,
            },
            "baseline_statistics": {
                "response_time_minutes": {
                    "mean": round(self.baseline_rt_mean, 2),
                    "std": round(self.baseline_rt_std, 2),
                    "ci_95_lower": round(self.baseline_rt_ci_lower, 2),
                    "ci_95_upper": round(self.baseline_rt_ci_upper, 2),
                },
                "completed_incidents_mean": round(self.baseline_completed_mean, 1),
                "critical_rt_mean_min": round(self.baseline_crit_rt_mean, 2),
            },
            "aureon_statistics": {
                "response_time_minutes": {
                    "mean": round(self.aureon_rt_mean, 2),
                    "std": round(self.aureon_rt_std, 2),
                    "ci_95_lower": round(self.aureon_rt_ci_lower, 2),
                    "ci_95_upper": round(self.aureon_rt_ci_upper, 2),
                },
                "completed_incidents_mean": round(self.aureon_completed_mean, 1),
                "critical_rt_mean_min": round(self.aureon_crit_rt_mean, 2),
            },
            "improvement_statistics": {
                "response_time_improvement_percent": {
                    "mean": round(self.improvement_rt_mean, 2),
                    "std": round(self.improvement_rt_std, 2),
                    "ci_95_lower": round(self.improvement_rt_ci_lower, 2),
                    "ci_95_upper": round(self.improvement_rt_ci_upper, 2),
                },
                "critical_rt_improvement_percent": round(self.improvement_crit_rt_mean, 2),
            },
            "per_seed_results": self.per_seed_results,
        }


class SimulationEvaluator:
    """Orchestrates controlled experiments to benchmark dispatch strategies."""

    @staticmethod
    def run_three_way_benchmark(
        num_seeds: int = 20,
        duration_minutes: float = 60.0,
        incident_rate_per_hour: float = 14.0,
        base_seed: int = 42,
        training_seeds: int = 15,
    ) -> ThreeWayReport:
        """Run full three-way benchmark with ML model training.

        Phase 1: Train demand model on `training_seeds` simulation runs.
        Phase 2: Evaluate all 3 strategies on `num_seeds` independent scenarios.

        Args:
            num_seeds: Number of evaluation seeds.
            duration_minutes: Simulation duration per run.
            incident_rate_per_hour: Poisson incident rate.
            base_seed: Starting seed.
            training_seeds: Number of seeds used for training data.
        """
        # Phase 1: Generate training data and train demand model
        logger.info("Phase 1: Training demand model on %d seeds...", training_seeds)
        train_road_network = build_bangalore_network()
        extractor = SimulationDataExtractor(train_road_network)
        training_data = extractor.generate_training_data(
            num_seeds=training_seeds,
            duration_minutes=duration_minutes,
            incident_rate_per_hour=incident_rate_per_hour,
        )

        demand_model = DemandPredictionModel()
        model_metrics = demand_model.train(training_data)
        logger.info("Demand model: RMSE=%.4f, R²=%.4f", model_metrics.rmse, model_metrics.r2)

        # Phase 2: Evaluate all strategies
        eval_seeds = [base_seed + i for i in range(num_seeds)]

        base_rts: list[float] = []
        heur_rts: list[float] = []
        pred_rts: list[float] = []
        base_crits: list[float] = []
        heur_crits: list[float] = []
        pred_crits: list[float] = []
        base_p90s: list[float] = []
        heur_p90s: list[float] = []
        pred_p90s: list[float] = []
        base_comps: list[int] = []
        heur_comps: list[int] = []
        pred_comps: list[int] = []
        base_utils: list[float] = []
        heur_utils: list[float] = []
        pred_utils: list[float] = []
        per_seed: list[dict[str, Any]] = []

        for seed in eval_seeds:
            road_network = build_bangalore_network()
            hospitals = get_default_bangalore_hospitals()
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

            # 1. Baseline (nearest available)
            bl_engine = CitySimulationEngine(
                road_network=copy.deepcopy(road_network),
                hospitals=copy.deepcopy(hospitals),
                ambulances=create_default_bangalore_fleet(),
                strategy=NearestAvailableStrategy(),
                enable_dynamic_traffic=True,
            )
            bl_metrics = bl_engine.run_scenario(
                schedule=copy.deepcopy(schedule), duration_minutes=duration_minutes,
            )

            # 2. Heuristic Aureon
            he_engine = CitySimulationEngine(
                road_network=copy.deepcopy(road_network),
                hospitals=copy.deepcopy(hospitals),
                ambulances=create_default_bangalore_fleet(),
                strategy=AureonDecisionEngine(),
                enable_dynamic_traffic=True,
            )
            he_metrics = he_engine.run_scenario(
                schedule=copy.deepcopy(schedule), duration_minutes=duration_minutes,
            )

            # 3. Predictive Aureon
            pred_dispatcher = AureonPredictiveDispatcher(
                demand_model=demand_model,
                feature_extractor=SimulationDataExtractor(copy.deepcopy(road_network)),
            )
            pred_engine = PredictionAwareEngine(
                predictive_dispatcher=pred_dispatcher,
                road_network=copy.deepcopy(road_network),
                hospitals=copy.deepcopy(hospitals),
                ambulances=create_default_bangalore_fleet(),
                enable_dynamic_traffic=True,
            )
            pred_metrics = pred_engine.run_scenario(
                schedule=copy.deepcopy(schedule), duration_minutes=duration_minutes,
            )

            # Collect metrics
            brt = bl_metrics.mean_response_time_sec / 60.0
            hrt = he_metrics.mean_response_time_sec / 60.0
            prt = pred_metrics.mean_response_time_sec / 60.0
            bcrit = bl_metrics.critical_mean_response_time_sec / 60.0
            hcrit = he_metrics.critical_mean_response_time_sec / 60.0
            pcrit = pred_metrics.critical_mean_response_time_sec / 60.0

            base_rts.append(brt)
            heur_rts.append(hrt)
            pred_rts.append(prt)
            base_crits.append(bcrit)
            heur_crits.append(hcrit)
            pred_crits.append(pcrit)
            base_p90s.append(bl_metrics.p90_response_time_sec / 60.0)
            heur_p90s.append(he_metrics.p90_response_time_sec / 60.0)
            pred_p90s.append(pred_metrics.p90_response_time_sec / 60.0)
            base_comps.append(bl_metrics.total_incidents_completed)
            heur_comps.append(he_metrics.total_incidents_completed)
            pred_comps.append(pred_metrics.total_incidents_completed)
            base_utils.append(bl_metrics.fleet_utilization_rate)
            heur_utils.append(he_metrics.fleet_utilization_rate)
            pred_utils.append(pred_metrics.fleet_utilization_rate)

            heur_imp = ((brt - hrt) / brt * 100.0) if brt > 0 else 0.0
            pred_imp = ((brt - prt) / brt * 100.0) if brt > 0 else 0.0
            per_seed.append({
                "seed": seed,
                "baseline_rt_min": round(brt, 2),
                "heuristic_rt_min": round(hrt, 2),
                "predictive_rt_min": round(prt, 2),
                "heuristic_improvement_pct": round(heur_imp, 2),
                "predictive_improvement_pct": round(pred_imp, 2),
            })

        def _mean(v: list[float]) -> float:
            return statistics.mean(v) if v else 0.0

        def _stdev(v: list[float]) -> float:
            return statistics.stdev(v) if len(v) > 1 else 0.0

        def _ci95(v: list[float]) -> tuple[float, float]:
            if len(v) < 2:
                m = _mean(v)
                return (m, m)
            m = statistics.mean(v)
            se = statistics.stdev(v) / math.sqrt(len(v))
            t_val = 1.96 if len(v) > 30 else 2.0
            return (m - t_val * se, m + t_val * se)

        base_mean = _mean(base_rts)
        heur_mean = _mean(heur_rts)
        pred_mean = _mean(pred_rts)

        return ThreeWayReport(
            num_seeds=num_seeds,
            seeds_used=eval_seeds,
            duration_minutes=duration_minutes,
            baseline_rt_mean_min=round(base_mean, 2),
            baseline_crit_rt_mean_min=round(_mean(base_crits), 2),
            baseline_p90_rt_min=round(_mean(base_p90s), 2),
            baseline_completed_mean=round(_mean(base_comps), 1),
            baseline_utilization_mean=round(_mean(base_utils), 4),
            heuristic_rt_mean_min=round(heur_mean, 2),
            heuristic_crit_rt_mean_min=round(_mean(heur_crits), 2),
            heuristic_p90_rt_min=round(_mean(heur_p90s), 2),
            heuristic_completed_mean=round(_mean(heur_comps), 1),
            heuristic_utilization_mean=round(_mean(heur_utils), 4),
            predictive_rt_mean_min=round(pred_mean, 2),
            predictive_crit_rt_mean_min=round(_mean(pred_crits), 2),
            predictive_p90_rt_min=round(_mean(pred_p90s), 2),
            predictive_completed_mean=round(_mean(pred_comps), 1),
            predictive_utilization_mean=round(_mean(pred_utils), 4),
            baseline_rt_ci=_ci95(base_rts),
            heuristic_rt_ci=_ci95(heur_rts),
            predictive_rt_ci=_ci95(pred_rts),
            heuristic_improvement_pct=round(
                ((base_mean - heur_mean) / base_mean * 100.0) if base_mean > 0 else 0.0, 2
            ),
            predictive_improvement_pct=round(
                ((base_mean - pred_mean) / base_mean * 100.0) if base_mean > 0 else 0.0, 2
            ),
            heuristic_crit_improvement_pct=round(
                ((_mean(base_crits) - _mean(heur_crits)) / max(_mean(base_crits), 0.01) * 100.0), 2
            ),
            predictive_crit_improvement_pct=round(
                ((_mean(base_crits) - _mean(pred_crits)) / max(_mean(base_crits), 0.01) * 100.0), 2
            ),
            demand_model_rmse=model_metrics.rmse,
            demand_model_r2=model_metrics.r2,
            demand_model_feature_importance=model_metrics.feature_importance,
            per_seed_results=per_seed,
        )

    @staticmethod
    def run_benchmark(
        duration_minutes: float = 60.0,
        incident_rate_per_hour: float = 14.0,
        seed: int = 42,
        enable_dynamic_traffic: bool = True,
        use_dynamic_zones: bool = True,
    ) -> ComparisonReport:
        """Run identical scenario schedule through Baseline and Aureon engines.

        Args:
            duration_minutes: Simulation duration.
            incident_rate_per_hour: Poisson rate for incident generation.
            seed: Random seed for reproducibility.
            enable_dynamic_traffic: If True, apply time-of-day congestion modulation.
            use_dynamic_zones: If True, apply time-of-day zone incident weighting.
        """
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
            use_dynamic_zones=use_dynamic_zones,
        )

        baseline_fleet = create_default_bangalore_fleet()
        baseline_hospitals = copy.deepcopy(hospitals)
        baseline_engine = CitySimulationEngine(
            road_network=copy.deepcopy(road_network),
            hospitals=baseline_hospitals,
            ambulances=baseline_fleet,
            strategy=NearestAvailableStrategy(),
            enable_dynamic_traffic=enable_dynamic_traffic,
        )
        baseline_schedule = copy.deepcopy(schedule)
        baseline_metrics = baseline_engine.run_scenario(
            schedule=baseline_schedule,
            duration_minutes=duration_minutes,
        )

        aureon_fleet = create_default_bangalore_fleet()
        aureon_hospitals = copy.deepcopy(hospitals)
        aureon_engine = CitySimulationEngine(
            road_network=copy.deepcopy(road_network),
            hospitals=aureon_hospitals,
            ambulances=aureon_fleet,
            strategy=AureonDecisionEngine(),
            enable_dynamic_traffic=enable_dynamic_traffic,
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

    @staticmethod
    def run_multi_seed_benchmark(
        num_seeds: int = 10,
        duration_minutes: float = 60.0,
        incident_rate_per_hour: float = 14.0,
        base_seed: int = 42,
        enable_dynamic_traffic: bool = True,
        use_dynamic_zones: bool = True,
    ) -> MultiSeedReport:
        """Run benchmark across multiple seeds with statistical aggregation.

        Args:
            num_seeds: Number of independent simulation runs.
            duration_minutes: Simulation duration per run.
            incident_rate_per_hour: Poisson rate for incident generation.
            base_seed: Starting seed (each run uses base_seed + i).
            enable_dynamic_traffic: Apply time-of-day congestion.
            use_dynamic_zones: Apply time-of-day zone weighting.
        """
        seeds = [base_seed + i for i in range(num_seeds)]
        baseline_rts_min: list[float] = []
        aureon_rts_min: list[float] = []
        improvement_pcts: list[float] = []
        baseline_completed: list[int] = []
        aureon_completed: list[int] = []
        baseline_crit_rts_min: list[float] = []
        aureon_crit_rts_min: list[float] = []
        per_seed: list[dict[str, Any]] = []

        for seed in seeds:
            report = SimulationEvaluator.run_benchmark(
                duration_minutes=duration_minutes,
                incident_rate_per_hour=incident_rate_per_hour,
                seed=seed,
                enable_dynamic_traffic=enable_dynamic_traffic,
                use_dynamic_zones=use_dynamic_zones,
            )

            base_rt_min = report.baseline_metrics.mean_response_time_sec / 60.0
            aur_rt_min = report.aureon_metrics.mean_response_time_sec / 60.0
            base_crit_min = report.baseline_metrics.critical_mean_response_time_sec / 60.0
            aur_crit_min = report.aureon_metrics.critical_mean_response_time_sec / 60.0

            baseline_rts_min.append(base_rt_min)
            aureon_rts_min.append(aur_rt_min)
            improvement_pcts.append(report.response_time_improvement_percent)
            baseline_completed.append(report.baseline_metrics.total_incidents_completed)
            aureon_completed.append(report.aureon_metrics.total_incidents_completed)
            baseline_crit_rts_min.append(base_crit_min)
            aureon_crit_rts_min.append(aur_crit_min)

            per_seed.append({
                "seed": seed,
                "baseline_rt_min": round(base_rt_min, 2),
                "aureon_rt_min": round(aur_rt_min, 2),
                "improvement_pct": round(report.response_time_improvement_percent, 2),
                "baseline_completed": report.baseline_metrics.total_incidents_completed,
                "aureon_completed": report.aureon_metrics.total_incidents_completed,
            })

        def _mean(vals: list[float]) -> float:
            return statistics.mean(vals) if vals else 0.0

        def _stdev(vals: list[float]) -> float:
            return statistics.stdev(vals) if len(vals) > 1 else 0.0

        def _ci95(vals: list[float]) -> tuple[float, float]:
            """95% confidence interval using t-distribution approximation."""
            if len(vals) < 2:
                m = _mean(vals)
                return (m, m)
            m = statistics.mean(vals)
            se = statistics.stdev(vals) / math.sqrt(len(vals))
            # t-value for 95% CI with n-1 degrees of freedom (approx 1.96 for n>30)
            t_val = 1.96 if len(vals) > 30 else 2.0
            return (m - t_val * se, m + t_val * se)

        import math

        baseline_rt_ci = _ci95(baseline_rts_min)
        aureon_rt_ci = _ci95(aureon_rts_min)
        improvement_rt_ci = _ci95(improvement_pcts)

        return MultiSeedReport(
            num_seeds=num_seeds,
            seeds_used=seeds,
            duration_minutes=duration_minutes,
            incident_rate_per_hour=incident_rate_per_hour,
            use_dynamic_traffic=enable_dynamic_traffic,
            use_dynamic_zones=use_dynamic_zones,
            baseline_rt_mean=round(_mean(baseline_rts_min), 2),
            baseline_rt_std=round(_stdev(baseline_rts_min), 2),
            baseline_rt_ci_lower=round(baseline_rt_ci[0], 2),
            baseline_rt_ci_upper=round(baseline_rt_ci[1], 2),
            baseline_completed_mean=round(_mean(baseline_completed), 1),
            aureon_rt_mean=round(_mean(aureon_rts_min), 2),
            aureon_rt_std=round(_stdev(aureon_rts_min), 2),
            aureon_rt_ci_lower=round(aureon_rt_ci[0], 2),
            aureon_rt_ci_upper=round(aureon_rt_ci[1], 2),
            aureon_completed_mean=round(_mean(aureon_completed), 1),
            improvement_rt_mean=round(_mean(improvement_pcts), 2),
            improvement_rt_std=round(_stdev(improvement_pcts), 2),
            improvement_rt_ci_lower=round(improvement_rt_ci[0], 2),
            improvement_rt_ci_upper=round(improvement_rt_ci[1], 2),
            baseline_crit_rt_mean=round(_mean(baseline_crit_rts_min), 2),
            aureon_crit_rt_mean=round(_mean(aureon_crit_rts_min), 2),
            improvement_crit_rt_mean=round(
                _mean([
                    (b - a) / b * 100.0 if b > 0 else 0.0
                    for b, a in zip(baseline_crit_rts_min, aureon_crit_rts_min)
                ]), 2
            ),
            per_seed_results=per_seed,
        )

    @staticmethod
    def run_four_way_benchmark(
        num_seeds: int = 20,
        duration_minutes: float = 60.0,
        incident_rate_per_hour: float = 14.0,
        base_seed: int = 42,
        training_seeds: int = 10,
    ) -> FourWayReport:
        """Run four-way benchmark: baseline, heuristic, predictive, optimization.

        Phase 1: Train demand model (XGBoost) on training_seeds runs.
        Phase 2: Evaluate all 4 strategies on num_seeds independent scenarios.
        """
        from ..dispatch.optimization import ORToolsDispatcher
        from ..ml.cluster_generator import ClusterIncidentGenerator
        from ..ml.demand_model import DemandPredictionModel
        from ..dispatch.predictive import AureonPredictiveDispatcher
        from ..models.events import get_default_bangalore_clusters

        # Phase 1: Train demand model
        logger.info("Phase 1: Training demand model on %d seeds...", training_seeds)
        train_network = build_bangalore_network()
        extractor = SimulationDataExtractor(train_network)
        training_data = extractor.generate_training_data(
            num_seeds=training_seeds,
            duration_minutes=duration_minutes,
            incident_rate_per_hour=incident_rate_per_hour,
        )
        demand_model = DemandPredictionModel()
        if training_data.size > 0:
            model_metrics = demand_model.train(training_data)
        else:
            from ..ml.demand_model import ModelMetrics
            model_metrics = ModelMetrics()

        # Phase 2: Evaluate
        logger.info("Phase 2: Evaluating 4 strategies on %d seeds...", num_seeds)
        eval_seeds = [base_seed + i for i in range(num_seeds)]

        # Collectors
        all_rts: dict[str, list[float]] = {
            "baseline": [], "heuristic": [], "predictive": [], "optim": [],
        }
        all_p90s: dict[str, list[float]] = {
            "baseline": [], "heuristic": [], "predictive": [], "optim": [],
        }
        all_crits: dict[str, list[float]] = {
            "baseline": [], "heuristic": [], "predictive": [], "optim": [],
        }
        all_comps: dict[str, list[int]] = {
            "baseline": [], "heuristic": [], "predictive": [], "optim": [],
        }
        per_seed: list[dict[str, Any]] = []

        for seed in eval_seeds:
            road_network = build_bangalore_network()
            hospitals = get_default_bangalore_hospitals()
            clusters = get_default_bangalore_clusters()

            # Generate cluster-based schedule
            gen = ClusterIncidentGenerator(road_network, clusters, seed=seed)
            cluster_schedule = gen.generate_schedule(
                duration_minutes=duration_minutes,
                incident_rate_per_hour=incident_rate_per_hour,
            )
            schedule = ClusterIncidentGenerator.to_simulation_schedule(cluster_schedule)

            strategies = {
                "baseline": NearestAvailableStrategy(),
                "heuristic": AureonDecisionEngine(),
                "optim": ORToolsDispatcher(),
            }

            results: dict[str, SimulationMetrics] = {}

            for name, strategy in strategies.items():
                engine = CitySimulationEngine(
                    road_network=copy.deepcopy(road_network),
                    hospitals=copy.deepcopy(hospitals),
                    ambulances=create_default_bangalore_fleet(),
                    strategy=strategy,
                    enable_dynamic_traffic=True,
                )
                metrics = engine.run_scenario(
                    schedule=copy.deepcopy(schedule),
                    duration_minutes=duration_minutes,
                )
                results[name] = metrics

            # Predictive strategy
            pred_dispatcher = AureonPredictiveDispatcher(
                demand_model=demand_model,
                feature_extractor=SimulationDataExtractor(copy.deepcopy(road_network)),
            )
            pred_engine = PredictionAwareEngine(
                predictive_dispatcher=pred_dispatcher,
                road_network=copy.deepcopy(road_network),
                hospitals=copy.deepcopy(hospitals),
                ambulances=create_default_bangalore_fleet(),
                enable_dynamic_traffic=True,
            )
            results["predictive"] = pred_engine.run_scenario(
                schedule=copy.deepcopy(schedule),
                duration_minutes=duration_minutes,
            )

            # Collect
            seed_results: dict[str, Any] = {"seed": seed}
            for name in ["baseline", "heuristic", "predictive", "optim"]:
                m = results[name]
                rt_min = m.mean_response_time_sec / 60.0
                all_rts[name].append(rt_min)
                all_p90s[name].append(m.p90_response_time_sec / 60.0)
                all_crits[name].append(m.critical_mean_response_time_sec / 60.0)
                all_comps[name].append(m.total_incidents_completed)
                seed_results[f"{name}_rt_min"] = round(rt_min, 2)

            per_seed.append(seed_results)

        # Aggregate
        return FourWayReport(
            num_seeds=num_seeds,
            seeds_used=eval_seeds,
            duration_minutes=duration_minutes,
            baseline_rt_mean=round(_mean(all_rts["baseline"]), 2),
            baseline_p90=round(_mean(all_p90s["baseline"]), 2),
            baseline_crit_rt=round(_mean(all_crits["baseline"]), 2),
            baseline_completed=round(_mean(all_comps["baseline"]), 1),
            heuristic_rt_mean=round(_mean(all_rts["heuristic"]), 2),
            heuristic_p90=round(_mean(all_p90s["heuristic"]), 2),
            heuristic_crit_rt=round(_mean(all_crits["heuristic"]), 2),
            heuristic_completed=round(_mean(all_comps["heuristic"]), 1),
            predictive_rt_mean=round(_mean(all_rts["predictive"]), 2),
            predictive_p90=round(_mean(all_p90s["predictive"]), 2),
            predictive_crit_rt=round(_mean(all_crits["predictive"]), 2),
            predictive_completed=round(_mean(all_comps["predictive"]), 1),
            optim_rt_mean=round(_mean(all_rts["optim"]), 2),
            optim_p90=round(_mean(all_p90s["optim"]), 2),
            optim_crit_rt=round(_mean(all_crits["optim"]), 2),
            optim_completed=round(_mean(all_comps["optim"]), 1),
            baseline_ci=_ci95(all_rts["baseline"]),
            heuristic_ci=_ci95(all_rts["heuristic"]),
            predictive_ci=_ci95(all_rts["predictive"]),
            optim_ci=_ci95(all_rts["optim"]),
            demand_model_rmse=model_metrics.rmse,
            demand_model_r2=model_metrics.r2,
            demand_model_feature_importance=model_metrics.feature_importance,
            per_seed_results=per_seed,
        )


@dataclass
class ThreeWayReport:
    """Three-way comparison: Baseline vs Heuristic Aureon vs Predictive Aureon."""

    baseline_rt_mean_min: float = 0.0
    baseline_crit_rt_mean_min: float = 0.0
    baseline_p90_rt_min: float = 0.0
    baseline_completed_mean: float = 0.0
    baseline_utilization_mean: float = 0.0

    heuristic_rt_mean_min: float = 0.0
    heuristic_crit_rt_mean_min: float = 0.0
    heuristic_p90_rt_min: float = 0.0
    heuristic_completed_mean: float = 0.0
    heuristic_utilization_mean: float = 0.0

    predictive_rt_mean_min: float = 0.0
    predictive_crit_rt_mean_min: float = 0.0
    predictive_p90_rt_min: float = 0.0
    predictive_completed_mean: float = 0.0
    predictive_utilization_mean: float = 0.0

    # CIs
    baseline_rt_ci: tuple[float, float] = (0.0, 0.0)
    heuristic_rt_ci: tuple[float, float] = (0.0, 0.0)
    predictive_rt_ci: tuple[float, float] = (0.0, 0.0)

    # Improvement vs baseline
    heuristic_improvement_pct: float = 0.0
    predictive_improvement_pct: float = 0.0
    heuristic_crit_improvement_pct: float = 0.0
    predictive_crit_improvement_pct: float = 0.0

    # Model metrics
    demand_model_rmse: float = 0.0
    demand_model_r2: float = 0.0
    demand_model_feature_importance: dict[str, float] = field(default_factory=dict)

    num_seeds: int = 0
    seeds_used: list[int] = field(default_factory=list)
    duration_minutes: float = 0.0

    per_seed_results: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_meta": {
                "num_seeds": self.num_seeds,
                "seeds_used": self.seeds_used,
                "duration_minutes": self.duration_minutes,
            },
            "baseline": {
                "rt_mean_min": round(self.baseline_rt_mean_min, 2),
                "rt_ci": (round(self.baseline_rt_ci[0], 2), round(self.baseline_rt_ci[1], 2)),
                "critical_rt_min": round(self.baseline_crit_rt_mean_min, 2),
                "p90_rt_min": round(self.baseline_p90_rt_min, 2),
                "completed_mean": round(self.baseline_completed_mean, 1),
                "utilization_mean": round(self.baseline_utilization_mean * 100, 1),
            },
            "heuristic_aureon": {
                "rt_mean_min": round(self.heuristic_rt_mean_min, 2),
                "rt_ci": (round(self.heuristic_rt_ci[0], 2), round(self.heuristic_rt_ci[1], 2)),
                "critical_rt_min": round(self.heuristic_crit_rt_mean_min, 2),
                "p90_rt_min": round(self.heuristic_p90_rt_min, 2),
                "completed_mean": round(self.heuristic_completed_mean, 1),
                "utilization_mean": round(self.heuristic_utilization_mean * 100, 1),
                "improvement_vs_baseline_pct": round(self.heuristic_improvement_pct, 2),
                "crit_improvement_pct": round(self.heuristic_crit_improvement_pct, 2),
            },
            "predictive_aureon": {
                "rt_mean_min": round(self.predictive_rt_mean_min, 2),
                "rt_ci": (round(self.predictive_rt_ci[0], 2), round(self.predictive_rt_ci[1], 2)),
                "critical_rt_min": round(self.predictive_crit_rt_mean_min, 2),
                "p90_rt_min": round(self.predictive_p90_rt_min, 2),
                "completed_mean": round(self.predictive_completed_mean, 1),
                "utilization_mean": round(self.predictive_utilization_mean * 100, 1),
                "improvement_vs_baseline_pct": round(self.predictive_improvement_pct, 2),
                "crit_improvement_pct": round(self.predictive_crit_improvement_pct, 2),
            },
            "demand_model": {
                "rmse": round(self.demand_model_rmse, 4),
                "r2": round(self.demand_model_r2, 4),
                "feature_importance_top10": {
                    k: round(v, 4) for k, v in sorted(
                        self.demand_model_feature_importance.items(), key=lambda x: -x[1]
                    )[:10]
                },
            },
            "per_seed_results": self.per_seed_results,
        }


class PredictionAwareEngine(CitySimulationEngine):
    """Extended engine that integrates predictive demand forecasting.

    Calls the predictive dispatcher's forecast and repositioning at
    each time step, then uses the predictive dispatch for decisions.
    """

    def __init__(
        self,
        predictive_dispatcher: AureonPredictiveDispatcher,
        **kwargs: Any,
    ) -> None:
        super().__init__(strategy=predictive_dispatcher, **kwargs)
        self.predictive_dispatcher = predictive_dispatcher
        self._forecast_interval_sec = TIME_WINDOW_SEC
        self._last_forecast_time = -TIME_WINDOW_SEC

    def step(self, new_incidents: list | None = None) -> None:  # type: ignore[override]
        """Override step to add forecasting and repositioning."""
        # Run forecast periodically
        if (self.sim_time_seconds - self._last_forecast_time) >= self._forecast_interval_sec:
            self._last_forecast_time = self.sim_time_seconds
            try:
                forecast = self.predictive_dispatcher.forecast_demand(
                    sim_time_sec=self.sim_time_seconds,
                    ambulances=self.ambulances,
                    hospitals=self.hospitals,
                    active_incidents=self.active_incidents,
                )
                # Execute repositioning
                commands = self.predictive_dispatcher.reposition_idle_ambulances(
                    ambulances=self.ambulances,
                    road_network=self.road_network,
                    forecast=forecast,
                )
                for cmd in commands:
                    amb = next((a for a in self.ambulances if a.id == cmd.ambulance_id), None)
                    if amb and amb.is_available:
                        amb.current_node_id = cmd.target_node_id
                        target_node = self.road_network.nodes.get(cmd.target_node_id)
                        if target_node:
                            amb.latitude = target_node.latitude
                            amb.longitude = target_node.longitude
            except Exception as e:
                logger.warning("Predictive forecast failed: %s", e)

        # Call parent step for normal dispatch
        super().step(new_incidents=new_incidents)


@dataclass
class FourWayReport:
    """Four-way comparison: Baseline vs Heuristic vs Predictive vs Optimization."""

    num_seeds: int = 0
    seeds_used: list[int] = field(default_factory=list)
    duration_minutes: float = 0.0

    # Strategy metrics
    baseline_rt_mean: float = 0.0
    baseline_p90: float = 0.0
    baseline_crit_rt: float = 0.0
    baseline_completed: float = 0.0

    heuristic_rt_mean: float = 0.0
    heuristic_p90: float = 0.0
    heuristic_crit_rt: float = 0.0
    heuristic_completed: float = 0.0

    predictive_rt_mean: float = 0.0
    predictive_p90: float = 0.0
    predictive_crit_rt: float = 0.0
    predictive_completed: float = 0.0

    optim_rt_mean: float = 0.0
    optim_p90: float = 0.0
    optim_crit_rt: float = 0.0
    optim_completed: float = 0.0

    # CIs
    baseline_ci: tuple[float, float] = (0.0, 0.0)
    heuristic_ci: tuple[float, float] = (0.0, 0.0)
    predictive_ci: tuple[float, float] = (0.0, 0.0)
    optim_ci: tuple[float, float] = (0.0, 0.0)

    # Demand model (auxiliary)
    demand_model_rmse: float = 0.0
    demand_model_r2: float = 0.0
    demand_model_feature_importance: dict[str, float] = field(default_factory=dict)

    per_seed_results: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_meta": {
                "num_seeds": self.num_seeds,
                "seeds_used": self.seeds_used,
                "duration_minutes": self.duration_minutes,
            },
            "baseline": {
                "rt_mean_min": round(self.baseline_rt_mean, 2),
                "rt_ci": (round(self.baseline_ci[0], 2), round(self.baseline_ci[1], 2)),
                "p90_min": round(self.baseline_p90, 2),
                "critical_rt_min": round(self.baseline_crit_rt, 2),
                "completed_mean": round(self.baseline_completed, 1),
            },
            "heuristic_aureon": {
                "rt_mean_min": round(self.heuristic_rt_mean, 2),
                "rt_ci": (round(self.heuristic_ci[0], 2), round(self.heuristic_ci[1], 2)),
                "p90_min": round(self.heuristic_p90, 2),
                "critical_rt_min": round(self.heuristic_crit_rt, 2),
                "completed_mean": round(self.heuristic_completed, 1),
                "improvement_pct": round(self._improvement(self.heuristic_rt_mean), 2),
            },
            "predictive_aureon": {
                "rt_mean_min": round(self.predictive_rt_mean, 2),
                "rt_ci": (round(self.predictive_ci[0], 2), round(self.predictive_ci[1], 2)),
                "p90_min": round(self.predictive_p90, 2),
                "critical_rt_min": round(self.predictive_crit_rt, 2),
                "completed_mean": round(self.predictive_completed, 1),
                "improvement_pct": round(self._improvement(self.predictive_rt_mean), 2),
            },
            "optimization_aureon": {
                "rt_mean_min": round(self.optim_rt_mean, 2),
                "rt_ci": (round(self.optim_ci[0], 2), round(self.optim_ci[1], 2)),
                "p90_min": round(self.optim_p90, 2),
                "critical_rt_min": round(self.optim_crit_rt, 2),
                "completed_mean": round(self.optim_completed, 1),
                "improvement_pct": round(self._improvement(self.optim_rt_mean), 2),
            },
            "demand_model": {
                "rmse": round(self.demand_model_rmse, 4),
                "r2": round(self.demand_model_r2, 4),
                "role": "auxiliary_signal_not_dispatch_control",
                "feature_importance_top5": {
                    k: round(v, 4) for k, v in sorted(
                        self.demand_model_feature_importance.items(), key=lambda x: -x[1]
                    )[:5]
                },
            },
            "per_seed_results": self.per_seed_results,
        }

    def _improvement(self, rt_mean: float) -> float:
        return ((self.baseline_rt_mean - rt_mean) / self.baseline_rt_mean * 100.0) if self.baseline_rt_mean > 0 else 0.0


def _mean(v: list[float]) -> float:
    return statistics.mean(v) if v else 0.0

def _stdev(v: list[float]) -> float:
    return statistics.stdev(v) if len(v) > 1 else 0.0

def _ci95(v: list[float]) -> tuple[float, float]:
    if len(v) < 2:
        m = _mean(v)
        return (m, m)
    m = statistics.mean(v)
    se = statistics.stdev(v) / math.sqrt(len(v))
    t_val = 1.96 if len(v) > 30 else 2.0
    return (m - t_val * se, m + t_val * se)
