"""Ambulance resource entities, capabilities, and operational lifecycle."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AmbulanceCapability(str, Enum):
    """Clinical capabilities of emergency ambulances."""

    BLS = "BLS"  # Basic Life Support (AED, oxygen, basic immobilization)
    ALS = "ALS"  # Advanced Life Support (cardiac monitor, ventilator, IV drugs, intubation)
    MICU = "MICU"  # Mobile Intensive Care Unit (critical care physician team)


class AmbulanceStatus(str, Enum):
    """Operational lifecycle statuses for emergency units."""

    IDLE_AT_BASE = "idle_at_base"
    DISPATCHED_TO_SCENE = "dispatched_to_scene"
    ON_SCENE_TRIAGE = "on_scene_triage"
    TRANSPORTING_HOSPITAL = "transporting_hospital"
    AT_HOSPITAL_HANDOVER = "at_hospital_handover"
    RETURNING_TO_BASE = "returning_to_base"


@dataclass
class Ambulance:
    """An emergency ambulance vehicle resource in the digital twin."""

    id: str
    callsign: str
    capability: AmbulanceCapability
    base_station_id: str
    current_node_id: str
    latitude: float
    longitude: float
    status: AmbulanceStatus = AmbulanceStatus.IDLE_AT_BASE

    # Mission tracking
    current_incident_id: str | None = None
    target_hospital_id: str | None = None
    target_node_id: str | None = None
    route_path: list[str] = field(default_factory=list)
    remaining_transit_time_sec: float = 0.0
    time_in_current_state_sec: float = 0.0

    # Operational metrics
    total_distance_km: float = 0.0
    missions_completed: int = 0
    total_busy_time_sec: float = 0.0
    total_idle_time_sec: float = 0.0

    @property
    def is_available(self) -> bool:
        """Check if ambulance is free to be dispatched."""
        return self.status == AmbulanceStatus.IDLE_AT_BASE

    def can_handle(self, required_capability: AmbulanceCapability) -> bool:
        """Check if ambulance capability meets or exceeds requirements."""
        hierarchy = {
            AmbulanceCapability.BLS: 1,
            AmbulanceCapability.ALS: 2,
            AmbulanceCapability.MICU: 3,
        }
        return hierarchy[self.capability] >= hierarchy[required_capability]

    def reset_to_base(self, base_node_id: str, lat: float, lon: float) -> None:
        """Return ambulance to initial idle state at base."""
        self.status = AmbulanceStatus.IDLE_AT_BASE
        self.current_node_id = base_node_id
        self.latitude = lat
        self.longitude = lon
        self.current_incident_id = None
        self.target_hospital_id = None
        self.target_node_id = None
        self.route_path = []
        self.remaining_transit_time_sec = 0.0
        self.time_in_current_state_sec = 0.0


def create_default_bangalore_fleet() -> list[Ambulance]:
    """Create a realistic distributed fleet of BLS and ALS ambulances across Bangalore."""
    fleet_configs = [
        # CBD Base
        ("amb_cbd_als_1", "ALS-CBD-01", AmbulanceCapability.ALS, "station_central_cbd", 12.9730, 77.6080),
        ("amb_cbd_bls_1", "BLS-CBD-02", AmbulanceCapability.BLS, "station_central_cbd", 12.9730, 77.6080),
        ("amb_cbd_bls_2", "BLS-CBD-03", AmbulanceCapability.BLS, "station_central_cbd", 12.9730, 77.6080),

        # Indiranagar Base
        ("amb_indira_als_1", "ALS-IND-01", AmbulanceCapability.ALS, "station_indiranagar", 12.9700, 77.6390),
        ("amb_indira_bls_1", "BLS-IND-02", AmbulanceCapability.BLS, "station_indiranagar", 12.9700, 77.6390),

        # Koramangala Base
        ("amb_kora_als_1", "ALS-KOR-01", AmbulanceCapability.ALS, "station_koramangala", 12.9340, 77.6200),
        ("amb_kora_bls_1", "BLS-KOR-02", AmbulanceCapability.BLS, "station_koramangala", 12.9340, 77.6200),
        ("amb_kora_bls_2", "BLS-KOR-03", AmbulanceCapability.BLS, "station_koramangala", 12.9340, 77.6200),

        # Whitefield Base
        ("amb_wfield_als_1", "ALS-WFD-01", AmbulanceCapability.ALS, "station_whitefield", 12.9800, 77.7300),
        ("amb_wfield_bls_1", "BLS-WFD-02", AmbulanceCapability.BLS, "station_whitefield", 12.9800, 77.7300),

        # Hebbal Base (North)
        ("amb_hebbal_als_1", "ALS-HEB-01", AmbulanceCapability.ALS, "station_hebbal", 13.0380, 77.5950),
        ("amb_hebbal_bls_1", "BLS-HEB-02", AmbulanceCapability.BLS, "station_hebbal", 13.0380, 77.5950),

        # Electronic City Base (South)
        ("amb_ecity_als_1", "ALS-ECT-01", AmbulanceCapability.ALS, "station_ecity", 12.8420, 77.6750),
        ("amb_ecity_bls_1", "BLS-ECT-02", AmbulanceCapability.BLS, "station_ecity", 12.8420, 77.6750),
    ]

    return [
        Ambulance(
            id=cid,
            callsign=callsign,
            capability=cap,
            base_station_id=station_id,
            current_node_id=station_id,
            latitude=lat,
            longitude=lon,
        )
        for cid, callsign, cap, station_id, lat, lon in fleet_configs
    ]
