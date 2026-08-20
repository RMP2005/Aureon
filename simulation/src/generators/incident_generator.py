"""Emergency incident models and dynamic scenario generation."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..models.ambulance import AmbulanceCapability
from ..models.dynamic_city import get_zone_weights


class IncidentCategory(str, Enum):
    """Clinical and dispatch incident categories."""

    CARDIAC_ARREST = "cardiac_arrest"
    ACUTE_STROKE = "acute_stroke"
    MAJOR_TRAUMA = "major_trauma"
    RESPIRATORY_DISTRESS = "respiratory_distress"
    TRAFFIC_COLLISION = "traffic_collision"
    STRUCTURE_FIRE_CASUALTY = "structure_fire_casualty"
    MINOR_INJURY = "minor_injury"
    GENERAL_MEDICAL = "general_medical"


class IncidentSeverity(str, Enum):
    """Clinical severity triage level."""

    CRITICAL = "critical"      # Immediate life threat (Gold standard < 8 mins)
    HIGH = "high"              # Serious condition (< 12 mins)
    MODERATE = "moderate"      # Stable urgent (< 20 mins)
    LOW = "low"                # Non-urgent (< 30 mins)


@dataclass
class IncidentDefinition:
    """Template for generating specific types of emergencies."""

    category: IncidentCategory
    severity: IncidentSeverity
    required_capability: AmbulanceCapability
    target_response_time_sec: float
    base_on_scene_time_sec: float
    description: str


INCIDENT_PROFILES: dict[IncidentCategory, IncidentDefinition] = {
    IncidentCategory.CARDIAC_ARREST: IncidentDefinition(
        category=IncidentCategory.CARDIAC_ARREST,
        severity=IncidentSeverity.CRITICAL,
        required_capability=AmbulanceCapability.ALS,
        target_response_time_sec=480.0,
        base_on_scene_time_sec=600.0,
        description="Out-of-hospital cardiac arrest / ventricular fibrillation",
    ),
    IncidentCategory.ACUTE_STROKE: IncidentDefinition(
        category=IncidentCategory.ACUTE_STROKE,
        severity=IncidentSeverity.CRITICAL,
        required_capability=AmbulanceCapability.ALS,
        target_response_time_sec=600.0,
        base_on_scene_time_sec=480.0,
        description="Acute ischemic stroke within thrombolysis window",
    ),
    IncidentCategory.MAJOR_TRAUMA: IncidentDefinition(
        category=IncidentCategory.MAJOR_TRAUMA,
        severity=IncidentSeverity.CRITICAL,
        required_capability=AmbulanceCapability.ALS,
        target_response_time_sec=600.0,
        base_on_scene_time_sec=540.0,
        description="High-speed vehicular trauma / multi-system injury",
    ),
    IncidentCategory.RESPIRATORY_DISTRESS: IncidentDefinition(
        category=IncidentCategory.RESPIRATORY_DISTRESS,
        severity=IncidentSeverity.HIGH,
        required_capability=AmbulanceCapability.ALS,
        target_response_time_sec=720.0,
        base_on_scene_time_sec=420.0,
        description="Severe acute asthma / COPD exacerbation with hypoxia",
    ),
    IncidentCategory.TRAFFIC_COLLISION: IncidentDefinition(
        category=IncidentCategory.TRAFFIC_COLLISION,
        severity=IncidentSeverity.HIGH,
        required_capability=AmbulanceCapability.BLS,
        target_response_time_sec=720.0,
        base_on_scene_time_sec=480.0,
        description="Two-wheeler / four-wheeler collision with moderate trauma",
    ),
    IncidentCategory.STRUCTURE_FIRE_CASUALTY: IncidentDefinition(
        category=IncidentCategory.STRUCTURE_FIRE_CASUALTY,
        severity=IncidentSeverity.HIGH,
        required_capability=AmbulanceCapability.ALS,
        target_response_time_sec=600.0,
        base_on_scene_time_sec=540.0,
        description="Commercial building fire casualty with smoke inhalation",
    ),
    IncidentCategory.MINOR_INJURY: IncidentDefinition(
        category=IncidentCategory.MINOR_INJURY,
        severity=IncidentSeverity.LOW,
        required_capability=AmbulanceCapability.BLS,
        target_response_time_sec=1200.0,
        base_on_scene_time_sec=300.0,
        description="Isolated closed fracture / minor laceration",
    ),
    IncidentCategory.GENERAL_MEDICAL: IncidentDefinition(
        category=IncidentCategory.GENERAL_MEDICAL,
        severity=IncidentSeverity.MODERATE,
        required_capability=AmbulanceCapability.BLS,
        target_response_time_sec=900.0,
        base_on_scene_time_sec=360.0,
        description="Severe abdominal pain / high-grade fever with dehydration",
    ),
}


@dataclass
class Incident:
    """A specific emergency incident instance within the simulation."""

    id: str
    category: IncidentCategory
    severity: IncidentSeverity
    required_capability: AmbulanceCapability
    location_node_id: str
    location_name: str
    latitude: float
    longitude: float
    reported_at_tick: int
    reported_at_sim_time_sec: float
    target_response_time_sec: float = 480.0
    base_on_scene_time_sec: float = 480.0

    assigned_ambulance_id: str | None = None
    assigned_hospital_id: str | None = None
    dispatched_at_sec: float | None = None
    arrived_scene_at_sec: float | None = None
    departed_scene_at_sec: float | None = None
    arrived_hospital_at_sec: float | None = None
    handover_completed_at_sec: float | None = None

    capability_matched: bool = False
    hospital_suitability_score: float = 0.0
    is_completed: bool = False

    @property
    def response_time_seconds(self) -> float | None:
        """Time from report to ambulance arrival at the scene."""
        if self.arrived_scene_at_sec is not None:
            return self.arrived_scene_at_sec - self.reported_at_sim_time_sec
        return None

    @property
    def total_mission_time_seconds(self) -> float | None:
        """Total time from report until hospital handover."""
        if self.handover_completed_at_sec is not None:
            return self.handover_completed_at_sec - self.reported_at_sim_time_sec
        return None

    @property
    def met_response_target(self) -> bool:
        """Whether response time was within the clinical golden standard."""
        rt = self.response_time_seconds
        return rt is not None and rt <= self.target_response_time_sec


class ScenarioGenerator:
    """Generates realistic Poisson / rate-controlled emergency incident streams."""

    def __init__(
        self,
        node_ids_with_coords: list[tuple[str, str, float, float]],
        seed: int | None = 42,
    ) -> None:
        self.nodes = node_ids_with_coords
        self.rng = random.Random(seed)
        self._incident_counter = 0

    def generate_incident(
        self,
        tick: int,
        sim_time_sec: float,
        category: IncidentCategory | None = None,
        zone_weights: dict[str, float] | None = None,
    ) -> Incident:
        """Generate a single emergency incident.

        Args:
            tick: Simulation tick number.
            sim_time_sec: Simulation time in seconds.
            category: Override incident category (None for random).
            zone_weights: Zone name -> relative weight for location selection.
        """
        self._incident_counter += 1
        incident_id = f"inc_{self._incident_counter:04d}"

        if category is None:
            category_choices = [
                IncidentCategory.CARDIAC_ARREST,
                IncidentCategory.ACUTE_STROKE,
                IncidentCategory.MAJOR_TRAUMA,
                IncidentCategory.RESPIRATORY_DISTRESS,
                IncidentCategory.TRAFFIC_COLLISION,
                IncidentCategory.STRUCTURE_FIRE_CASUALTY,
                IncidentCategory.MINOR_INJURY,
                IncidentCategory.GENERAL_MEDICAL,
            ]
            weights = [0.18, 0.14, 0.15, 0.13, 0.15, 0.05, 0.10, 0.10]
            category = self.rng.choices(category_choices, weights=weights, k=1)[0]

        profile = INCIDENT_PROFILES[category]

        # Zone-weighted location selection
        if zone_weights and len(self.nodes) > 1:
            node_weights = []
            for node_id, node_name, lat, lon in self.nodes:
                # Look up zone from node metadata or default
                zone = "general"
                for zn, w in zone_weights.items():
                    if zn.lower() in node_name.lower():
                        zone = zn
                        break
                node_weights.append(zone_weights.get(zone, 1.0))

            chosen_idx = self.rng.choices(range(len(self.nodes)), weights=node_weights, k=1)[0]
            node_id, node_name, lat, lon = self.nodes[chosen_idx]
        else:
            node_id, node_name, lat, lon = self.rng.choice(self.nodes)

        return Incident(
            id=incident_id,
            category=category,
            severity=profile.severity,
            required_capability=profile.required_capability,
            location_node_id=node_id,
            location_name=node_name,
            latitude=lat,
            longitude=lon,
            reported_at_tick=tick,
            reported_at_sim_time_sec=sim_time_sec,
            target_response_time_sec=profile.target_response_time_sec,
            base_on_scene_time_sec=profile.base_on_scene_time_sec,
        )

    def generate_scenario_schedule(
        self,
        duration_minutes: float,
        incident_rate_per_hour: float = 12.0,
        use_dynamic_zones: bool = False,
    ) -> list[tuple[float, Incident]]:
        """Pre-generate a complete deterministic incident schedule over a time window.

        Args:
            duration_minutes: Simulation duration in minutes.
            incident_rate_per_hour: Average incidents per hour (Poisson rate).
            use_dynamic_zones: If True, apply time-of-day zone weighting.
        """
        total_seconds = duration_minutes * 60.0
        avg_interval_sec = 3600.0 / incident_rate_per_hour

        schedule: list[tuple[float, Incident]] = []
        current_time = self.rng.uniform(30.0, 120.0)

        tick = 0
        while current_time < total_seconds:
            tick = int(current_time)
            zone_weights = get_zone_weights(current_time) if use_dynamic_zones else None
            incident = self.generate_incident(
                tick=tick,
                sim_time_sec=current_time,
                zone_weights=zone_weights,
            )
            schedule.append((current_time, incident))
            interval = self.rng.expovariate(1.0 / avg_interval_sec)
            current_time += max(interval, 45.0)

        return schedule
