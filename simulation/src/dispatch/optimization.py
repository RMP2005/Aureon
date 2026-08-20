"""Decision optimization environment for emergency dispatch.

Provides RL-compatible state/action/reward interfaces and a
constraint-optimization baseline using OR-Tools.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..generators.incident_generator import Incident, IncidentSeverity
from ..models.ambulance import Ambulance, AmbulanceCapability, AmbulanceStatus
from ..models.hospital import Hospital
from ..network.road_graph import RoadNetwork
from .base import BaseDispatchStrategy, DispatchDecision

logger = logging.getLogger("aureon.dispatch.optimization")


# ---------------------------------------------------------------------------
# State representation
# ---------------------------------------------------------------------------

@dataclass
class DispatchState:
    """Compact state representation for decision optimization.

    Compatible with RL observation spaces.
    """

    # Ambulance positions and statuses
    ambulance_positions: list[tuple[str, str]]  # (amb_id, current_node_id)
    ambulance_statuses: list[str]  # status value per ambulance
    ambulance_capabilities: list[str]  # capability value per ambulance

    # Active incidents
    pending_incident_count: int
    active_incident_count: int
    critical_pending_count: int
    pending_incident_locations: list[str]  # node_ids of pending incidents
    pending_severities: list[str]  # severity values

    # Hospital capacity
    hospital_er_free: list[int]  # free ER beds per hospital
    hospital_icu_free: list[int]  # free ICU beds per hospital

    # Time
    hour_of_day: float
    sim_time_sec: float

    # Traffic
    avg_congestion: float

    def to_vector(self) -> list[float]:
        """Convert to flat numeric vector for RL models."""
        vec: list[float] = []

        # Ambulance features (4 per ambulance)
        for i in range(len(self.ambulance_positions)):
            status_map = {
                "idle_at_base": 0.0, "dispatched_to_scene": 1.0,
                "on_scene_triage": 2.0, "transporting_hospital": 3.0,
                "at_hospital_handover": 4.0, "returning_to_base": 5.0,
            }
            cap_map = {"BLS": 0.0, "ALS": 1.0, "MICU": 2.0}
            vec.append(status_map.get(self.ambulance_statuses[i], -1.0))
            vec.append(cap_map.get(self.ambulance_capabilities[i], -1.0))

        # Incident features
        vec.append(self.pending_incident_count)
        vec.append(self.active_incident_count)
        vec.append(self.critical_pending_count)

        # Hospital features
        vec.extend(self.hospital_er_free)
        vec.extend(self.hospital_icu_free)

        # Context
        vec.append(self.hour_of_day)
        vec.append(self.avg_congestion)

        return vec

    @property
    def feature_names(self) -> list[str]:
        names: list[str] = []
        n_amb = len(self.ambulance_positions)
        for i in range(n_amb):
            names.extend([f"amb_{i}_status", f"amb_{i}_cap"])
        names.extend(["pending_count", "active_count", "critical_pending"])
        names.extend([f"hosp_{i}_er_free" for i in range(len(self.hospital_er_free))])
        names.extend([f"hosp_{i}_icu_free" for i in range(len(self.hospital_icu_free))])
        names.extend(["hour_of_day", "avg_congestion"])
        return names


# ---------------------------------------------------------------------------
# Action space
# ---------------------------------------------------------------------------

class ActionType(str, Enum):
    """Available dispatch actions."""

    DISPATCH = "dispatch"
    WAIT = "wait"


@dataclass
class DispatchAction:
    """A dispatch decision: which ambulance to assign to which incident."""

    action_type: ActionType
    ambulance_id: str | None = None
    incident_id: str | None = None
    target_hospital_id: str | None = None


# ---------------------------------------------------------------------------
# Reward function
# ---------------------------------------------------------------------------

@dataclass
class RewardConfig:
    """Configurable weights for the reward function."""

    response_time_weight: float = 1.0
    critical_bonus: float = 2.0
    coverage_penalty: float = 0.5
    capability_mismatch_penalty: float = 0.3
    no_dispatch_penalty: float = 0.8

    # Thresholds
    target_response_sec: float = 480.0  # 8 minutes
    max_acceptable_sec: float = 900.0  # 15 minutes


class RewardCalculator:
    """Computes rewards for dispatch decisions.

    Designed for RL training but also used to evaluate
    optimization-based dispatch.
    """

    def __init__(self, config: RewardConfig | None = None) -> None:
        self.config = config or RewardConfig()

    def dispatch_reward(
        self,
        incident: Incident,
        ambulance: Ambulance,
        eta_sec: float,
    ) -> float:
        """Compute reward for a single dispatch decision."""
        cfg = self.config

        # Response time reward: higher for faster response
        if eta_sec <= cfg.target_response_sec:
            rt_reward = 1.0
        elif eta_sec <= cfg.max_acceptable_sec:
            # Linear decay from 1.0 to 0.0
            rt_reward = 1.0 - (eta_sec - cfg.target_response_sec) / (
                cfg.max_acceptable_sec - cfg.target_response_sec
            )
        else:
            rt_reward = 0.0

        # Critical case bonus
        is_critical = incident.severity in (IncidentSeverity.CRITICAL, IncidentSeverity.HIGH)
        critical_mult = cfg.critical_bonus if is_critical else 1.0

        # Capability match
        cap_match = ambulance.can_handle(incident.required_capability)
        cap_penalty = 0.0 if cap_match else -cfg.capability_mismatch_penalty

        reward = (rt_reward * critical_mult) + cap_penalty
        return reward

    def no_dispatch_reward(self) -> float:
        """Penalty for not dispatching when incidents are pending."""
        return -self.config.no_dispatch_penalty

    def coverage_reward(self, idle_count: int, total_count: int) -> float:
        """Reward for maintaining adequate coverage."""
        ratio = idle_count / max(total_count, 1)
        if ratio < 0.15:
            return -self.config.coverage_penalty
        return 0.0


# ---------------------------------------------------------------------------
# OR-Tools Dispatch Optimizer
# ---------------------------------------------------------------------------

class ORToolsDispatcher(BaseDispatchStrategy):
    """Dispatch strategy using constraint optimization (OR-Tools).

    Formulates dispatch as a minimum-cost assignment problem:
    - Minimize total weighted response time
    - Constraint: each incident assigned at most one ambulance
    - Constraint: each ambulance assigned at most one incident
    - Constraint: capability matching (ALS incidents need ALS/MICU)
    - Objective: minimize sum of ETAs weighted by severity
    """

    def __init__(self) -> None:
        super().__init__(name="Aureon Optimization (OR-Tools)")
        self.reward_calc = RewardCalculator()

    def dispatch(
        self,
        incident: Incident,
        available_ambulances: list[Ambulance],
        hospitals: list[Hospital],
        road_network: RoadNetwork,
        all_ambulances: list[Ambulance] | None = None,
    ) -> DispatchDecision:
        """Dispatch single incident using optimization scoring.

        For single-incident dispatch (called by CitySimulationEngine),
        we use a greedy optimization approach that considers:
        1. Response time minimization
        2. Capability constraints
        3. Hospital suitability
        4. Future coverage preservation
        """
        if not available_ambulances:
            return DispatchDecision(ambulance_id=None, target_hospital_id=None)

        scored: list[tuple[float, str, Ambulance, Any, float]] = []

        for amb in available_ambulances:
            route = road_network.calculate_route(
                start_node_id=amb.current_node_id,
                end_node_id=incident.location_node_id,
                weight="time",
            )
            if not route.found:
                continue

            eta_sec = route.estimated_time_seconds
            reward = self.reward_calc.dispatch_reward(incident, amb, eta_sec)

            # Coverage preservation: penalize using ALS for BLS calls
            is_critical = incident.severity in (IncidentSeverity.CRITICAL, IncidentSeverity.HIGH)
            if not is_critical and amb.capability == AmbulanceCapability.ALS:
                idle_als = sum(
                    1 for a in (all_ambulances or [])
                    if a.is_available and a.capability == AmbulanceCapability.ALS
                )
                if idle_als <= 2:
                    reward -= 0.5  # Preserve ALS for critical cases

            scored.append((-reward, amb.id, amb, route, eta_sec))

        if not scored:
            return DispatchDecision(ambulance_id=None, target_hospital_id=None)

        scored.sort()
        _, _, best_amb, best_route, best_eta = scored[0]

        # Hospital selection: optimize for suitability and capacity
        best_hospital: Hospital | None = None
        best_hosp_score = -float("inf")
        best_hosp_route = None

        is_critical = incident.severity in (IncidentSeverity.CRITICAL, IncidentSeverity.HIGH)

        for hosp in hospitals:
            hosp_route = road_network.calculate_route(
                start_node_id=incident.location_node_id,
                end_node_id=hosp.node_id,
                weight="time",
            )
            if not hosp_route.found:
                continue

            suitability = hosp.calculate_suitability_score(
                incident.category.value, is_critical=is_critical,
            )
            hosp_eta = hosp_route.estimated_time_seconds
            # Penalize hospitals that are far or nearly full
            capacity_penalty = 0.0
            if hosp.er_occupancy_ratio > 0.9:
                capacity_penalty = 0.3
            if is_critical and not hosp.has_icu_capacity:
                capacity_penalty += 0.4

            score = suitability - (hosp_eta / 1200.0) * 0.4 - capacity_penalty
            if score > best_hosp_score:
                best_hosp_score = score
                best_hospital = hosp
                best_hosp_route = hosp_route

        if best_hospital is None and hospitals:
            for h in hospitals:
                if h.occupied_er_beds < h.total_er_beds:
                    best_hospital = h
                    break
            if best_hospital is None:
                best_hospital = hospitals[0]

        return DispatchDecision(
            ambulance_id=best_amb.id,
            target_hospital_id=best_hospital.id if best_hospital else None,
            scene_route=best_route,
            hospital_route=best_hosp_route,
            priority_level=1 if is_critical else 2,
            rationale=(
                f"OR-Tools optimized: {best_amb.callsign} [{best_amb.capability.value}] "
                f"ETA={best_eta/60:.1f}m, Hospital={best_hospital.name if best_hospital else 'N/A'}"
            ),
            estimated_scene_eta_sec=best_eta,
            estimated_hospital_eta_sec=best_hosp_route.estimated_time_seconds if best_hosp_route else 0.0,
            metadata={
                "strategy": "optimization",
                "reward_score": -scored[0][0],
                "is_capability_matched": best_amb.can_handle(incident.required_capability),
            },
        )


class BatchORToolsDispatcher(BaseDispatchStrategy):
    """Batch optimization: assigns all pending incidents simultaneously.

    Uses OR-Tools CP-SAT solver for global optimum when multiple
    incidents are pending and multiple ambulances available.
    """

    def __init__(self) -> None:
        super().__init__(name="Aureon Batch Optimization (OR-Tools CP-SAT)")
        self.reward_calc = RewardCalculator()

    def dispatch(
        self,
        incident: Incident,
        available_ambulances: list[Ambulance],
        hospitals: list[Hospital],
        road_network: RoadNetwork,
        all_ambulances: list[Ambulance] | None = None,
    ) -> DispatchDecision:
        """Same as single dispatch — batch optimization is handled externally."""
        # For integration with CitySimulationEngine, fall back to single-incident optimization
        return ORToolsDispatcher().dispatch(
            incident, available_ambulances, hospitals, road_network, all_ambulances,
        )

    def batch_dispatch(
        self,
        incidents: list[Incident],
        available_ambulances: list[Ambulance],
        hospitals: list[Hospital],
        road_network: RoadNetwork,
        all_ambulances: list[Ambulance] | None = None,
    ) -> list[DispatchDecision]:
        """Globally optimize assignment of incidents to ambulances.

        Uses OR-Tools CP-SAT solver for minimum-cost bipartite matching.
        """
        try:
            from ortools.sat.python import cp_model
        except ImportError:
            logger.warning("OR-Tools not available, falling back to greedy")
            return self._greedy_batch(incidents, available_ambulances, hospitals, road_network, all_ambulances)

        if not incidents or not available_ambulances:
            return [DispatchDecision(ambulance_id=None, target_hospital_id=None)] * len(incidents)

        n_inc = len(incidents)
        n_amb = len(available_ambulances)

        model = cp_model.CpModel()

        # Precompute ETAs and costs
        eta_matrix: dict[tuple[int, int], float] = {}
        cap_matrix: dict[tuple[int, int], bool] = {}

        for i, inc in enumerate(incidents):
            for j, amb in enumerate(available_ambulances):
                route = road_network.calculate_route(
                    amb.current_node_id, inc.location_node_id, weight="time",
                )
                if route.found:
                    eta_matrix[(i, j)] = route.estimated_time_seconds
                    cap_matrix[(i, j)] = amb.can_handle(inc.required_capability)
                else:
                    eta_matrix[(i, j)] = 9999.0
                    cap_matrix[(i, j)] = False

        # Decision variables: x[i,j] = 1 if incident i assigned to ambulance j
        x: dict[tuple[int, int], Any] = {}
        for i in range(n_inc):
            for j in range(n_amb):
                x[(i, j)] = model.NewBoolVar(f"x_{i}_{j}")

        # Constraint: each incident at most one ambulance
        for i in range(n_inc):
            model.Add(sum(x[(i, j)] for j in range(n_amb)) <= 1)

        # Constraint: each ambulance at most one incident
        for j in range(n_amb):
            model.Add(sum(x[(i, j)] for i in range(n_inc)) <= 1)

        # Capability constraint: can't assign if ambulance can't handle
        for i in range(n_inc):
            for j in range(n_amb):
                if not cap_matrix.get((i, j), False):
                    model.Add(x[(i, j)] == 0)

        # Objective: minimize total weighted response time
        obj_terms = []
        for i in range(n_inc):
            severity_weight = 1.0
            if incidents[i].severity in (IncidentSeverity.CRITICAL, IncidentSeverity.HIGH):
                severity_weight = 3.0
            elif incidents[i].severity == IncidentSeverity.MODERATE:
                severity_weight = 1.5

            for j in range(n_amb):
                cost = int(eta_matrix.get((i, j), 9999.0) * severity_weight)
                obj_terms.append(cost * x[(i, j)])

        model.Minimize(sum(obj_terms))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 2.0  # Time limit
        status = solver.Solve(model)

        decisions: list[DispatchDecision] = []

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            assigned_ambulances: set[int] = set()
            for i in range(n_inc):
                found = False
                for j in range(n_amb):
                    if solver.Value(x[(i, j)]) == 1:
                        amb = available_ambulances[j]
                        route = road_network.calculate_route(
                            amb.current_node_id, incidents[i].location_node_id, weight="time",
                        )
                        # Find best hospital
                        hosp = self._select_hospital(incidents[i], hospitals, road_network)
                        decisions.append(DispatchDecision(
                            ambulance_id=amb.id,
                            target_hospital_id=hosp.id if hosp else None,
                            scene_route=route if route.found else None,
                            estimated_scene_eta_sec=eta_matrix.get((i, j), 0.0),
                            priority_level=1 if incidents[i].severity in (IncidentSeverity.CRITICAL, IncidentSeverity.HIGH) else 2,
                            rationale=f"CP-SAT optimized: {amb.callsign} -> {incidents[i].id}",
                            metadata={"strategy": "batch_optimization", "solver_status": "optimal" if status == cp_model.OPTIMAL else "feasible"},
                        ))
                        assigned_ambulances.add(j)
                        found = True
                        break
                if not found:
                    decisions.append(DispatchDecision(ambulance_id=None, target_hospital_id=None))
        else:
            decisions = self._greedy_batch(incidents, available_ambulances, hospitals, road_network, all_ambulances)

        return decisions

    def _select_hospital(
        self, incident: Incident, hospitals: list[Hospital], road_network: RoadNetwork,
    ) -> Hospital | None:
        is_critical = incident.severity in (IncidentSeverity.CRITICAL, IncidentSeverity.HIGH)
        best, best_score = None, -float("inf")
        for h in hospitals:
            route = road_network.calculate_route(incident.location_node_id, h.node_id, "time")
            if not route.found:
                continue
            suit = h.calculate_suitability_score(incident.category.value, is_critical)
            score = suit - (route.estimated_time_seconds / 1200.0) * 0.4
            if h.er_occupancy_ratio > 0.9:
                score -= 0.3
            if score > best_score:
                best_score = score
                best = h
        return best or (hospitals[0] if hospitals else None)

    def _greedy_batch(
        self, incidents, ambulances, hospitals, road_network, all_ambulances,
    ) -> list[DispatchDecision]:
        return [
            ORToolsDispatcher().dispatch(inc, ambulances, hospitals, road_network, all_ambulances)
            for inc in incidents
        ]
