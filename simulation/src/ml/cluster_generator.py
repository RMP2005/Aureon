"""Cluster-based incident generation using event-level emergency models.

Replaces uniform Poisson generation with realistic spatial/temporal
emergency clusters.
"""

from __future__ import annotations

import logging
import math
import random
from dataclasses import dataclass

from ..models.events import (
    INCIDENT_PROFILES,
    EmergencyCluster,
    Incident as RichIncident,
    IncidentCategory,
    IncidentLocationDistribution,
    IncidentProfile,
    IncidentSeverity,
    SEVERITY_PRIORITY,
    get_default_bangalore_clusters,
)
from ..models.ambulance import AmbulanceCapability
from ..network.road_graph import RoadNetwork

logger = logging.getLogger("aureon.ml.cluster_generator")


@dataclass
class GeneratedIncident:
    """Wrapper that bridges rich Incident model to simulation engine."""

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
    target_response_time_sec: float
    base_on_scene_time_sec: float
    severity_confidence: float
    location_confidence: float
    cluster_id: str


class ClusterIncidentGenerator:
    """Generates incidents from spatial/temporal emergency clusters.

    Instead of uniform random placement, incidents emerge from
    realistic clusters with time-varying rates.
    """

    def __init__(
        self,
        road_network: RoadNetwork,
        clusters: list[EmergencyCluster] | None = None,
        seed: int = 42,
    ) -> None:
        self.road_network = road_network
        self.clusters = clusters or get_default_bangalore_clusters()
        self.rng = random.Random(seed)
        self._incident_counter = 0

        # Background rate (incidents/hour not from any cluster)
        self.background_rate = 1.0  # 1 background incident per hour
        self.total_base_rate = self.background_rate + sum(c.base_rate for c in self.clusters)

    def _sample_category(self, cluster: EmergencyCluster | None) -> IncidentCategory:
        """Sample incident category, biased by cluster type."""
        if cluster and cluster.dominant_categories:
            # 70% from dominant categories, 30% general pool
            if self.rng.random() < 0.7:
                return self.rng.choice(cluster.dominant_categories)

        # General pool
        categories = list(IncidentCategory)
        weights = [0.18, 0.14, 0.15, 0.13, 0.15, 0.05, 0.10, 0.10]
        return self.rng.choices(categories, weights=weights, k=1)[0]

    def generate_incident(
        self,
        tick: int,
        sim_time_sec: float,
    ) -> GeneratedIncident:
        """Generate a single incident at the current simulation time."""
        self._incident_counter += 1
        incident_id = f"inc_{self._incident_counter:04d}"

        hour_of_day = (8 + sim_time_sec / 3600.0) % 24

        # Select source: cluster or background
        cluster = None
        if self.rng.random() < 0.85:  # 85% from clusters
            # Weight clusters by their current rate
            rates = [c.rate_at_hour(hour_of_day) for c in self.clusters]
            total = sum(rates)
            if total > 0:
                probs = [r / total for r in rates]
                cluster = self.rng.choices(self.clusters, weights=probs, k=1)[0]

        # Sample category
        category = self._sample_category(cluster)
        profile = INCIDENT_PROFILES[category]

        # Sample severity with uncertainty
        severity = profile.sample_severity(self.rng)
        severity_confidence = 0.8 if severity != profile.base_severity else 1.0

        # Location from cluster distribution or random network node
        if cluster:
            node_id, node_name, lat, lon = cluster.location.sample_location(
                self.rng, self.road_network.nodes,
            )
            location_confidence = cluster.location.radius_km / 5.0  # Wider = less confident
            cluster_id = f"cluster_{self.clusters.index(cluster)}"
        else:
            # Background: random non-hospital, non-station node
            candidates = [
                n for n in self.road_network.nodes.values()
                if not n.is_hospital and not n.is_station
            ]
            if candidates:
                node = self.rng.choice(candidates)
                node_id, node_name, lat, lon = node.id, node.name, node.latitude, node.longitude
            else:
                node = list(self.road_network.nodes.values())[0]
                node_id, node_name, lat, lon = node.id, node.name, node.latitude, node.longitude
            location_confidence = 0.5
            cluster_id = "background"

        return GeneratedIncident(
            id=incident_id,
            category=category,
            severity=severity,
            required_capability=profile.required_capability,
            location_node_id=node_id,
            location_name=node_name,
            latitude=lat,
            longitude=lon,
            reported_at_tick=tick,
            reported_at_sim_time_sec=sim_time_sec,
            target_response_time_sec=profile.target_response_time_sec,
            base_on_scene_time_sec=profile.base_on_scene_time_sec,
            severity_confidence=severity_confidence,
            location_confidence=location_confidence,
            cluster_id=cluster_id,
        )

    def generate_schedule(
        self,
        duration_minutes: float,
        incident_rate_per_hour: float | None = None,
    ) -> list[tuple[float, GeneratedIncident]]:
        """Generate a complete incident schedule from clusters.

        The effective rate varies by time of day based on cluster activity.
        """
        total_seconds = duration_minutes * 60.0
        effective_rate = incident_rate_per_hour or self.total_base_rate

        schedule: list[tuple[float, GeneratedIncident]] = []
        current_time = self.rng.uniform(30.0, 120.0)

        while current_time < total_seconds:
            tick = int(current_time)
            incident = self.generate_incident(tick=tick, sim_time_sec=current_time)
            schedule.append((current_time, incident))

            # Inter-arrival time: exponential with rate scaling
            avg_interval = 3600.0 / effective_rate
            interval = self.rng.expovariate(1.0 / avg_interval)
            current_time += max(interval, 45.0)

        return schedule

    @staticmethod
    def to_simulation_schedule(
        cluster_schedule: list[tuple[float, GeneratedIncident]],
    ) -> list[tuple[float, RichIncident]]:
        """Convert GeneratedIncidents to the simulation engine's Incident format."""
        result = []
        for time_sec, gen_inc in cluster_schedule:
            inc = RichIncident(
                id=gen_inc.id,
                category=gen_inc.category,
                severity=gen_inc.severity,
                required_capability=gen_inc.required_capability,
                location_node_id=gen_inc.location_node_id,
                location_name=gen_inc.location_name,
                latitude=gen_inc.latitude,
                longitude=gen_inc.longitude,
                reported_at_tick=gen_inc.reported_at_tick,
                reported_at_sim_time_sec=gen_inc.reported_at_sim_time_sec,
                target_response_time_sec=gen_inc.target_response_time_sec,
                base_on_scene_time_sec=gen_inc.base_on_scene_time_sec,
            )
            result.append((time_sec, inc))
        return result
