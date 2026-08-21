"""Fleet coverage analysis for dispatch decisions.

Evaluates the impact of dispatching a specific ambulance on remaining
fleet coverage across the service area. Prevents dispatch decisions
that leave geographic zones critically exposed.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from ..models.ambulance import Ambulance, AmbulanceStatus
from ..network.road_graph import RoadNetwork

logger = logging.getLogger("aureon.dispatch.coverage")


@dataclass
class ZoneCoverage:
    """Coverage state for a geographic zone."""

    zone_id: str
    nearest_ambulance_eta_sec: float = float("inf")
    ambulance_count: int = 0
    has_als: bool = False


@dataclass
class CoverageAssessment:
    """Result of fleet coverage analysis after a candidate dispatch."""

    candidate_id: str
    coverage_score: float  # 0.0 (terrible) to 1.0 (excellent)
    zones_below_threshold: int = 0
    worst_zone_eta_sec: float = 0.0
    avg_nearest_eta_sec: float = 0.0
    creates_gap: bool = False
    rationale: str = ""


class FleetCoverageAnalyzer:
    """Evaluates fleet coverage impact of dispatch decisions.

    Uses station-based zones to efficiently assess whether removing
    an ambulance from service would leave a geographic area critically
    under-covered. Runs in O(K * A) where K=stations, A=available ambulances.
    """

    def __init__(
        self,
        coverage_threshold_sec: float = 900.0,
        gap_penalty_threshold_sec: float = 1200.0,
    ) -> None:
        """
        Args:
            coverage_threshold_sec: Maximum acceptable ETA to next ambulance in zone.
            gap_penalty_threshold_sec: ETA above which a zone is considered "gap".
        """
        self.coverage_threshold_sec = coverage_threshold_sec
        self.gap_penalty_threshold_sec = gap_penalty_threshold_sec

    def assess_dispatch_impact(
        self,
        candidate_ambulance: Ambulance,
        available_ambulances: list[Ambulance],
        all_ambulances: list[Ambulance],
        road_network: RoadNetwork,
    ) -> CoverageAssessment:
        """Evaluate coverage impact of dispatching a specific ambulance.

        Computes the "remaining coverage" if this ambulance is removed from
        the available pool, using station locations as zone centers.

        Args:
            candidate_ambulance: The ambulance being considered for dispatch.
            available_ambulances: Currently available ambulances (including candidate).
            all_ambulances: Full fleet (for station location reference).
            road_network: Road network for ETA computation.

        Returns:
            CoverageAssessment with coverage score and gap analysis.
        """
        if len(available_ambulances) <= 1:
            return CoverageAssessment(
                candidate_id=candidate_ambulance.id,
                coverage_score=1.0,
                rationale="Only ambulance available — coverage not a factor",
            )

        # Collect station node IDs as zone centers
        station_nodes: dict[str, str] = {}
        for amb in all_ambulances:
            if amb.base_station_id not in station_nodes:
                station_nodes[amb.base_station_id] = amb.base_station_id

        # Remaining ambulances after dispatch (exclude candidate)
        remaining = [a for a in available_ambulances if a.id != candidate_ambulance.id]

        # Precompute ETAs from each remaining ambulance to each station
        zone_etas: dict[str, list[float]] = {sid: [] for sid in station_nodes}
        als_counts: dict[str, int] = {sid: 0 for sid in station_nodes}

        for amb in remaining:
            for zone_id, station_nid in station_nodes.items():
                route = road_network.calculate_route(
                    start_node_id=amb.current_node_id,
                    end_node_id=station_nid,
                    weight="time",
                )
                if route.found:
                    zone_etas[zone_id].append(route.estimated_time_seconds)
                    if amb.capability.value in ("ALS", "MICU"):
                        als_counts[zone_id] += 1

        # Compute per-zone coverage
        worst_eta = 0.0
        all_etas: list[float] = []
        zones_below = 0

        for zone_id in station_nodes:
            etas = zone_etas[zone_id]
            if etas:
                nearest = min(etas)
                worst_eta = max(worst_eta, nearest)
                all_etas.append(nearest)
                if nearest > self.coverage_threshold_sec:
                    zones_below += 1
            else:
                worst_eta = max(worst_eta, float("inf"))
                zones_below += 1

        avg_eta = sum(all_etas) / len(all_etas) if all_etas else float("inf")
        creates_gap = worst_eta > self.gap_penalty_threshold_sec

        # Coverage score: 1.0 if all zones well-covered, degrades with gaps
        if zones_below == 0 and not creates_gap:
            score = 1.0
        elif creates_gap:
            score = max(0.0, 1.0 - (worst_eta / self.gap_penalty_threshold_sec) * 0.5)
        else:
            score = max(0.0, 1.0 - zones_below * 0.15)

        rationale_parts = []
        if creates_gap:
            rationale_parts.append(f"creates coverage gap (worst={worst_eta/60:.1f}m)")
        if zones_below > 0:
            rationale_parts.append(f"{zones_below} zones below threshold")
        if not rationale_parts:
            rationale_parts.append("coverage acceptable")

        return CoverageAssessment(
            candidate_id=candidate_ambulance.id,
            coverage_score=score,
            zones_below_threshold=zones_below,
            worst_zone_eta_sec=worst_eta,
            avg_nearest_eta_sec=avg_eta,
            creates_gap=creates_gap,
            rationale="; ".join(rationale_parts),
        )
