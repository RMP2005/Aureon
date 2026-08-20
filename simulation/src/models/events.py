"""Event-level emergency modeling with uncertainty, clusters, and rich representations.

Replaces simple Poisson incident generation with realistic emergency
event clusters that model spatial/temporal correlations.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..models.ambulance import AmbulanceCapability


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

    CRITICAL = "critical"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


SEVERITY_PRIORITY: dict[IncidentSeverity, int] = {
    IncidentSeverity.CRITICAL: 0,
    IncidentSeverity.HIGH: 1,
    IncidentSeverity.MODERATE: 2,
    IncidentSeverity.LOW: 3,
}


class EmergencyClusterType(str, Enum):
    """Types of emergency event clusters."""

    TRAFFIC_ACCIDENT_HOTSPOT = "traffic_accident_hotspot"
    MEDICAL_EMERGENCY_ZONE = "medical_emergency_zone"
    INDUSTRIAL_INCIDENT = "industrial_incident"
    RESIDENTIAL_MEDICAL = "residential_medical"
    COMMERCIAL_TRAUMA = "commercial_trauma"


@dataclass
class IncidentLocationDistribution:
    """Probabilistic location model for an incident cluster.

    Instead of fixed nodes, incidents are generated from a
    weighted distribution over nearby nodes.
    """

    center_node_id: str
    center_lat: float
    center_lon: float
    radius_km: float = 2.0
    node_weights: dict[str, float] = field(default_factory=dict)

    def sample_location(
        self, rng: random.Random, all_nodes: dict[str, Any]
    ) -> tuple[str, str, float, float]:
        """Sample a location from this distribution.

        Returns (node_id, node_name, lat, lon).
        """
        if not self.node_weights:
            # Fallback: find nearest node
            best_id = self.center_node_id
            best_name = "Unknown"
            for nid, node in all_nodes.items():
                d = _haversine(self.center_lat, self.center_lon, node.latitude, node.longitude)
                if d <= self.radius_km:
                    self.node_weights[nid] = max(0.01, 1.0 - d / self.radius_km)
            if not self.node_weights:
                self.node_weights[self.center_node_id] = 1.0

        ids = list(self.node_weights.keys())
        weights = list(self.node_weights.values())
        chosen_id = rng.choices(ids, weights=weights, k=1)[0]
        chosen_node = all_nodes[chosen_id]
        return chosen_id, chosen_node.name, chosen_node.latitude, chosen_node.longitude


@dataclass
class IncidentProfile:
    """Template for a type of emergency incident with uncertainty."""

    category: IncidentCategory
    base_severity: IncidentSeverity
    severity_distribution: dict[IncidentSeverity, float] = field(default_factory=dict)
    required_capability: AmbulanceCapability = AmbulanceCapability.BLS
    target_response_time_sec: float = 600.0
    base_on_scene_time_sec: float = 480.0
    description: str = ""

    def sample_severity(self, rng: random.Random) -> IncidentSeverity:
        """Sample actual severity from uncertainty distribution."""
        if not self.severity_distribution:
            return self.base_severity
        severities = list(self.severity_distribution.keys())
        weights = list(self.severity_distribution.values())
        return rng.choices(severities, weights=weights, k=1)[0]


# Incident profiles with severity uncertainty
INCIDENT_PROFILES: dict[IncidentCategory, IncidentProfile] = {
    IncidentCategory.CARDIAC_ARREST: IncidentProfile(
        category=IncidentCategory.CARDIAC_ARREST,
        base_severity=IncidentSeverity.CRITICAL,
        severity_distribution={IncidentSeverity.CRITICAL: 0.85, IncidentSeverity.HIGH: 0.15},
        required_capability=AmbulanceCapability.ALS,
        target_response_time_sec=480.0,
        base_on_scene_time_sec=600.0,
        description="Out-of-hospital cardiac arrest / ventricular fibrillation",
    ),
    IncidentCategory.ACUTE_STROKE: IncidentProfile(
        category=IncidentCategory.ACUTE_STROKE,
        base_severity=IncidentSeverity.CRITICAL,
        severity_distribution={IncidentSeverity.CRITICAL: 0.7, IncidentSeverity.HIGH: 0.3},
        required_capability=AmbulanceCapability.ALS,
        target_response_time_sec=600.0,
        base_on_scene_time_sec=480.0,
        description="Acute ischemic stroke within thrombolysis window",
    ),
    IncidentCategory.MAJOR_TRAUMA: IncidentProfile(
        category=IncidentCategory.MAJOR_TRAUMA,
        base_severity=IncidentSeverity.CRITICAL,
        severity_distribution={IncidentSeverity.CRITICAL: 0.6, IncidentSeverity.HIGH: 0.3, IncidentSeverity.MODERATE: 0.1},
        required_capability=AmbulanceCapability.ALS,
        target_response_time_sec=600.0,
        base_on_scene_time_sec=540.0,
        description="High-speed vehicular trauma / multi-system injury",
    ),
    IncidentCategory.RESPIRATORY_DISTRESS: IncidentProfile(
        category=IncidentCategory.RESPIRATORY_DISTRESS,
        base_severity=IncidentSeverity.HIGH,
        severity_distribution={IncidentSeverity.HIGH: 0.7, IncidentSeverity.MODERATE: 0.2, IncidentSeverity.CRITICAL: 0.1},
        required_capability=AmbulanceCapability.ALS,
        target_response_time_sec=720.0,
        base_on_scene_time_sec=420.0,
        description="Severe acute asthma / COPD exacerbation with hypoxia",
    ),
    IncidentCategory.TRAFFIC_COLLISION: IncidentProfile(
        category=IncidentCategory.TRAFFIC_COLLISION,
        base_severity=IncidentSeverity.HIGH,
        severity_distribution={IncidentSeverity.HIGH: 0.4, IncidentSeverity.MODERATE: 0.35, IncidentSeverity.LOW: 0.15, IncidentSeverity.CRITICAL: 0.1},
        required_capability=AmbulanceCapability.BLS,
        target_response_time_sec=720.0,
        base_on_scene_time_sec=480.0,
        description="Two-wheeler / four-wheeler collision with moderate trauma",
    ),
    IncidentCategory.STRUCTURE_FIRE_CASUALTY: IncidentProfile(
        category=IncidentCategory.STRUCTURE_FIRE_CASUALTY,
        base_severity=IncidentSeverity.HIGH,
        severity_distribution={IncidentSeverity.HIGH: 0.5, IncidentSeverity.CRITICAL: 0.3, IncidentSeverity.MODERATE: 0.2},
        required_capability=AmbulanceCapability.ALS,
        target_response_time_sec=600.0,
        base_on_scene_time_sec=540.0,
        description="Commercial building fire casualty with smoke inhalation",
    ),
    IncidentCategory.MINOR_INJURY: IncidentProfile(
        category=IncidentCategory.MINOR_INJURY,
        base_severity=IncidentSeverity.LOW,
        severity_distribution={IncidentSeverity.LOW: 0.8, IncidentSeverity.MODERATE: 0.2},
        required_capability=AmbulanceCapability.BLS,
        target_response_time_sec=1200.0,
        base_on_scene_time_sec=300.0,
        description="Isolated closed fracture / minor laceration",
    ),
    IncidentCategory.GENERAL_MEDICAL: IncidentProfile(
        category=IncidentCategory.GENERAL_MEDICAL,
        base_severity=IncidentSeverity.MODERATE,
        severity_distribution={IncidentSeverity.MODERATE: 0.6, IncidentSeverity.HIGH: 0.25, IncidentSeverity.LOW: 0.15},
        required_capability=AmbulanceCapability.BLS,
        target_response_time_sec=900.0,
        base_on_scene_time_sec=360.0,
        description="Severe abdominal pain / high-grade fever with dehydration",
    ),
}


@dataclass
class EmergencyCluster:
    """A spatial/temporal cluster of related emergency events.

    Models realistic patterns like:
    - Highway accidents cluster near intersections during rush hour
    - Medical emergencies cluster in residential zones
    - Fire incidents cluster in industrial areas
    """

    cluster_type: EmergencyClusterType
    location: IncidentLocationDistribution
    peak_hour_start: float  # Hour of day (0-24)
    peak_hour_end: float
    peak_rate_multiplier: float = 2.5
    base_rate: float = 0.3  # Incidents per hour at this cluster
    dominant_categories: list[IncidentCategory] = field(default_factory=list)
    dominant_severity: IncidentSeverity = IncidentSeverity.MODERATE

    def rate_at_hour(self, hour: float) -> float:
        """Get incident rate at this cluster for a given hour."""
        if self.peak_hour_start <= hour <= self.peak_hour_end:
            return self.base_rate * self.peak_rate_multiplier
        # Smooth transition
        dist_to_peak = min(
            abs(hour - self.peak_hour_start),
            abs(hour - self.peak_hour_end),
            24.0 - abs(hour - self.peak_hour_start),
            24.0 - abs(hour - self.peak_hour_end),
        )
        decay = max(0.3, 1.0 - dist_to_peak / 6.0)
        return self.base_rate * decay


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

    # Uncertainty / confidence fields
    severity_confidence: float = 1.0  # 1.0 = certain, lower = uncertain
    location_confidence: float = 1.0
    cluster_id: str | None = None  # Which cluster spawned this

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
        if self.arrived_scene_at_sec is not None:
            return self.arrived_scene_at_sec - self.reported_at_sim_time_sec
        return None

    @property
    def total_mission_time_seconds(self) -> float | None:
        if self.handover_completed_at_sec is not None:
            return self.handover_completed_at_sec - self.reported_at_sim_time_sec
        return None

    @property
    def met_response_target(self) -> bool:
        rt = self.response_time_seconds
        return rt is not None and rt <= self.target_response_time_sec


# ---------------------------------------------------------------------------
# Default Bangalore emergency clusters
# ---------------------------------------------------------------------------

def get_default_bangalore_clusters() -> list[EmergencyCluster]:
    """Define realistic emergency clusters for Bangalore."""
    return [
        # Traffic accidents on ORR (Outer Ring Road) corridors
        EmergencyCluster(
            cluster_type=EmergencyClusterType.TRAFFIC_ACCIDENT_HOTSPOT,
            location=IncidentLocationDistribution(
                center_node_id="node_silk_board", center_lat=12.9176, center_lon=77.6238,
                radius_km=3.0,
            ),
            peak_hour_start=7.5, peak_hour_end=10.5,
            peak_rate_multiplier=3.0, base_rate=0.4,
            dominant_categories=[IncidentCategory.TRAFFIC_COLLISION, IncidentCategory.MAJOR_TRAUMA],
            dominant_severity=IncidentSeverity.HIGH,
        ),
        EmergencyCluster(
            cluster_type=EmergencyClusterType.TRAFFIC_ACCIDENT_HOTSPOT,
            location=IncidentLocationDistribution(
                center_node_id="node_hebbal_flyover", center_lat=13.0358, center_lon=77.5970,
                radius_km=2.5,
            ),
            peak_hour_start=17.0, peak_hour_end=20.0,
            peak_rate_multiplier=2.8, base_rate=0.35,
            dominant_categories=[IncidentCategory.TRAFFIC_COLLISION],
            dominant_severity=IncidentSeverity.MODERATE,
        ),
        EmergencyCluster(
            cluster_type=EmergencyClusterType.TRAFFIC_ACCIDENT_HOTSPOT,
            location=IncidentLocationDistribution(
                center_node_id="node_marathahalli", center_lat=12.9591, center_lon=77.6974,
                radius_km=3.5,
            ),
            peak_hour_start=8.0, peak_hour_end=11.0,
            peak_rate_multiplier=2.5, base_rate=0.3,
            dominant_categories=[IncidentCategory.TRAFFIC_COLLISION, IncidentCategory.MINOR_INJURY],
        ),

        # Medical emergencies in residential/commercial zones
        EmergencyCluster(
            cluster_type=EmergencyClusterType.RESIDENTIAL_MEDICAL,
            location=IncidentLocationDistribution(
                center_node_id="node_koramangala_sony", center_lat=12.9352, center_lon=77.6245,
                radius_km=2.0,
            ),
            peak_hour_start=6.0, peak_hour_end=22.0,
            peak_rate_multiplier=1.5, base_rate=0.25,
            dominant_categories=[IncidentCategory.CARDIAC_ARREST, IncidentCategory.GENERAL_MEDICAL,
                                IncidentCategory.RESPIRATORY_DISTRESS],
        ),
        EmergencyCluster(
            cluster_type=EmergencyClusterType.RESIDENTIAL_MEDICAL,
            location=IncidentLocationDistribution(
                center_node_id="node_indiranagar", center_lat=12.9719, center_lon=77.6412,
                radius_km=2.0,
            ),
            peak_hour_start=5.0, peak_hour_end=23.0,
            peak_rate_multiplier=1.8, base_rate=0.2,
            dominant_categories=[IncidentCategory.CARDIAC_ARREST, IncidentCategory.ACUTE_STROKE,
                                IncidentCategory.GENERAL_MEDICAL],
        ),

        # Commercial trauma in CBD
        EmergencyCluster(
            cluster_type=EmergencyClusterType.COMMERCIAL_TRAUMA,
            location=IncidentLocationDistribution(
                center_node_id="node_mg_road", center_lat=12.9756, center_lon=77.6066,
                radius_km=1.5,
            ),
            peak_hour_start=10.0, peak_hour_end=22.0,
            peak_rate_multiplier=2.0, base_rate=0.2,
            dominant_categories=[IncidentCategory.MINOR_INJURY, IncidentCategory.GENERAL_MEDICAL,
                                IncidentCategory.STRUCTURE_FIRE_CASUALTY],
        ),

        # Whitefield IT corridor (mixed traffic + medical)
        EmergencyCluster(
            cluster_type=EmergencyClusterType.MEDICAL_EMERGENCY_ZONE,
            location=IncidentLocationDistribution(
                center_node_id="node_whitefield_itpl", center_lat=12.9863, center_lon=77.7342,
                radius_km=3.0,
            ),
            peak_hour_start=9.0, peak_hour_end=19.0,
            peak_rate_multiplier=2.0, base_rate=0.25,
            dominant_categories=[IncidentCategory.GENERAL_MEDICAL, IncidentCategory.TRAFFIC_COLLISION],
        ),

        # Electronic City (industrial/IT)
        EmergencyCluster(
            cluster_type=EmergencyClusterType.INDUSTRIAL_INCIDENT,
            location=IncidentLocationDistribution(
                center_node_id="node_electronic_city", center_lat=12.8399, center_lon=77.6770,
                radius_km=2.5,
            ),
            peak_hour_start=8.0, peak_hour_end=18.0,
            peak_rate_multiplier=1.8, base_rate=0.15,
            dominant_categories=[IncidentCategory.MINOR_INJURY, IncidentCategory.RESPIRATORY_DISTRESS],
        ),
    ]


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in km between two lat/lon points."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
