"""Aureon AI Decision Engine — Intelligent Emergency Dispatch."""

from __future__ import annotations

import logging
from typing import Any

from ..generators.incident_generator import Incident, IncidentSeverity
from ..models.ambulance import Ambulance, AmbulanceCapability
from ..models.hospital import Hospital
from ..network.road_graph import RoadNetwork
from .base import BaseDispatchStrategy, DispatchDecision

logger = logging.getLogger("aureon.simulation.intelligence")


class AureonDecisionEngine(BaseDispatchStrategy):
    """Aureon Intelligent Multi-Factor Emergency Dispatcher."""

    def __init__(self, name: str = "Aureon Intelligence (Multi-Factor Engine)") -> None:
        super().__init__(name=name)
        self.w_eta = 0.50             # Weight on travel time
        self.w_capability = 0.30      # Weight on clinical skill match
        self.w_hospital_spec = 0.20   # Weight on hospital specialty match

    def recommend_action(
        self,
        city_state: dict[str, Any],
        emergency_event: dict[str, Any],
    ) -> dict[str, Any]:
        """Generic AI decision interface matching Phase 2 specification."""
        return {
            "strategy": self.name,
            "action": "dispatch_ambulance",
            "recommended_capability": emergency_event.get("required_capability", "BLS"),
            "status": "ready",
        }

    def dispatch(
        self,
        incident: Incident,
        available_ambulances: list[Ambulance],
        hospitals: list[Hospital],
        road_network: RoadNetwork,
        all_ambulances: list[Ambulance] | None = None,
    ) -> DispatchDecision:
        """Execute multi-factor intelligent dispatch evaluation."""
        if not available_ambulances:
            return DispatchDecision(
                ambulance_id=None,
                target_hospital_id=None,
                rationale="No available ambulances in city fleet",
            )

        is_critical = incident.severity in (IncidentSeverity.CRITICAL, IncidentSeverity.HIGH)
        needs_als = incident.required_capability in (AmbulanceCapability.ALS, AmbulanceCapability.MICU)

        scored_candidates: list[tuple[float, Ambulance, Any, float]] = []
        idle_als_count = sum(
            1 for a in available_ambulances if a.capability == AmbulanceCapability.ALS
        )

        for amb in available_ambulances:
            route = road_network.calculate_route(
                start_node_id=amb.current_node_id,
                end_node_id=incident.location_node_id,
                weight="time",
            )
            if not route.found:
                continue

            eta_sec = route.estimated_time_seconds
            time_cost = min(eta_sec / 900.0, 2.0)
            capability_cost = 0.0

            if needs_als:
                if amb.capability == AmbulanceCapability.ALS:
                    capability_cost = 0.0
                else:
                    capability_cost = 1.8
            else:
                if amb.capability == AmbulanceCapability.BLS:
                    capability_cost = 0.0
                else:
                    if idle_als_count <= 2:
                        capability_cost = 1.5
                    else:
                        capability_cost = 0.5

            total_score = (self.w_eta * time_cost) + (self.w_capability * capability_cost)
            scored_candidates.append((total_score, amb, route, eta_sec))

        if not scored_candidates:
            best_amb = available_ambulances[0]
            best_route = road_network.calculate_route(
                best_amb.current_node_id, incident.location_node_id, weight="time"
            )
            best_eta = best_route.estimated_time_seconds if best_route.found else 600.0
        else:
            scored_candidates.sort(key=lambda x: x[0])
            _, best_amb, best_route, best_eta = scored_candidates[0]

        best_hospital: Hospital | None = None
        best_hosp_route = None
        best_hosp_score = -float("inf")
        min_hosp_time = float("inf")

        for hosp in hospitals:
            route = road_network.calculate_route(
                start_node_id=incident.location_node_id,
                end_node_id=hosp.node_id,
                weight="time",
            )
            if not route.found:
                continue

            hosp_eta_sec = route.estimated_time_seconds
            suitability = hosp.calculate_suitability_score(
                incident_category=incident.category.value,
                is_critical=is_critical,
            )

            time_penalty = min(hosp_eta_sec / 1200.0, 1.0) * 0.4
            composite = suitability - time_penalty

            if composite > best_hosp_score:
                best_hosp_score = composite
                best_hospital = hosp
                best_hosp_route = route
                min_hosp_time = hosp_eta_sec

        if best_hospital is None and hospitals:
            best_hospital = hospitals[0]

        matched = best_amb.can_handle(incident.required_capability)
        rationale = (
            f"Aureon Multi-Factor: {best_amb.callsign} [{best_amb.capability.value}] "
            f"selected (ETA: {best_eta/60.0:.1f}m, Req: {incident.required_capability.value}, "
            f"Match: {matched}). Target Hospital: {best_hospital.name if best_hospital else 'N/A'}"
        )

        return DispatchDecision(
            ambulance_id=best_amb.id,
            target_hospital_id=best_hospital.id if best_hospital else None,
            scene_route=best_route,
            hospital_route=best_hosp_route,
            priority_level=1 if is_critical else 2,
            rationale=rationale,
            estimated_scene_eta_sec=best_eta,
            estimated_hospital_eta_sec=min_hosp_time,
            metadata={
                "is_capability_matched": matched,
                "hospital_suitability": best_hosp_score,
            },
        )
