"""Adaptive Aureon Policy — Scenario-Aware Emergency Dispatch.

Selects dispatch strategy based on detected city conditions.
Falls back to proximity-first hybrid in normal conditions.
Activates specialized modes when they provide measurable value.

No future information is used — only current observable state.
No hyperparameter tuning against final benchmarks.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any

from ..generators.incident_generator import Incident, IncidentSeverity
from ..models.ambulance import Ambulance, AmbulanceCapability, AmbulanceStatus
from ..models.hospital import Hospital
from ..network.road_graph import RoadNetwork, RouteResult
from .base import BaseDispatchStrategy, DispatchDecision
from .hybrid_intelligence import HybridAureonStrategy, HybridDispatchConfig
from .scenario_detector import DispatchMode, ScenarioDetector, ScenarioState

logger = logging.getLogger("aureon.dispatch.adaptive")

SEVERITY_WEIGHTS = {
    IncidentSeverity.CRITICAL: 3.0,
    IncidentSeverity.HIGH: 2.0,
    IncidentSeverity.MODERATE: 1.5,
    IncidentSeverity.LOW: 1.0,
}
CAPABILITY_PENALTY_SEC = 300.0


@dataclass
class BatchAssignment:
    """A single assignment from batch optimization."""

    incident_id: str
    ambulance_id: str
    hospital_id: str | None
    eta_sec: float
    severity_weight: float
    is_capability_matched: bool


class AdaptiveAureonStrategy(BaseDispatchStrategy):
    """Adaptive dispatch strategy that switches mode based on city conditions.

    Normal conditions -> proximity-first hybrid (no regression)
    Resource scarcity -> coverage-aware dispatch
    Multiple incidents -> batch global optimization (OR-Tools)
    Hospital congestion -> dynamic destination selection
    Road disruption -> reroute and reassess

    Design principle: Aureon only becomes "intelligent" when intelligence
    provides measurable value. In normal conditions, it matches baseline.
    """

    def __init__(
        self,
        name: str = "Adaptive Aureon Intelligence",
        hybrid_config: HybridDispatchConfig | None = None,
    ) -> None:
        super().__init__(name=name)
        self._hybrid = HybridAureonStrategy(
            config=hybrid_config or HybridDispatchConfig(enable_coverage_analysis=True),
        )
        self._detector: ScenarioDetector | None = None
        self._last_mode: DispatchMode = DispatchMode.NORMAL
        self._mode_counts: dict[str, int] = {}
        self._batch_assignments: dict[str, BatchAssignment] = {}
        self._total_dispatches: int = 0
        self._batch_dispatches: int = 0

    @property
    def supports_batch(self) -> bool:
        return True

    def _ensure_detector(
        self,
        all_ambulances: list[Ambulance] | None,
        road_network: RoadNetwork,
    ) -> ScenarioDetector:
        if self._detector is None:
            self._detector = ScenarioDetector(
                network=road_network,
                all_ambulances=all_ambulances or [],
            )
        return self._detector

    def dispatch(
        self,
        incident: Incident,
        available_ambulances: list[Ambulance],
        hospitals: list[Hospital],
        road_network: RoadNetwork,
        all_ambulances: list[Ambulance] | None = None,
    ) -> DispatchDecision:
        self._total_dispatches += 1

        if incident.id in self._batch_assignments:
            batch = self._batch_assignments.pop(incident.id)
            return self._build_batch_decision(
                batch, incident, available_ambulances, hospitals, road_network,
            )

        detector = self._ensure_detector(all_ambulances, road_network)
        state = detector.detect(
            available_ambulances=available_ambulances,
            pending_incidents=[incident],
            hospitals=hospitals,
            road_network=road_network,
        )
        mode = state.recommended_mode()
        self._last_mode = mode
        self._mode_counts[mode.value] = self._mode_counts.get(mode.value, 0) + 1

        if mode == DispatchMode.NORMAL:
            return self._dispatch_hybrid(incident, available_ambulances, hospitals, road_network, all_ambulances)
        elif mode == DispatchMode.HIGH_DEMAND:
            return self._dispatch_coverage_aware(incident, available_ambulances, hospitals, road_network, all_ambulances)
        elif mode == DispatchMode.FLEET_SCARCITY:
            return self._dispatch_scarcity(incident, available_ambulances, hospitals, road_network, all_ambulances)
        elif mode == DispatchMode.CRITICAL_SURGE:
            return self._dispatch_critical_surge(incident, available_ambulances, hospitals, road_network, all_ambulances)
        elif mode == DispatchMode.HOSPITAL_CONGESTION:
            return self._dispatch_hospital_aware(incident, available_ambulances, hospitals, road_network, all_ambulances)
        elif mode == DispatchMode.ROAD_DISRUPTION:
            return self._dispatch_disruption_aware(incident, available_ambulances, hospitals, road_network, all_ambulances)
        elif mode == DispatchMode.SPATIAL_HOTSPOT:
            return self._dispatch_coverage_aware(incident, available_ambulances, hospitals, road_network, all_ambulances)
        else:
            return self._dispatch_hybrid(incident, available_ambulances, hospitals, road_network, all_ambulances)

    def dispatch_batch(
        self,
        incidents: list[Incident],
        available_ambulances: list[Ambulance],
        hospitals: list[Hospital],
        road_network: RoadNetwork,
        all_ambulances: list[Ambulance] | None = None,
    ) -> list[tuple[str, DispatchDecision]]:
        if len(incidents) < 2 or len(available_ambulances) < 2:
            return []

        detector = self._ensure_detector(all_ambulances, road_network)
        state = detector.detect(
            available_ambulances=available_ambulances,
            pending_incidents=incidents,
            hospitals=hospitals,
            road_network=road_network,
        )
        mode = state.recommended_mode()

        if mode not in (DispatchMode.MULTI_INCIDENT, DispatchMode.CRITICAL_SURGE, DispatchMode.FLEET_SCARCITY):
            return []

        n_inc = len(incidents)
        n_amb = len(available_ambulances)
        INF = 1e9

        eta_matrix: list[list[float]] = []
        cap_matrix: list[list[bool]] = []

        for amb in available_ambulances:
            amb_etas: list[float] = []
            amb_caps: list[bool] = []
            for inc in incidents:
                route = road_network.calculate_route(
                    start_node_id=amb.current_node_id,
                    end_node_id=inc.location_node_id,
                    weight="time",
                )
                if route.found:
                    amb_etas.append(route.estimated_time_seconds)
                    amb_caps.append(amb.can_handle(inc.required_capability))
                else:
                    amb_etas.append(INF)
                    amb_caps.append(False)
            eta_matrix.append(amb_etas)
            cap_matrix.append(amb_caps)

        assignments = self._solve_assignment_or_tools(
            available_ambulances, incidents, eta_matrix, cap_matrix, hospitals, road_network,
        )

        if not assignments:
            return []

        self._batch_assignments = {a.incident_id: a for a in assignments}
        self._batch_dispatches += len(assignments)

        results: list[tuple[str, DispatchDecision]] = []
        for batch in assignments:
            inc = next(i for i in incidents if i.id == batch.incident_id)
            decision = self._build_batch_decision(batch, inc, available_ambulances, hospitals, road_network)
            results.append((batch.incident_id, decision))

        return results

    def _solve_assignment_or_tools(
        self,
        ambulances: list[Ambulance],
        incidents: list[Incident],
        eta_matrix: list[list[float]],
        cap_matrix: list[list[bool]],
        hospitals: list[Hospital],
        road_network: RoadNetwork,
    ) -> list[BatchAssignment]:
        try:
            from ortools.linear_solver import pywraplp
        except ImportError:
            logger.warning("OR-Tools not available, falling back to greedy dispatch")
            return []

        solver = pywraplp.Solver.CreateSolver("SCIP")
        if solver is None:
            return []

        n_amb = len(ambulances)
        n_inc = len(incidents)

        # x[i,j] = 1 if ambulance i assigned to incident j
        x: list[list[Any]] = []
        for i in range(n_amb):
            row = []
            for j in range(n_inc):
                row.append(solver.IntVar(0, 1, f"x_{i}_{j}"))
            x.append(row)

        # u[j] = 1 if incident j remains unassigned (penalty variable)
        u: list[Any] = []
        for j in range(n_inc):
            u.append(solver.IntVar(0, 1, f"u_{j}"))

        # Each ambulance gets at most 1 incident
        for i in range(n_amb):
            solver.Add(sum(x[i][j] for j in range(n_inc)) <= 1)

        # Each incident is either assigned to exactly 1 ambulance OR unassigned
        UNASSIGNED_PENALTY_SEC = 1800.0
        for j in range(n_inc):
            solver.Add(sum(x[i][j] for i in range(n_amb)) + u[j] == 1)

        objective_terms = []
        for i in range(n_amb):
            for j in range(n_inc):
                eta = eta_matrix[i][j]
                if eta >= 1e8:
                    objective_terms.append(1e6 * x[i][j])
                    continue

                severity_w = SEVERITY_WEIGHTS.get(incidents[j].severity, 1.0)
                cap_penalty = 0.0 if cap_matrix[i][j] else CAPABILITY_PENALTY_SEC
                cost = severity_w * (eta + cap_penalty)
                objective_terms.append(cost * x[i][j])

        for j in range(n_inc):
            severity_w = SEVERITY_WEIGHTS.get(incidents[j].severity, 1.0)
            objective_terms.append(severity_w * UNASSIGNED_PENALTY_SEC * u[j])

        solver.Minimize(solver.Sum(objective_terms))

        status = solver.Solve()
        if status != pywraplp.Solver.OPTIMAL and status != pywraplp.Solver.FEASIBLE:
            return []

        assignments: list[BatchAssignment] = []
        for j in range(n_inc):
            if u[j].solution_value() > 0.5:
                continue
            for i in range(n_amb):
                if x[i][j].solution_value() > 0.5:
                    eta = eta_matrix[i][j]
                    sev_w = SEVERITY_WEIGHTS.get(incidents[j].severity, 1.0)
                    hosp_id, _ = self._select_hospital_for_incident(
                        incidents[j], hospitals, road_network,
                    )
                    assignments.append(BatchAssignment(
                        incident_id=incidents[j].id,
                        ambulance_id=ambulances[i].id,
                        hospital_id=hosp_id,
                        eta_sec=eta,
                        severity_weight=sev_w,
                        is_capability_matched=cap_matrix[i][j],
                    ))
                    break

        return assignments

    def _select_hospital_for_incident(
        self,
        incident: Incident,
        hospitals: list[Hospital],
        road_network: RoadNetwork,
    ) -> tuple[str | None, float]:
        if not hospitals:
            return None, 0.0

        is_critical = incident.severity in (IncidentSeverity.CRITICAL, IncidentSeverity.HIGH)
        best_id = None
        best_score = -float("inf")

        for hosp in hospitals:
            route = road_network.calculate_route(
                start_node_id=incident.location_node_id,
                end_node_id=hosp.node_id,
                weight="time",
            )
            if not route.found:
                continue

            suitability = hosp.calculate_suitability_score(
                incident.category.value, is_critical=is_critical,
            )
            hosp_eta = route.estimated_time_seconds
            time_factor = 1.0 / (1.0 + math.log1p(hosp_eta / 300.0))
            capacity_ratio = 1.0 - (hosp.occupied_er_beds / max(hosp.total_er_beds, 1))
            score = suitability * time_factor * (0.5 + 0.5 * capacity_ratio)

            if score > best_score:
                best_score = score
                best_id = hosp.id

        return best_id, best_score

    def _build_batch_decision(
        self,
        batch: BatchAssignment,
        incident: Incident,
        available_ambulances: list[Ambulance],
        hospitals: list[Hospital],
        road_network: RoadNetwork,
    ) -> DispatchDecision:
        amb = next((a for a in available_ambulances if a.id == batch.ambulance_id), None)
        if amb is None:
            return self._dispatch_hybrid(incident, available_ambulances, hospitals, road_network, None)

        route = road_network.calculate_route(
            start_node_id=amb.current_node_id,
            end_node_id=incident.location_node_id,
            weight="time",
        )

        hosp_route = None
        hosp_eta = 0.0
        if batch.hospital_id:
            hosp_node = next((h.node_id for h in hospitals if h.id == batch.hospital_id), None)
            if hosp_node:
                hosp_route = road_network.calculate_route(
                    start_node_id=incident.location_node_id,
                    end_node_id=hosp_node,
                    weight="time",
                )
                if hosp_route.found:
                    hosp_eta = hosp_route.estimated_time_seconds

        is_critical = incident.severity in (IncidentSeverity.CRITICAL, IncidentSeverity.HIGH)

        return DispatchDecision(
            ambulance_id=amb.id,
            target_hospital_id=batch.hospital_id,
            scene_route=route if route.found else None,
            hospital_route=hosp_route,
            priority_level=1 if is_critical else 2,
            rationale=(
                f"Batch optimized: {amb.callsign} [{amb.capability.value}] "
                f"ETA={batch.eta_sec/60:.1f}m (severity_w={batch.severity_weight:.1f}, "
                f"cap_match={batch.is_capability_matched})"
            ),
            estimated_scene_eta_sec=batch.eta_sec,
            estimated_hospital_eta_sec=hosp_eta,
            metadata={
                "mode": "batch_optimization",
                "severity_weight": batch.severity_weight,
                "is_capability_matched": batch.is_capability_matched,
            },
        )

    # === Mode-specific dispatch strategies ===

    def _dispatch_hybrid(
        self,
        incident: Incident,
        available: list[Ambulance],
        hospitals: list[Hospital],
        net: RoadNetwork,
        all_amb: list[Ambulance] | None,
    ) -> DispatchDecision:
        return self._hybrid.dispatch(incident, available, hospitals, net, all_amb)

    def _dispatch_coverage_aware(
        self,
        incident: Incident,
        available: list[Ambulance],
        hospitals: list[Hospital],
        net: RoadNetwork,
        all_amb: list[Ambulance] | None,
    ) -> DispatchDecision:
        if not available:
            return DispatchDecision(ambulance_id=None, target_hospital_id=None, rationale="No available ambulances")

        candidates: list[tuple[Ambulance, float, RouteResult]] = []
        for amb in available:
            route = net.calculate_route(amb.current_node_id, incident.location_node_id, "time")
            if route.found:
                candidates.append((amb, route.estimated_time_seconds, route))

        if not candidates:
            return DispatchDecision(ambulance_id=None, target_hospital_id=None, rationale="No reachable ambulance")

        candidates.sort(key=lambda c: c[1])
        nearest_amb, nearest_eta, nearest_route = candidates[0]

        is_critical = incident.severity in (IncidentSeverity.CRITICAL, IncidentSeverity.HIGH)

        if is_critical:
            return self._dispatch_hybrid(incident, available, hospitals, net, all_amb)

        if len(candidates) >= 2:
            from .coverage import FleetCoverageAnalyzer
            analyzer = FleetCoverageAnalyzer(
                coverage_threshold_sec=900.0, gap_penalty_threshold_sec=1200.0,
            )
            impact_nearest = analyzer.assess_dispatch_impact(
                nearest_amb, available, all_amb or available, net,
            )
            second_amb, second_eta, second_route = candidates[1]
            impact_second = analyzer.assess_dispatch_impact(
                second_amb, available, all_amb or available, net,
            )

            if (impact_nearest.creates_gap
                    and not impact_second.creates_gap
                    and second_eta <= nearest_eta * 1.3):
                chosen = second_amb
                chosen_route = second_route
                chosen_eta = second_eta
                reason = "coverage-aware: avoided gap"
            else:
                chosen = nearest_amb
                chosen_route = nearest_route
                chosen_eta = nearest_eta
                reason = "nearest (coverage acceptable)"
        else:
            chosen = nearest_amb
            chosen_route = nearest_route
            chosen_eta = nearest_eta
            reason = "nearest (only candidate)"

        best_hospital, best_hosp_route, hosp_eta = self._select_hospital(
            incident, hospitals, net,
        )

        matched = chosen.can_handle(incident.required_capability)

        return DispatchDecision(
            ambulance_id=chosen.id,
            target_hospital_id=best_hospital.id if best_hospital else None,
            scene_route=chosen_route,
            hospital_route=best_hosp_route,
            priority_level=1 if is_critical else 2,
            rationale=(
                f"Coverage-aware: {chosen.callsign} [{chosen.capability.value}] "
                f"ETA={chosen_eta/60:.1f}m. {reason}"
            ),
            estimated_scene_eta_sec=chosen_eta,
            estimated_hospital_eta_sec=hosp_eta,
            metadata={"mode": "coverage_aware", "decision_reason": reason},
        )

    def _dispatch_scarcity(
        self,
        incident: Incident,
        available: list[Ambulance],
        hospitals: list[Hospital],
        net: RoadNetwork,
        all_amb: list[Ambulance] | None,
    ) -> DispatchDecision:
        if not available:
            return DispatchDecision(ambulance_id=None, target_hospital_id=None, rationale="Fleet exhausted")

        needs_als = incident.required_capability in (AmbulanceCapability.ALS, AmbulanceCapability.MICU)
        is_critical = incident.severity in (IncidentSeverity.CRITICAL, IncidentSeverity.HIGH)

        candidates: list[tuple[Ambulance, float, RouteResult]] = []
        for amb in available:
            route = net.calculate_route(amb.current_node_id, incident.location_node_id, "time")
            if route.found:
                candidates.append((amb, route.estimated_time_seconds, route))

        if not candidates:
            return DispatchDecision(ambulance_id=None, target_hospital_id=None, rationale="No reachable ambulance")

        candidates.sort(key=lambda c: c[1])

        if is_critical and needs_als:
            als_candidates = [(a, e, r) for a, e, r in candidates if a.can_handle(incident.required_capability)]
            if als_candidates:
                chosen_amb, chosen_eta, chosen_route = als_candidates[0]
                reason = "scarce-critical: nearest ALS"
            else:
                chosen_amb, chosen_eta, chosen_route = candidates[0]
                reason = "scarce-critical: no ALS available, nearest used"
        elif is_critical:
            chosen_amb, chosen_eta, chosen_route = candidates[0]
            reason = "scarce-critical: nearest"
        else:
            from .coverage import FleetCoverageAnalyzer
            analyzer = FleetCoverageAnalyzer(
                coverage_threshold_sec=900.0, gap_penalty_threshold_sec=1200.0,
            )
            best_choice = candidates[0]
            best_impact = analyzer.assess_dispatch_impact(
                best_choice[0], available, all_amb or available, net,
            )

            for amb, eta, route in candidates[1:]:
                impact = analyzer.assess_dispatch_impact(amb, available, all_amb or available, net)
                if (not impact.creates_gap and best_impact.creates_gap) or \
                   (impact.creates_gap == best_impact.creates_gap and eta < best_choice[1]):
                    best_choice = (amb, eta, route)
                    best_impact = impact

            chosen_amb, chosen_eta, chosen_route = best_choice
            reason = "scarce: coverage-preserved" if best_impact.creates_gap else "scarce: nearest"

        best_hospital, best_hosp_route, hosp_eta = self._select_hospital(
            incident, hospitals, net,
        )

        matched = chosen_amb.can_handle(incident.required_capability)

        return DispatchDecision(
            ambulance_id=chosen_amb.id,
            target_hospital_id=best_hospital.id if best_hospital else None,
            scene_route=chosen_route,
            hospital_route=best_hosp_route,
            priority_level=1 if is_critical else 2,
            rationale=(
                f"Fleet scarcity: {chosen_amb.callsign} [{chosen_amb.capability.value}] "
                f"ETA={chosen_eta/60:.1f}m. {reason}"
            ),
            estimated_scene_eta_sec=chosen_eta,
            estimated_hospital_eta_sec=hosp_eta,
            metadata={"mode": "fleet_scarcity", "decision_reason": reason},
        )

    def _dispatch_critical_surge(
        self,
        incident: Incident,
        available: list[Ambulance],
        hospitals: list[Hospital],
        net: RoadNetwork,
        all_amb: list[Ambulance] | None,
    ) -> DispatchDecision:
        if not available:
            return DispatchDecision(ambulance_id=None, target_hospital_id=None, rationale="Fleet exhausted in critical surge")

        needs_als = incident.required_capability in (AmbulanceCapability.ALS, AmbulanceCapability.MICU)

        candidates: list[tuple[Ambulance, float, RouteResult]] = []
        for amb in available:
            route = net.calculate_route(amb.current_node_id, incident.location_node_id, "time")
            if route.found:
                candidates.append((amb, route.estimated_time_seconds, route))

        if not candidates:
            return DispatchDecision(ambulance_id=None, target_hospital_id=None, rationale="No reachable ambulance")

        candidates.sort(key=lambda c: c[1])

        if needs_als:
            als_candidates = [(a, e, r) for a, e, r in candidates if a.can_handle(incident.required_capability)]
            if als_candidates:
                best_als = als_candidates[0]
                nearest = candidates[0]
                penalty_pct = (best_als[1] - nearest[1]) / max(nearest[1], 1.0)
                if penalty_pct <= 0.25:
                    chosen_amb, chosen_eta, chosen_route = best_als
                    reason = f"critical-surge: ALS override (penalty={penalty_pct:.1%})"
                else:
                    chosen_amb, chosen_eta, chosen_route = nearest
                    reason = f"critical-surge: nearest (ALS penalty={penalty_pct:.1%} too high)"
            else:
                chosen_amb, chosen_eta, chosen_route = candidates[0]
                reason = "critical-surge: no ALS, nearest BLS"
        else:
            chosen_amb, chosen_eta, chosen_route = candidates[0]
            reason = "critical-surge: nearest"

        best_hospital, best_hosp_route, hosp_eta = self._select_hospital(
            incident, hospitals, net,
        )

        return DispatchDecision(
            ambulance_id=chosen_amb.id,
            target_hospital_id=best_hospital.id if best_hospital else None,
            scene_route=chosen_route,
            hospital_route=best_hosp_route,
            priority_level=1,
            rationale=(
                f"Critical surge: {chosen_amb.callsign} [{chosen_amb.capability.value}] "
                f"ETA={chosen_eta/60:.1f}m. {reason}"
            ),
            estimated_scene_eta_sec=chosen_eta,
            estimated_hospital_eta_sec=hosp_eta,
            metadata={"mode": "critical_surge", "decision_reason": reason},
        )

    def _dispatch_hospital_aware(
        self,
        incident: Incident,
        available: list[Ambulance],
        hospitals: list[Hospital],
        net: RoadNetwork,
        all_amb: list[Ambulance] | None,
    ) -> DispatchDecision:
        if not available:
            return DispatchDecision(ambulance_id=None, target_hospital_id=None, rationale="No available ambulances")

        candidates: list[tuple[Ambulance, float, RouteResult]] = []
        for amb in available:
            route = net.calculate_route(amb.current_node_id, incident.location_node_id, "time")
            if route.found:
                candidates.append((amb, route.estimated_time_seconds, route))

        if not candidates:
            return DispatchDecision(ambulance_id=None, target_hospital_id=None, rationale="No reachable ambulance")

        candidates.sort(key=lambda c: c[1])
        nearest_amb, nearest_eta, nearest_route = candidates[0]

        available_hospitals = [h for h in hospitals if h.occupied_er_beds < h.total_er_beds]
        if not available_hospitals:
            available_hospitals = hospitals

        best_hospital, best_hosp_route, hosp_eta = self._select_hospital_with_capacity(
            incident, available_hospitals, net,
        )

        matched = nearest_amb.can_handle(incident.required_capability)
        is_critical = incident.severity in (IncidentSeverity.CRITICAL, IncidentSeverity.HIGH)

        return DispatchDecision(
            ambulance_id=nearest_amb.id,
            target_hospital_id=best_hospital.id if best_hospital else None,
            scene_route=nearest_route,
            hospital_route=best_hosp_route,
            priority_level=1 if is_critical else 2,
            rationale=(
                f"Hospital-aware: {nearest_amb.callsign} [{nearest_amb.capability.value}] "
                f"ETA={nearest_eta/60:.1f}m. Hospital: {best_hospital.name if best_hospital else 'N/A'} "
                f"(capacity-aware)"
            ),
            estimated_scene_eta_sec=nearest_eta,
            estimated_hospital_eta_sec=hosp_eta,
            metadata={"mode": "hospital_congestion", "hospital_capacity_aware": True},
        )

    def _dispatch_disruption_aware(
        self,
        incident: Incident,
        available: list[Ambulance],
        hospitals: list[Hospital],
        net: RoadNetwork,
        all_amb: list[Ambulance] | None,
    ) -> DispatchDecision:
        net.invalidate_route_cache()

        return self._dispatch_hybrid(incident, available, hospitals, net, all_amb)

    def _select_hospital(
        self,
        incident: Incident,
        hospitals: list[Hospital],
        net: RoadNetwork,
    ) -> tuple[Hospital | None, RouteResult | None, float]:
        if not hospitals:
            return None, None, float("inf")

        is_critical = incident.severity in (IncidentSeverity.CRITICAL, IncidentSeverity.HIGH)
        best_hospital: Hospital | None = None
        best_route: RouteResult | None = None
        best_score = -float("inf")
        best_eta = float("inf")

        for hosp in hospitals:
            route = net.calculate_route(
                start_node_id=incident.location_node_id,
                end_node_id=hosp.node_id,
                weight="time",
            )
            if not route.found:
                continue

            hosp_eta = route.estimated_time_seconds
            suitability = hosp.calculate_suitability_score(
                incident.category.value, is_critical=is_critical,
            )
            time_factor = 1.0 / (1.0 + math.log1p(hosp_eta / 300.0))
            score = suitability * time_factor

            if score > best_score:
                best_score = score
                best_hospital = hosp
                best_route = route
                best_eta = hosp_eta

        if best_hospital is None and hospitals:
            return hospitals[0], None, 0.0

        return best_hospital, best_route, best_eta

    def _select_hospital_with_capacity(
        self,
        incident: Incident,
        hospitals: list[Hospital],
        net: RoadNetwork,
    ) -> tuple[Hospital | None, RouteResult | None, float]:
        if not hospitals:
            return None, None, float("inf")

        is_critical = incident.severity in (IncidentSeverity.CRITICAL, IncidentSeverity.HIGH)
        best_hospital: Hospital | None = None
        best_route: RouteResult | None = None
        best_score = -float("inf")
        best_eta = float("inf")

        for hosp in hospitals:
            route = net.calculate_route(
                start_node_id=incident.location_node_id,
                end_node_id=hosp.node_id,
                weight="time",
            )
            if not route.found:
                continue

            hosp_eta = route.estimated_time_seconds
            suitability = hosp.calculate_suitability_score(
                incident.category.value, is_critical=is_critical,
            )

            capacity_ratio = 1.0 - (hosp.occupied_er_beds / max(hosp.total_er_beds, 1))

            time_factor = 1.0 / (1.0 + math.log1p(hosp_eta / 300.0))
            score = suitability * time_factor * (0.5 + 0.5 * capacity_ratio)

            if score > best_score:
                best_score = score
                best_hospital = hosp
                best_route = route
                best_eta = hosp_eta

        if best_hospital is None and hospitals:
            return hospitals[0], None, 0.0

        return best_hospital, best_route, best_eta

    def get_mode_stats(self) -> dict[str, Any]:
        return {
            "total_dispatches": self._total_dispatches,
            "batch_dispatches": self._batch_dispatches,
            "mode_counts": dict(self._mode_counts),
            "last_mode": self._last_mode.value,
        }
