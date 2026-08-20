"""Geographically distributed ambulance bases and configurable fleet generation."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..models.ambulance import (
    Ambulance,
    AmbulanceCapability,
    AmbulanceStatus,
    create_default_bangalore_fleet,
)


@dataclass
class AmbulanceStation:
    """A physical ambulance base with geographic coordinates."""

    id: str
    name: str
    latitude: float
    longitude: float
    zone: str
    node_id: str  # nearest road network node (populated at runtime)


_STATIONS: list[AmbulanceStation] = [
    AmbulanceStation(
        id="station_central_cbd",
        name="CBD Central",
        latitude=12.9730,
        longitude=77.6080,
        zone="Central",
        node_id="",
    ),
    AmbulanceStation(
        id="station_indiranagar",
        name="Indiranagar",
        latitude=12.9700,
        longitude=77.6390,
        zone="East",
        node_id="",
    ),
    AmbulanceStation(
        id="station_koramangala",
        name="Koramangala",
        latitude=12.9340,
        longitude=77.6200,
        zone="South-East",
        node_id="",
    ),
    AmbulanceStation(
        id="station_whitefield",
        name="Whitefield",
        latitude=12.9800,
        longitude=77.7300,
        zone="East",
        node_id="",
    ),
    AmbulanceStation(
        id="station_hebbal",
        name="Hebbal North",
        latitude=13.0380,
        longitude=77.5950,
        zone="North",
        node_id="",
    ),
    AmbulanceStation(
        id="station_ecity",
        name="Electronic City South",
        latitude=12.8420,
        longitude=77.6750,
        zone="South-East",
        node_id="",
    ),
    AmbulanceStation(
        id="station_silk_board",
        name="Silk Board",
        latitude=12.9176,
        longitude=77.6238,
        zone="South-East",
        node_id="",
    ),
    AmbulanceStation(
        id="station_yeshwanthpur",
        name="Yeshwanthpur",
        latitude=13.0280,
        longitude=77.5408,
        zone="West",
        node_id="",
    ),
    AmbulanceStation(
        id="station_marathahalli",
        name="Marathahalli",
        latitude=12.9591,
        longitude=77.6974,
        zone="South-East",
        node_id="",
    ),
    AmbulanceStation(
        id="station_btm_layout",
        name="BTM Layout",
        latitude=12.9166,
        longitude=77.6101,
        zone="South",
        node_id="",
    ),
]

_STATION_SHORT_CODES: dict[str, str] = {
    "station_central_cbd": "cbd",
    "station_indiranagar": "indira",
    "station_koramangala": "kora",
    "station_whitefield": "wfield",
    "station_hebbal": "hebbal",
    "station_ecity": "ecity",
    "station_silk_board": "sboard",
    "station_yeshwanthpur": "yesh",
    "station_marathahalli": "marath",
    "station_btm_layout": "btm",
}


@dataclass
class FleetConfig:
    """Parameters for generating a simulated ambulance fleet."""

    num_ambulances: int
    als_ratio: float = 0.3  # fraction of ALS units
    stations: list[AmbulanceStation] | None = None  # None = all stations


def get_stations() -> list[AmbulanceStation]:
    """Return all predefined ambulance stations."""
    return list(_STATIONS)


def generate_fleet(config: FleetConfig) -> list[Ambulance]:
    """Generate an ambulance fleet distributed across the configured stations.

    Units are spread proportionally: every station receives
    ``num_ambulances // num_stations`` units, and the remainder is assigned to
    the earliest-listed stations (central city / major population hubs).
    ``ceil(num_ambulances * als_ratio)`` units are ALS (allocated to stations
    in order); all others are BLS.
    """
    stations = config.stations if config.stations is not None else get_stations()
    if not stations or config.num_ambulances <= 0:
        return []

    num_stations = len(stations)
    base_count = config.num_ambulances // num_stations
    remainder = config.num_ambulances % num_stations
    station_counts = [base_count + (1 if i < remainder else 0) for i in range(num_stations)]

    total_als = math.ceil(config.num_ambulances * config.als_ratio)
    als_remaining = total_als

    fleet: list[Ambulance] = []
    for station, count in zip(stations, station_counts):
        short = _STATION_SHORT_CODES.get(station.id, station.id.removeprefix("station_"))
        for index in range(1, count + 1):
            if als_remaining > 0:
                capability = AmbulanceCapability.ALS
                als_remaining -= 1
            else:
                capability = AmbulanceCapability.BLS
            fleet.append(
                Ambulance(
                    id=f"amb_{short}_{capability.value.lower()}_{index}",
                    callsign=f"{capability.value}-{short.upper()}-{index:02d}",
                    capability=capability,
                    base_station_id=station.id,
                    current_node_id=station.node_id or station.id,
                    latitude=station.latitude,
                    longitude=station.longitude,
                    status=AmbulanceStatus.IDLE_AT_BASE,
                )
            )
    return fleet


FLEET_SMALL = FleetConfig(num_ambulances=14)
FLEET_MEDIUM = FleetConfig(num_ambulances=30)
FLEET_LARGE = FleetConfig(num_ambulances=50)
FLEET_XLARGE = FleetConfig(num_ambulances=100)
