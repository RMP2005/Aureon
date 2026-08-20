"""Baseline dispatch strategy — Nearest Available Unit (Greedy Dispatch)."""

from __future__ import annotations

from ..generators.incident_generator import Incident
from ..models.ambulance import Ambulance
from ..models.hospital import Hospital
from ..network.road_graph import RoadNetwork
from .base import BaseDispatchStrategy, DispatchDecision


class NearestAvailableStrategy(BaseDispatchStrategy):
    """Traditional greedy Nearest-Available dispatch policy."""

    def __init__(self) -> None:
        super().__init__(name="Baseline: Nearest Available Unit")

    def dispatch(
        self,
        incident: Incident,
        available_ambulances: list[Ambulance],
        hospitals: list[Hospital],
        road_network: RoadNetwork,
        all_ambulances: list[Ambulance] | None = None,
    ) -> DispatchDecision:
        """Find the closest idle ambulance and nearest hospital."""
        if not available_ambulances:
            return DispatchDecision(
                ambulance_id=None,
                target_hospital_id=None,
                rationale="No available ambulances in fleet",
            )

        best_ambulance: Ambulance | None = None
        best_scene_route = None
        min_scene_time = float("inf")

        for amb in available_ambulances:
            route = road_network.calculate_route(
                start_node_id=amb.current_node_id,
                end_node_id=incident.location_node_id,
                weight="time",
            )
            if route.found and route.estimated_time_seconds < min_scene_time:
                min_scene_time = route.estimated_time_seconds
                best_ambulance = amb
                best_scene_route = route

        if best_ambulance is None or best_scene_route is None:
            best_ambulance = available_ambulances[0]
            min_scene_time = 600.0

        best_hospital: Hospital | None = None
        best_hosp_route = None
        min_hosp_time = float("inf")

        for hosp in hospitals:
            route = road_network.calculate_route(
                start_node_id=incident.location_node_id,
                end_node_id=hosp.node_id,
                weight="time",
            )
            if route.found and route.estimated_time_seconds < min_hosp_time:
                min_hosp_time = route.estimated_time_seconds
                best_hospital = hosp
                best_hosp_route = route

        if best_hospital is None:
            best_hospital = hospitals[0] if hospitals else None

        return DispatchDecision(
            ambulance_id=best_ambulance.id,
            target_hospital_id=best_hospital.id if best_hospital else None,
            scene_route=best_scene_route,
            hospital_route=best_hosp_route,
            priority_level=1 if incident.severity.value in ("critical", "high") else 2,
            rationale=f"Greedy nearest dispatch: {best_ambulance.callsign} ({best_ambulance.capability.value}) chosen with ETA {min_scene_time/60.0:.1f}m",
            estimated_scene_eta_sec=min_scene_time,
            estimated_hospital_eta_sec=min_hosp_time,
        )
