"""City Digital Twin Emergency Response Simulation Engine."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from ..dispatch.base import BaseDispatchStrategy
from ..dispatch.baseline import NearestAvailableStrategy
from ..generators.incident_generator import Incident
from ..models.ambulance import Ambulance, AmbulanceStatus, create_default_bangalore_fleet
from ..models.hospital import Hospital, get_default_bangalore_hospitals
from ..network.bangalore_map import build_bangalore_network
from ..network.road_graph import RoadNetwork

logger = logging.getLogger("aureon.simulation.city_engine")


@dataclass
class SimulationMetrics:
    """Consolidated outcome metrics from a simulation run."""

    total_incidents_reported: int = 0
    total_incidents_dispatched: int = 0
    total_incidents_completed: int = 0
    unserviced_incidents_count: int = 0

    mean_response_time_sec: float = 0.0
    median_response_time_sec: float = 0.0
    p90_response_time_sec: float = 0.0
    p95_response_time_sec: float = 0.0
    min_response_time_sec: float = 0.0
    max_response_time_sec: float = 0.0

    critical_incidents_count: int = 0
    critical_mean_response_time_sec: float = 0.0
    critical_target_compliance_rate: float = 0.0

    capability_match_rate: float = 0.0
    mean_hospital_suitability: float = 0.0

    total_fleet_distance_km: float = 0.0
    fleet_utilization_rate: float = 0.0
    missions_per_ambulance_avg: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "total_incidents_reported": self.total_incidents_reported,
            "total_incidents_dispatched": self.total_incidents_dispatched,
            "total_incidents_completed": self.total_incidents_completed,
            "unserviced_incidents_count": self.unserviced_incidents_count,
            "response_times_minutes": {
                "mean": round(self.mean_response_time_sec / 60.0, 2),
                "median": round(self.median_response_time_sec / 60.0, 2),
                "p90": round(self.p90_response_time_sec / 60.0, 2),
                "p95": round(self.p95_response_time_sec / 60.0, 2),
                "min": round(self.min_response_time_sec / 60.0, 2),
                "max": round(self.max_response_time_sec / 60.0, 2),
            },
            "critical_cases": {
                "count": self.critical_incidents_count,
                "mean_response_time_min": round(self.critical_mean_response_time_sec / 60.0, 2),
                "target_compliance_percent": round(self.critical_target_compliance_rate * 100.0, 1),
            },
            "clinical_quality": {
                "capability_match_percent": round(self.capability_match_rate * 100.0, 1),
                "mean_hospital_suitability_score": round(self.mean_hospital_suitability, 3),
            },
            "operations": {
                "total_fleet_distance_km": round(self.total_fleet_distance_km, 2),
                "fleet_utilization_percent": round(self.fleet_utilization_rate * 100.0, 1),
                "avg_missions_per_ambulance": round(self.missions_per_ambulance_avg, 2),
            },
        }


class CitySimulationEngine:
    """Discrete-time Digital Twin Simulation Engine for City Emergency Management."""

    def __init__(
        self,
        road_network: RoadNetwork | None = None,
        hospitals: list[Hospital] | None = None,
        ambulances: list[Ambulance] | None = None,
        strategy: BaseDispatchStrategy | None = None,
        dt_seconds: float = 10.0,
    ) -> None:
        self.road_network = road_network or build_bangalore_network()
        self.hospitals = hospitals or get_default_bangalore_hospitals()
        self.ambulances = ambulances or create_default_bangalore_fleet()
        self.strategy = strategy or NearestAvailableStrategy()
        self.dt = dt_seconds

        self.current_tick: int = 0
        self.sim_time_seconds: float = 0.0

        self.active_incidents: dict[str, Incident] = {}
        self.completed_incidents: list[Incident] = []
        self.pending_queue: list[Incident] = []

        self.dispatch_log: list[dict[str, Any]] = []

    def reset(self) -> None:
        """Reset the simulation environment to initial conditions."""
        self.current_tick = 0
        self.sim_time_seconds = 0.0
        self.active_incidents.clear()
        self.completed_incidents.clear()
        self.pending_queue.clear()
        self.dispatch_log.clear()

        for h in self.hospitals:
            h.occupied_er_beds = int(h.total_er_beds * 0.4)
            h.occupied_icu_beds = int(h.total_icu_beds * 0.4)

        for amb in self.ambulances:
            amb.status = AmbulanceStatus.IDLE_AT_BASE
            amb.current_node_id = amb.base_station_id
            amb.current_incident_id = None
            amb.target_hospital_id = None
            amb.remaining_transit_time_sec = 0.0
            amb.time_in_current_state_sec = 0.0
            amb.total_distance_km = 0.0
            amb.missions_completed = 0
            amb.total_busy_time_sec = 0.0
            amb.total_idle_time_sec = 0.0

    def step(self, new_incidents: list[Incident] | None = None) -> None:
        """Advance the simulation by one time step `dt`."""
        self.current_tick += 1
        self.sim_time_seconds += self.dt

        if new_incidents:
            for inc in new_incidents:
                self.pending_queue.append(inc)
                self.active_incidents[inc.id] = inc

        unresolved_queue: list[Incident] = []
        available_ambulances = [a for a in self.ambulances if a.is_available]

        for incident in self.pending_queue:
            if not available_ambulances:
                unresolved_queue.append(incident)
                continue

            decision = self.strategy.dispatch(
                incident=incident,
                available_ambulances=available_ambulances,
                hospitals=self.hospitals,
                road_network=self.road_network,
                all_ambulances=self.ambulances,
            )

            if decision.ambulance_id is None:
                unresolved_queue.append(incident)
                continue

            chosen_amb = next(
                (a for a in available_ambulances if a.id == decision.ambulance_id),
                None,
            )
            if not chosen_amb:
                unresolved_queue.append(incident)
                continue

            available_ambulances.remove(chosen_amb)

            incident.assigned_ambulance_id = chosen_amb.id
            incident.assigned_hospital_id = decision.target_hospital_id
            incident.dispatched_at_sec = self.sim_time_seconds
            incident.capability_matched = chosen_amb.can_handle(incident.required_capability)

            target_hosp = next((h for h in self.hospitals if h.id == decision.target_hospital_id), None)
            if target_hosp:
                incident.hospital_suitability_score = target_hosp.calculate_suitability_score(
                    incident.category.value,
                    is_critical=incident.severity.value in ("critical", "high"),
                )

            chosen_amb.status = AmbulanceStatus.DISPATCHED_TO_SCENE
            chosen_amb.current_incident_id = incident.id
            chosen_amb.target_hospital_id = decision.target_hospital_id
            chosen_amb.remaining_transit_time_sec = decision.estimated_scene_eta_sec
            chosen_amb.time_in_current_state_sec = 0.0

            if decision.scene_route:
                chosen_amb.total_distance_km += decision.scene_route.total_distance_km

            self.dispatch_log.append({
                "tick": self.current_tick,
                "sim_time_sec": self.sim_time_seconds,
                "incident_id": incident.id,
                "category": incident.category.value,
                "severity": incident.severity.value,
                "ambulance_id": chosen_amb.id,
                "callsign": chosen_amb.callsign,
                "capability": chosen_amb.capability.value,
                "matched": incident.capability_matched,
                "scene_eta_sec": decision.estimated_scene_eta_sec,
                "hospital_id": decision.target_hospital_id,
                "rationale": decision.rationale,
            })

        self.pending_queue = unresolved_queue
        self._update_fleet_states()

    def _update_fleet_states(self) -> None:
        """Update timers, status transitions, and physics for all ambulances."""
        for amb in self.ambulances:
            amb.time_in_current_state_sec += self.dt

            if amb.status == AmbulanceStatus.IDLE_AT_BASE:
                amb.total_idle_time_sec += self.dt
                continue

            amb.total_busy_time_sec += self.dt
            inc = self.active_incidents.get(amb.current_incident_id or "")

            if amb.status == AmbulanceStatus.DISPATCHED_TO_SCENE:
                amb.remaining_transit_time_sec -= self.dt
                if amb.remaining_transit_time_sec <= 0:
                    amb.status = AmbulanceStatus.ON_SCENE_TRIAGE
                    amb.time_in_current_state_sec = 0.0
                    amb.remaining_transit_time_sec = inc.base_on_scene_time_sec if inc else 480.0
                    if inc:
                        amb.current_node_id = inc.location_node_id
                        amb.latitude = inc.latitude
                        amb.longitude = inc.longitude
                        inc.arrived_scene_at_sec = self.sim_time_seconds

            elif amb.status == AmbulanceStatus.ON_SCENE_TRIAGE:
                amb.remaining_transit_time_sec -= self.dt
                if amb.remaining_transit_time_sec <= 0:
                    target_hosp = next((h for h in self.hospitals if h.id == amb.target_hospital_id), None)
                    hosp_route = self.road_network.calculate_route(
                        start_node_id=amb.current_node_id,
                        end_node_id=target_hosp.node_id if target_hosp else amb.base_station_id,
                        weight="time",
                    )
                    hosp_eta = hosp_route.estimated_time_seconds if hosp_route.found else 400.0

                    amb.status = AmbulanceStatus.TRANSPORTING_HOSPITAL
                    amb.time_in_current_state_sec = 0.0
                    amb.remaining_transit_time_sec = hosp_eta
                    amb.total_distance_km += hosp_route.total_distance_km if hosp_route.found else 5.0
                    if inc:
                        inc.departed_scene_at_sec = self.sim_time_seconds

            elif amb.status == AmbulanceStatus.TRANSPORTING_HOSPITAL:
                amb.remaining_transit_time_sec -= self.dt
                if amb.remaining_transit_time_sec <= 0:
                    target_hosp = next((h for h in self.hospitals if h.id == amb.target_hospital_id), None)
                    if target_hosp:
                        amb.current_node_id = target_hosp.node_id
                        amb.latitude = target_hosp.latitude
                        amb.longitude = target_hosp.longitude
                        target_hosp.occupied_er_beds = min(target_hosp.total_er_beds, target_hosp.occupied_er_beds + 1)

                    amb.status = AmbulanceStatus.AT_HOSPITAL_HANDOVER
                    amb.time_in_current_state_sec = 0.0
                    amb.remaining_transit_time_sec = (target_hosp.avg_triage_time_min * 60.0) if target_hosp else 480.0
                    if inc:
                        inc.arrived_hospital_at_sec = self.sim_time_seconds

            elif amb.status == AmbulanceStatus.AT_HOSPITAL_HANDOVER:
                amb.remaining_transit_time_sec -= self.dt
                if amb.remaining_transit_time_sec <= 0:
                    if inc:
                        inc.handover_completed_at_sec = self.sim_time_seconds
                        inc.is_completed = True
                        self.completed_incidents.append(inc)
                        if inc.id in self.active_incidents:
                            del self.active_incidents[inc.id]

                    amb.missions_completed += 1
                    base_route = self.road_network.calculate_route(
                        start_node_id=amb.current_node_id,
                        end_node_id=amb.base_station_id,
                        weight="time",
                    )
                    return_eta = base_route.estimated_time_seconds if base_route.found else 450.0

                    amb.status = AmbulanceStatus.RETURNING_TO_BASE
                    amb.current_incident_id = None
                    amb.target_hospital_id = None
                    amb.time_in_current_state_sec = 0.0
                    amb.remaining_transit_time_sec = return_eta
                    amb.total_distance_km += base_route.total_distance_km if base_route.found else 4.0

            elif amb.status == AmbulanceStatus.RETURNING_TO_BASE:
                amb.remaining_transit_time_sec -= self.dt
                if amb.remaining_transit_time_sec <= 0:
                    station_node = self.road_network.nodes.get(amb.base_station_id)
                    amb.status = AmbulanceStatus.IDLE_AT_BASE
                    amb.current_node_id = amb.base_station_id
                    if station_node:
                        amb.latitude = station_node.latitude
                        amb.longitude = station_node.longitude
                    amb.time_in_current_state_sec = 0.0

    def run_scenario(
        self,
        schedule: list[tuple[float, Incident]],
        duration_minutes: float = 60.0,
    ) -> SimulationMetrics:
        """Execute a full scenario from a pre-defined schedule."""
        self.reset()
        total_seconds = duration_minutes * 60.0
        schedule_queue = list(schedule)
        all_reported: list[Incident] = [inc for _, inc in schedule]

        while self.sim_time_seconds < total_seconds:
            due_incidents: list[Incident] = []
            while schedule_queue and schedule_queue[0][0] <= self.sim_time_seconds:
                _, inc = schedule_queue.pop(0)
                due_incidents.append(inc)

            self.step(new_incidents=due_incidents)

        return self.calculate_metrics(all_reported_incidents=all_reported)

    def calculate_metrics(
        self,
        all_reported_incidents: list[Incident] | None = None,
    ) -> SimulationMetrics:
        """Compute comprehensive performance and outcome metrics."""
        incidents = all_reported_incidents or (
            self.completed_incidents + list(self.active_incidents.values())
        )

        response_times: list[float] = []
        critical_response_times: list[float] = []
        critical_met_target_count = 0
        critical_count = 0
        capability_matched_count = 0
        hospital_suitability_scores: list[float] = []
        dispatched_count = 0

        for inc in incidents:
            if inc.assigned_ambulance_id:
                dispatched_count += 1

            if inc.response_time_seconds is not None:
                rt = inc.response_time_seconds
                response_times.append(rt)

                if inc.severity.value in ("critical", "high"):
                    critical_count += 1
                    critical_response_times.append(rt)
                    if inc.met_response_target:
                        critical_met_target_count += 1

                if inc.capability_matched:
                    capability_matched_count += 1

                if inc.hospital_suitability_score > 0:
                    hospital_suitability_scores.append(inc.hospital_suitability_score)

        mean_rt = sum(response_times) / len(response_times) if response_times else 0.0
        sorted_rt = sorted(response_times)
        median_rt = sorted_rt[len(sorted_rt) // 2] if sorted_rt else 0.0

        p90_idx = int(len(sorted_rt) * 0.90)
        p90_rt = sorted_rt[min(p90_idx, len(sorted_rt) - 1)] if sorted_rt else 0.0

        p95_idx = int(len(sorted_rt) * 0.95)
        p95_rt = sorted_rt[min(p95_idx, len(sorted_rt) - 1)] if sorted_rt else 0.0

        crit_mean_rt = (
            sum(critical_response_times) / len(critical_response_times)
            if critical_response_times
            else 0.0
        )
        crit_compliance = (
            critical_met_target_count / critical_count
            if critical_count > 0
            else 1.0
        )
        match_rate = (
            capability_matched_count / len(response_times)
            if response_times
            else 1.0
        )
        mean_suitability = (
            sum(hospital_suitability_scores) / len(hospital_suitability_scores)
            if hospital_suitability_scores
            else 0.75
        )

        total_distance = sum(a.total_distance_km for a in self.ambulances)
        total_busy = sum(a.total_busy_time_sec for a in self.ambulances)
        total_time = sum(a.total_busy_time_sec + a.total_idle_time_sec for a in self.ambulances)
        utilization = total_busy / total_time if total_time > 0 else 0.0

        return SimulationMetrics(
            total_incidents_reported=len(incidents),
            total_incidents_dispatched=dispatched_count,
            total_incidents_completed=len(self.completed_incidents),
            unserviced_incidents_count=len(self.pending_queue),
            mean_response_time_sec=mean_rt,
            median_response_time_sec=median_rt,
            p90_response_time_sec=p90_rt,
            p95_response_time_sec=p95_rt,
            min_response_time_sec=sorted_rt[0] if sorted_rt else 0.0,
            max_response_time_sec=sorted_rt[-1] if sorted_rt else 0.0,
            critical_incidents_count=critical_count,
            critical_mean_response_time_sec=crit_mean_rt,
            critical_target_compliance_rate=crit_compliance,
            capability_match_rate=match_rate,
            mean_hospital_suitability=mean_suitability,
            total_fleet_distance_km=total_distance,
            fleet_utilization_rate=utilization,
            missions_per_ambulance_avg=len(self.completed_incidents) / len(self.ambulances) if self.ambulances else 0.0,
        )

    def get_current_state(self) -> dict[str, Any]:
        """Export comprehensive serializable state of the city digital twin."""
        return {
            "tick": self.current_tick,
            "sim_time_sec": self.sim_time_seconds,
            "sim_time_formatted": f"{int(self.sim_time_seconds // 3600):02d}:{int((self.sim_time_seconds % 3600) // 60):02d}:{int(self.sim_time_seconds % 60):02d}",
            "strategy": self.strategy.name,
            "ambulances": [
                {
                    "id": a.id,
                    "callsign": a.callsign,
                    "capability": a.capability.value,
                    "status": a.status.value,
                    "latitude": a.latitude,
                    "longitude": a.longitude,
                    "current_node_id": a.current_node_id,
                    "active_incident_id": a.current_incident_id,
                    "missions_completed": a.missions_completed,
                    "total_distance_km": round(a.total_distance_km, 2),
                }
                for a in self.ambulances
            ],
            "hospitals": [
                {
                    "id": h.id,
                    "name": h.name,
                    "latitude": h.latitude,
                    "longitude": h.longitude,
                    "specialties": [s.value for s in h.specialties],
                    "er_occupancy": f"{h.occupied_er_beds}/{h.total_er_beds}",
                    "icu_occupancy": f"{h.occupied_icu_beds}/{h.total_icu_beds}",
                }
                for h in self.hospitals
            ],
            "active_incidents": [
                {
                    "id": inc.id,
                    "category": inc.category.value,
                    "severity": inc.severity.value,
                    "location_name": inc.location_name,
                    "latitude": inc.latitude,
                    "longitude": inc.longitude,
                    "required_capability": inc.required_capability.value,
                    "assigned_ambulance": inc.assigned_ambulance_id,
                }
                for inc in self.active_incidents.values()
            ],
            "completed_incidents_count": len(self.completed_incidents),
            "pending_queue_count": len(self.pending_queue),
        }
