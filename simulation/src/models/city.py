"""City state models for urban digital twin simulation.

Defines city zones, infrastructure, population distribution,
and resource availability.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


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


class GeoCoordinate(BaseModel):
    """Geographic coordinate."""

    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)


class CityZone(BaseModel):
    """A discrete zone within the city."""

    id: str
    name: str
    zone_type: ZoneType
    center: GeoCoordinate
    area_sq_km: float = Field(default=1.0, gt=0.0)
    population: int = Field(default=0, ge=0)
    population_density: float = Field(default=0.0, ge=0.0)
    infrastructure_status: InfrastructureStatus = InfrastructureStatus.OPERATIONAL


class ResourcePool(BaseModel):
    """Available emergency response resources."""

    ambulances: int = Field(default=0, ge=0)
    fire_trucks: int = Field(default=0, ge=0)
    police_units: int = Field(default=0, ge=0)
    medical_teams: int = Field(default=0, ge=0)
    shelters_capacity: int = Field(default=0, ge=0)

    @property
    def total_units(self) -> int:
        """Total available response units."""
        return (
            self.ambulances
            + self.fire_trucks
            + self.police_units
            + self.medical_teams
        )


class TrafficState(BaseModel):
    """City-wide traffic conditions."""

    congestion_index: float = Field(default=0.3, ge=0.0, le=1.0)
    average_speed_kmh: float = Field(default=35.0, ge=0.0)
    incidents_active: int = Field(default=0, ge=0)


class CityState(BaseModel):
    """Complete city state for the simulation."""

    name: str = "Aureon City"
    total_population: int = Field(default=500_000, ge=0)
    zones: list[CityZone] = Field(default_factory=list)
    resources: ResourcePool = Field(default_factory=ResourcePool)
    traffic: TrafficState = Field(default_factory=TrafficState)
    power_grid_load_percent: float = Field(default=65.0, ge=0.0, le=100.0)
    water_system_pressure_psi: float = Field(default=60.0, ge=0.0)
    communications_uptime_percent: float = Field(default=99.9, ge=0.0, le=100.0)
