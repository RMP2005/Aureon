"""City state models for urban digital twin simulation.

Defines city zones, infrastructure, population distribution,
and resource availability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ZoneType(str, Enum):
    """Urban zone classifications."""

    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    MIXED_USE = "mixed_use"
    PARK = "park"
    TRANSPORT = "transport"
    EMERGENCY = "emergency"
    GOVERNMENT = "government"


class InfrastructureStatus(str, Enum):
    """Infrastructure operational status."""

    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    IMPAIRED = "impaired"
    OFFLINE = "offline"


@dataclass
class GeoCoordinate:
    """Geographic coordinate."""

    latitude: float
    longitude: float


@dataclass
class CityZone:
    """A discrete zone within the city."""

    id: str
    name: str
    zone_type: ZoneType
    center: GeoCoordinate
    area_sq_km: float = 1.0
    population: int = 0
    population_density: float = 0.0
    infrastructure_status: InfrastructureStatus = InfrastructureStatus.OPERATIONAL


@dataclass
class ResourcePool:
    """Available emergency response resources."""

    ambulances: int = 0
    fire_trucks: int = 0
    police_units: int = 0
    medical_teams: int = 0
    shelters_capacity: int = 0

    @property
    def total_units(self) -> int:
        """Total available response units."""
        return (
            self.ambulances
            + self.fire_trucks
            + self.police_units
            + self.medical_teams
        )


@dataclass
class TrafficState:
    """City-wide traffic conditions."""

    congestion_index: float = 0.3
    average_speed_kmh: float = 35.0
    incidents_active: int = 0


@dataclass
class CityState:
    """Complete city state for the simulation."""

    name: str = "Aureon City"
    total_population: int = 500_000
    zones: list[CityZone] = field(default_factory=list)
    resources: ResourcePool = field(default_factory=ResourcePool)
    traffic: TrafficState = field(default_factory=TrafficState)
    power_grid_load_percent: float = 65.0
    water_system_pressure_psi: float = 60.0
    communications_uptime_percent: float = 99.9
