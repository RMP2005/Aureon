"""Emergency event models for urban simulation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from .city import GeoCoordinate


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


@dataclass
class AffectedArea:
    """Geographic area affected by an emergency."""

    center: GeoCoordinate
    radius_km: float = 0.5
    affected_population: int = 0
    affected_zone_ids: list[str] = field(default_factory=list)


@dataclass
class ResponseAllocation:
    """Resources allocated to an emergency response."""

    ambulances: int = 0
    fire_trucks: int = 0
    police_units: int = 0
    medical_teams: int = 0
    estimated_response_time_min: float = 0.0


@dataclass
class EmergencyEvent:
    """A single emergency event in the simulation."""

    id: str
    event_type: EmergencyType
    severity: SeverityLevel
    affected_area: AffectedArea
    status: EventStatus = EventStatus.DETECTED
    title: str = ""
    description: str = ""
    response: ResponseAllocation = field(default_factory=ResponseAllocation)
    casualties: int = 0
    property_damage_estimate_usd: float = 0.0
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
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
