"""Emergency outcome scoring framework.

Provides composable, transparent scoring of dispatch decisions for
evaluation and future RL-compatible optimization. Replaces opaque
multi-factor weights with explicit reward/penalty components.

Every component is independently measurable and auditable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from ..generators.incident_generator import Incident, IncidentSeverity
from ..models.ambulance import Ambulance, AmbulanceCapability
from ..models.hospital import Hospital
from ..network.road_graph import RoadNetwork, RouteResult


@dataclass
class OutcomeComponents:
    """Decomposed scoring components for a single dispatch decision."""

    # Reward components (positive)
    proximity_score: float = 0.0  # How close the chosen ambulance is
    capability_score: float = 0.0  # Clinical capability match quality
    hospital_match_score: float = 0.0  # Hospital suitability for incident
    coverage_score: float = 0.0  # Fleet coverage preservation

    # Penalty components (negative)
    distance_penalty: float = 0.0  # Extra distance vs nearest option
    capability_gap_penalty: float = 0.0  # Mismatch between need and capability
    coverage_gap_penalty: float = 0.0  # Coverage hole created
    hospital_distance_penalty: float = 0.0  # Hospital too far from scene

    @property
    def total(self) -> float:
        """Net outcome score (higher is better)."""
        rewards = self.proximity_score + self.capability_score + self.hospital_match_score + self.coverage_score
        penalties = self.distance_penalty + self.capability_gap_penalty + self.coverage_gap_penalty + self.hospital_distance_penalty
        return rewards - penalties

    def to_dict(self) -> dict[str, float]:
        return {
            "proximity": self.proximity_score,
            "capability": self.capability_score,
            "hospital_match": self.hospital_match_score,
            "coverage": self.coverage_score,
            "distance_penalty": self.distance_penalty,
            "capability_gap_penalty": self.capability_gap_penalty,
            "coverage_gap_penalty": self.coverage_gap_penalty,
            "hospital_distance_penalty": self.hospital_distance_penalty,
            "total": self.total,
        }


class EmergencyOutcomeScore:
    """Scoring engine for emergency dispatch decisions.

    Computes decomposed reward/penalty components that are individually
    interpretable and suitable for RL reward shaping.

    Design principles:
    - Proximity always dominates (fastest response is primary objective)
    - Capability matching is rewarded only when clinically needed
    - Coverage preservation prevents creating response-time gaps
    - Hospital selection is decoupled from ambulance selection
    """

    def __init__(
        self,
        w_proximity: float = 1.0,
        w_capability: float = 0.3,
        w_hospital: float = 0.15,
        w_coverage: float = 0.2,
        capability_eta_tolerance_pct: float = 0.15,
    ) -> None:
        """
        Args:
            w_proximity: Weight on proximity (response time) component.
            w_capability: Weight on clinical capability matching.
            w_hospital: Weight on hospital suitability.
            w_coverage: Weight on fleet coverage preservation.
            capability_eta_tolerance_pct: Max ETA penalty (%) to allow capability override.
        """
        self.w_proximity = w_proximity
        self.w_capability = w_capability
        self.w_hospital = w_hospital
        self.w_coverage = w_coverage
        self.capability_eta_tolerance_pct = capability_eta_tolerance_pct

    def score_dispatch(
        self,
        chosen_ambulance: Ambulance,
        chosen_route: RouteResult,
        incident: Incident,
        hospitals: list[Hospital],
        nearest_eta_sec: float,
        available_ambulances: list[Ambulance],
        all_ambulances: list[Ambulance],
        road_network: RoadNetwork,
    ) -> OutcomeComponents:
        """Score a dispatch decision with decomposed components.

        Args:
            chosen_ambulance: The ambulance selected for dispatch.
            chosen_route: Route from ambulance to incident scene.
            incident: The emergency incident.
            hospitals: Available hospitals for scoring.
            nearest_eta_sec: ETA of the nearest available ambulance.
            available_ambulances: All available ambulances.
            all_ambulances: Full fleet.
            road_network: Road network for hospital routing.

        Returns:
            OutcomeComponents with individual scoring factors.
        """
        comps = OutcomeComponents()

        chosen_eta = chosen_route.estimated_time_seconds if chosen_route.found else float("inf")

        # --- Proximity Score ---
        # Score relative to nearest possible ETA. 1.0 = is nearest, degrades.
        if nearest_eta_sec > 0:
            proximity_ratio = nearest_eta_sec / max(chosen_eta, 1.0)
            comps.proximity_score = self.w_proximity * min(proximity_ratio, 1.0)
        else:
            comps.proximity_score = self.w_proximity

        # --- Capability Score ---
        needs_als = incident.required_capability in (AmbulanceCapability.ALS, AmbulanceCapability.MICU)
        if needs_als:
            if chosen_ambulance.can_handle(incident.required_capability):
                # Bonus for matching clinical need
                comps.capability_score = self.w_capability * 1.0
            else:
                # Penalty for capability mismatch on critical incident
                comps.capability_gap_penalty = self.w_capability * 0.8
        else:
            # BLS incidents: mild bonus for using BLS (resource conservation)
            if chosen_ambulance.capability == AmbulanceCapability.BLS:
                comps.capability_score = self.w_capability * 0.3

        # --- Hospital Score ---
        best_hospital_score = 0.0
        best_hospital_eta = float("inf")
        for hosp in hospitals:
            hosp_suit = hosp.calculate_suitability_score(
                incident.category.value,
                is_critical=incident.severity.value in ("critical", "high"),
            )
            hosp_route = road_network.calculate_route(
                start_node_id=incident.location_node_id,
                end_node_id=hosp.node_id,
                weight="time",
            )
            if hosp_route.found:
                hosp_eta = hosp_route.estimated_time_seconds
                # Suitability weighted by proximity to scene
                if hosp_eta > 0:
                    combined = hosp_suit * (best_hospital_eta / max(hosp_eta, 1.0)) if best_hospital_eta < float("inf") else hosp_suit
                else:
                    combined = hosp_suit
                if hosp_suit > best_hospital_score:
                    best_hospital_score = hosp_suit
                    best_hospital_eta = hosp_eta

        comps.hospital_match_score = self.w_hospital * best_hospital_score

        # --- Distance Penalty ---
        # Penalty for choosing a farther ambulance than necessary
        if nearest_eta_sec > 0 and chosen_eta > nearest_eta_sec:
            extra_pct = (chosen_eta - nearest_eta_sec) / nearest_eta_sec
            comps.distance_penalty = extra_pct * 0.5  # moderate penalty

        # --- Coverage Score (simplified) ---
        # Count available ALS in fleet as proxy for coverage richness
        idle_als = sum(
            1 for a in available_ambulances
            if a.id != chosen_ambulance.id and a.capability.value in ("ALS", "MICU")
        )
        if needs_als and idle_als == 0:
            comps.coverage_gap_penalty = self.w_coverage * 0.5
        else:
            comps.coverage_score = self.w_coverage * min(1.0, idle_als / 3.0)

        return comps

    def score_dispatch_simple(
        self,
        chosen_ambulance: Ambulance,
        chosen_eta_sec: float,
        incident: Incident,
        nearest_eta_sec: float,
        is_capability_matched: bool,
    ) -> float:
        """Fast simplified scoring for benchmarking (no hospital routing).

        Returns a single composite score for comparison.
        """
        needs_als = incident.required_capability in (AmbulanceCapability.ALS, AmbulanceCapability.MICU)

        # Proximity component
        if nearest_eta_sec > 0:
            proximity = nearest_eta_sec / max(chosen_eta_sec, 1.0)
        else:
            proximity = 1.0

        # Capability component
        if needs_als:
            cap_score = 1.0 if is_capability_matched else -0.5
        else:
            cap_score = 0.3 if chosen_ambulance.capability.value == "BLS" else 0.0

        # Distance penalty
        dist_penalty = 0.0
        if nearest_eta_sec > 0 and chosen_eta_sec > nearest_eta_sec:
            dist_penalty = (chosen_eta_sec - nearest_eta_sec) / nearest_eta_sec * 0.5

        return proximity * self.w_proximity + cap_score * self.w_capability - dist_penalty
