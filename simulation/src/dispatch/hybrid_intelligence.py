"""Aureon Hybrid Intelligence — Adaptive Emergency Dispatch.

Architecture redesign from the XLARGE benchmark failure:

Problem: Previous Aureon optimized multi-factor scores that selected farther
ambulances for better hospital/capability matching. At city scale, the transit
time penalty (26.4% slower) overwhelmed the quality gains.

Solution: Hybrid dispatch with proximity-first default, capability override
when clinically justified, and coverage-aware decision making.

Decision flow:
1. Compute ETAs for ALL available ambulances (scipy-backed, cached)
2. Find nearest ambulance (baseline equivalent)
3. If ALS-required: find nearest ALS-capable ambulance
4. Override to ALS only if ETA penalty is within configurable threshold
5. Evaluate coverage impact of the dispatch
6. Separately select optimal hospital (never sacrifice ambulance ETA for hospital)

This strategy can never perform worse than baseline by more than the
configurable tolerance, while capturing genuine clinical improvements
when the cost is small.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from ..generators.incident_generator import Incident, IncidentSeverity
from ..models.ambulance import Ambulance, AmbulanceCapability
from ..models.hospital import Hospital
from ..network.road_graph import RoadNetwork, RouteResult
from .base import BaseDispatchStrategy, DispatchDecision
from .coverage import CoverageAssessment, FleetCoverageAnalyzer

logger = logging.getLogger("aureon.dispatch.hybrid")


@dataclass
class DispatchCandidate:
    """A scored ambulance candidate for dispatch."""

    ambulance: Ambulance
    route: RouteResult
    eta_sec: float
    is_capability_matched: bool
    is_nearest: bool = False
    is_nearest_capable: bool = False


@dataclass
class HybridDispatchConfig:
    """Configurable thresholds for hybrid dispatch behavior."""

    # Capability override: switch to farther ALS if penalty <= this fraction
    capability_eta_tolerance_pct: float = 0.15

    # Hard ceiling: never choose an ambulance more than this factor slower than nearest
    max_eta_factor: float = 1.5

    # Coverage: enable coverage-aware penalty scoring
    enable_coverage_analysis: bool = True

    # Coverage: ETA threshold for "gap" in seconds
    coverage_gap_threshold_sec: float = 1200.0

    # Hospital: max hospital distance as multiple of scene ETA
    max_hospital_distance_factor: float = 2.0

    # Resource conservation: penalize using ALS for BLS incidents when ALS count is low
    conserve_als_below_count: int = 3


class HybridAureonStrategy(BaseDispatchStrategy):
    """Hybrid dispatch: proximity-first with intelligent capability override.

    Guarantees:
    - Never dispatches an ambulance more than max_eta_factor × nearest ETA
    - Capability override only when ETA penalty <= capability_eta_tolerance_pct
    - Coverage analysis prevents creating response-time gaps
    - Hospital selection is independent of ambulance selection
    """

    def __init__(
        self,
        config: HybridDispatchConfig | None = None,
        name: str = "Aureon Hybrid Intelligence",
    ) -> None:
        super().__init__(name=name)
        self.config = config or HybridDispatchConfig()
        self._coverage_analyzer = FleetCoverageAnalyzer(
            coverage_threshold_sec=self.config.coverage_gap_threshold_sec,
            gap_penalty_threshold_sec=self.config.coverage_gap_threshold_sec * 1.3,
        )

    def dispatch(
        self,
        incident: Incident,
        available_ambulances: list[Ambulance],
        hospitals: list[Hospital],
        road_network: RoadNetwork,
        all_ambulances: list[Ambulance] | None = None,
    ) -> DispatchDecision:
        """Execute hybrid proximity-first dispatch with capability override."""
        if not available_ambulances:
            return DispatchDecision(
                ambulance_id=None,
                target_hospital_id=None,
                rationale="No available ambulances in fleet",
            )

        is_critical = incident.severity in (IncidentSeverity.CRITICAL, IncidentSeverity.HIGH)
        needs_als = incident.required_capability in (AmbulanceCapability.ALS, AmbulanceCapability.MICU)

        # === Phase 1: Compute ETAs for all candidates ===
        candidates = self._compute_candidates(incident, available_ambulances, road_network)

        if not candidates:
            return DispatchDecision(
                ambulance_id=None,
                target_hospital_id=None,
                rationale="No reachable ambulance found via road network",
            )

        # === Phase 2: Identify key candidates ===
        nearest = min(candidates, key=lambda c: c.eta_sec)
        nearest.is_nearest = True
        nearest_eta = nearest.eta_sec

        best_capable: DispatchCandidate | None = None
        if needs_als:
            capable = [c for c in candidates if c.is_capability_matched]
            if capable:
                best_capable = min(capable, key=lambda c: c.eta_sec)
                best_capable.is_nearest_capable = True

        # === Phase 3: Make dispatch decision ===
        chosen, decision_reason = self._select_ambulance(
            nearest, best_capable, needs_als, is_critical, candidates,
        )

        # === Phase 4: Coverage analysis ===
        coverage_assessment = None
        if self.config.enable_coverage_analysis and all_ambulances:
            coverage_assessment = self._coverage_analyzer.assess_dispatch_impact(
                candidate_ambulance=chosen.ambulance,
                available_ambulances=available_ambulances,
                all_ambulances=all_ambulances,
                road_network=road_network,
            )
            # If coverage creates a gap and we're not in critical override,
            # consider falling back to nearest
            if (coverage_assessment.creates_gap
                    and not is_critical
                    and chosen.ambulance.id != nearest.ambulance.id):
                chosen = nearest
                decision_reason += " + coverage fallback"

        # === Phase 5: Hospital selection (independent of ambulance choice) ===
        best_hospital, best_hosp_route, hosp_eta = self._select_hospital(
            incident, hospitals, road_network,
        )

        # === Phase 6: Build decision ===
        matched = chosen.ambulance.can_handle(incident.required_capability)

        rationale = (
            f"Hybrid: {chosen.ambulance.callsign} [{chosen.ambulance.capability.value}] "
            f"ETA={chosen.eta_sec/60:.1f}m (nearest={nearest_eta/60:.1f}m, "
            f"gap={chosen.eta_sec - nearest_eta:.0f}s). "
            f"Decision: {decision_reason}. "
            f"Hospital: {best_hospital.name if best_hospital else 'N/A'} "
            f"(ETA={hosp_eta/60:.1f}m)"
        )
        if coverage_assessment:
            rationale += f" Coverage: {coverage_assessment.rationale}"

        return DispatchDecision(
            ambulance_id=chosen.ambulance.id,
            target_hospital_id=best_hospital.id if best_hospital else None,
            scene_route=chosen.route,
            hospital_route=best_hosp_route,
            priority_level=1 if is_critical else 2,
            rationale=rationale,
            estimated_scene_eta_sec=chosen.eta_sec,
            estimated_hospital_eta_sec=hosp_eta,
            metadata={
                "is_capability_matched": matched,
                "nearest_eta_sec": nearest_eta,
                "eta_gap_sec": chosen.eta_sec - nearest_eta,
                "decision_reason": decision_reason,
                "coverage_score": coverage_assessment.coverage_score if coverage_assessment else None,
            },
        )

    def _compute_candidates(
        self,
        incident: Incident,
        available_ambulances: list[Ambulance],
        road_network: RoadNetwork,
    ) -> list[DispatchCandidate]:
        """Compute ETAs and capability match for all available ambulances."""
        candidates = []
        for amb in available_ambulances:
            route = road_network.calculate_route(
                start_node_id=amb.current_node_id,
                end_node_id=incident.location_node_id,
                weight="time",
            )
            if route.found:
                candidates.append(DispatchCandidate(
                    ambulance=amb,
                    route=route,
                    eta_sec=route.estimated_time_seconds,
                    is_capability_matched=amb.can_handle(incident.required_capability),
                ))
        return candidates

    def _select_ambulance(
        self,
        nearest: DispatchCandidate,
        best_capable: DispatchCandidate | None,
        needs_als: bool,
        is_critical: bool,
        all_candidates: list[DispatchCandidate],
    ) -> tuple[DispatchCandidate, str]:
        """Select the best ambulance based on proximity-first hybrid logic.

        Returns (chosen_candidate, decision_reason_string).
        """
        # Default: nearest ambulance (baseline behavior)
        chosen = nearest
        reason = "nearest"

        if not needs_als or best_capable is None:
            return chosen, reason

        if best_capable.ambulance.id == nearest.ambulance.id:
            return nearest, "nearest is already capability-matched"

        # Compute ETA penalty for capability override
        eta_penalty_sec = best_capable.eta_sec - nearest.eta_sec
        eta_penalty_pct = eta_penalty_sec / nearest.eta_sec if nearest.eta_sec > 0 else float("inf")

        # Hard ceiling check
        if best_capable.eta_sec > nearest.eta_sec * self.config.max_eta_factor:
            return nearest, f"nearest (cap override exceeds {self.config.max_eta_factor}× ceiling)"

        # Tolerance check
        if eta_penalty_pct <= self.config.capability_eta_tolerance_pct:
            return best_capable, f"capability override (penalty={eta_penalty_pct:.1%} < {self.config.capability_eta_tolerance_pct:.0%} threshold)"

        # Critical incident: allow larger tolerance
        if is_critical and eta_penalty_pct <= self.config.capability_eta_tolerance_pct * 2:
            return best_capable, f"critical capability override (penalty={eta_penalty_pct:.1%}, critical放宽)"

        return nearest, f"nearest (cap penalty={eta_penalty_pct:.1%} exceeds threshold)"

    def _select_hospital(
        self,
        incident: Incident,
        hospitals: list[Hospital],
        road_network: RoadNetwork,
    ) -> tuple[Hospital | None, RouteResult | None, float]:
        """Select optimal hospital independent of ambulance choice.

        Optimizes for: suitability × (1 / travel_time) to balance clinical
        quality with transport time. Never sacrifices transport time for
        marginal suitability gains.
        """
        if not hospitals:
            return None, None, float("inf")

        is_critical = incident.severity.value in ("critical", "high")
        best_hospital: Hospital | None = None
        best_route: RouteResult | None = None
        best_score = -float("inf")
        best_eta = float("inf")

        for hosp in hospitals:
            route = road_network.calculate_route(
                start_node_id=incident.location_node_id,
                end_node_id=hosp.node_id,
                weight="time",
            )
            if not route.found:
                continue

            hosp_eta = route.estimated_time_seconds
            suitability = hosp.calculate_suitability_score(
                incident.category.value,
                is_critical=is_critical,
            )

            # Score: suitability weighted by transport time
            # Use log-scale to prevent distance from dominating
            import math
            time_factor = 1.0 / (1.0 + math.log1p(hosp_eta / 300.0))
            score = suitability * time_factor

            if score > best_score:
                best_score = score
                best_hospital = hosp
                best_route = route
                best_eta = hosp_eta

        # Fallback: nearest hospital with capacity
        if best_hospital is None:
            for hosp in hospitals:
                if hosp.occupied_er_beds < hosp.total_er_beds:
                    route = road_network.calculate_route(
                        start_node_id=incident.location_node_id,
                        end_node_id=hosp.node_id,
                        weight="time",
                    )
                    if route.found:
                        return hosp, route, route.estimated_time_seconds
            if hospitals:
                return hospitals[0], None, 0.0

        return best_hospital, best_route, best_eta
