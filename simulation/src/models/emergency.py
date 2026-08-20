"""Emergency event models for urban simulation.

Defines event types, severity levels, response protocols,
and event lifecycle management.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from src.models.city import GeoCoordinate


class EmergencyType(str, Enum):
    """Categories of emergency events."""

    FIRE = "fire"
    FLOOD = "flood"
    EARTHQUAKE = "earthquake"
    HAZMAT = "hazmat"
    MEDICAL = "medical"
    TRAFFIC_ACCIDENT = "traffic_accident"
    STRUCTURAL_COLLAPSE = "structural_collapse"
    POWER_OUTAGE = "power_outage"
    CIVIL_UNREST = "civil_unrest"
    WEATHER_EMERGENCY = "weather_emergency"


class SeverityLevel(str, Enum):
    """Emergency severity classifications."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"
    CATASTROPHIC = "catastrophic"


class EventStatus(str, Enum):
    """Emergency event lifecycle states."""

    DETECTED = "detected"
    CONFIRMED = "confirmed"
    RESPONDING = "responding"
    CONTAINED = "contained"
    RESOLVED = "resolved"


class AffectedArea(BaseModel):
    """Geographic area affected by an emergency."""

    center: GeoCoordinate
    radius_km: float = Field(default=0.5, gt=0.0)
    affected_population: int = Field(default=0, ge=0)
    affected_zone_ids: list[str] = Field(default_factory=list)


class ResponseAllocation(BaseModel):
    """Resources allocated to an emergency response."""

    ambulances: int = Field(default=0, ge=0)
    fire_trucks: int = Field(default=0, ge=0)
    police_units: int = Field(default=0, ge=0)
    medical_teams: int = Field(default=0, ge=0)
    estimated_response_time_min: float = Field(default=0.0, ge=0.0)


class EmergencyEvent(BaseModel):
    """A single emergency event in the simulation."""

    id: str
    event_type: EmergencyType
    severity: SeverityLevel
    status: EventStatus = EventStatus.DETECTED
    title: str = ""
    description: str = ""
    affected_area: AffectedArea
    response: ResponseAllocation = Field(default_factory=ResponseAllocation)
    casualties: int = Field(default=0, ge=0)
    property_damage_estimate_usd: float = Field(default=0.0, ge=0.0)
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        """Check if the event is still active."""
        return self.status not in (EventStatus.RESOLVED, EventStatus.CONTAINED)

    @property
    def severity_multiplier(self) -> float:
        """Numeric multiplier for severity-based calculations."""
        multipliers = {
            SeverityLevel.LOW: 1.0,
            SeverityLevel.MODERATE: 2.0,
            SeverityLevel.HIGH: 4.0,
            SeverityLevel.CRITICAL: 8.0,
            SeverityLevel.CATASTROPHIC: 16.0,
        }
        return multipliers[self.severity]
