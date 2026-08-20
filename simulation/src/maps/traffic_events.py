"""Temporary road conditions (closures, congestion spikes, construction) for dynamic routing.

Provides :class:`TrafficEventManager`, which injects time-boxed traffic events into a
:class:`RoadNetwork`, rerouting ambulances around blockages and slowdowns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from random import Random

from ..network.road_graph import RoadNetwork, haversine_distance_km


class TrafficEventType(str, Enum):
    """Classification of temporary road conditions."""

    ROAD_CLOSURE = "road_closure"
    CONGESTION_SPIKE = "congestion_spike"
    CONSTRUCTION = "construction"
    INCIDENT_BLOCKAGE = "incident_blockage"


ROAD_CLOSURE_CONGESTION_FACTOR = 25.0

EVENT_TYPE_WEIGHTS: list[tuple[TrafficEventType, float]] = [
    (TrafficEventType.CONGESTION_SPIKE, 40.0),
    (TrafficEventType.ROAD_CLOSURE, 25.0),
    (TrafficEventType.CONSTRUCTION, 20.0),
    (TrafficEventType.INCIDENT_BLOCKAGE, 15.0),
]

BANGALORE_HOTSPOTS: list[tuple[str, float, float]] = [
    ("Silk Board Junction", 12.9176, 77.6238),
    ("Hebbal Flyover", 13.0358, 77.5970),
    ("Marathahalli Bridge", 12.9591, 77.6974),
    ("Majestic / City Railway", 12.9781, 77.5696),
    ("Koramangala Sony World Signal", 12.9352, 77.6245),
    ("Domlur EGL Flyover", 12.9609, 77.6387),
    ("Old Airport Rd Junction", 12.9575, 77.6580),
    ("Electronic City Phase 1", 12.8399, 77.6770),
    ("Whitefield / ITPL", 12.9863, 77.7342),
    ("BTM Layout 2nd Stage", 12.9166, 77.6101),
]

BANGALORE_LAT_RANGE: tuple[float, float] = (12.82, 13.10)
BANGALORE_LON_RANGE: tuple[float, float] = (77.53, 77.74)


@dataclass
class TrafficEvent:
    """A time-boxed traffic condition affecting roads near a geographic center."""

    id: str
    event_type: TrafficEventType
    latitude: float
    longitude: float
    radius_km: float
    congestion_factor: float
    start_time_sec: float
    duration_sec: float
    affected_edge_ids: list[str] = field(default_factory=list)
    is_active: bool = True

    @property
    def end_time_sec(self) -> float:
        """Simulation time at which the event clears."""
        return self.start_time_sec + self.duration_sec

    def covers_time(self, current_time_sec: float) -> bool:
        """Return True if the event window contains ``current_time_sec``."""
        return self.start_time_sec <= current_time_sec < self.end_time_sec


@dataclass
class _EdgeSnapshot:
    """Original edge attributes captured before event application."""

    congestion_factor: float
    lanes: int


class TrafficEventManager:
    """Registers traffic events and applies them to a road network over time."""

    def __init__(self) -> None:
        self._events: dict[str, TrafficEvent] = {}
        self._edge_snapshots: dict[str, _EdgeSnapshot] = {}

    def add_event(self, event: TrafficEvent) -> str:
        """Register a traffic event. Returns event ID."""
        self._events[event.id] = event
        return event.id

    def remove_event(self, event_id: str) -> None:
        """Remove a traffic event."""
        self._events.pop(event_id, None)

    def get_active_events(self, current_time_sec: float) -> list[TrafficEvent]:
        """Get all currently active events."""
        active: list[TrafficEvent] = []
        for event in self._events.values():
            event.is_active = event.covers_time(current_time_sec)
            if event.is_active:
                active.append(event)
        return active

    def update_network(self, network: RoadNetwork, current_time_sec: float) -> int:
        """Apply all active events to the road network. Returns count of affected edges.

        Resets edges that are no longer affected.
        """
        active_events = self.get_active_events(current_time_sec)

        edge_max_factor: dict[str, float] = {}
        edge_has_construction: dict[str, bool] = {}

        for event in active_events:
            affected_ids = self._find_affected_edge_ids(network, event)
            event.affected_edge_ids = affected_ids
            for edge_id in affected_ids:
                current_max = edge_max_factor.get(edge_id, 0.0)
                if event.congestion_factor > current_max:
                    edge_max_factor[edge_id] = event.congestion_factor
                if event.event_type == TrafficEventType.CONSTRUCTION:
                    edge_has_construction[edge_id] = True

        for edge_id in list(self._edge_snapshots.keys()):
            if edge_id not in edge_max_factor:
                self._restore_edge(network, edge_id)

        for edge_id, factor in edge_max_factor.items():
            edge = network._edges_by_id.get(edge_id)
            if edge is None:
                continue
            snapshot = self._edge_snapshots.get(edge_id)
            if snapshot is None:
                snapshot = _EdgeSnapshot(
                    congestion_factor=edge.congestion_factor,
                    lanes=edge.lanes,
                )
                self._edge_snapshots[edge_id] = snapshot
            edge.congestion_factor = snapshot.congestion_factor * factor
            if edge_has_construction.get(edge_id, False):
                edge.lanes = max(1, snapshot.lanes - 1)
            else:
                edge.lanes = snapshot.lanes

        return len(edge_max_factor)

    def generate_random_events(
        self,
        num_events: int,
        sim_duration_sec: float,
        rng: Random,
    ) -> list[TrafficEvent]:
        """Generate random traffic events for a simulation run.

        Events are registered with this manager and returned.
        """
        generated: list[TrafficEvent] = []
        if num_events <= 0:
            return generated

        slot_width = sim_duration_sec / num_events

        for index in range(num_events):
            event_type = self._sample_event_type(rng)
            latitude, longitude = self._sample_location(rng)
            radius_km = rng.uniform(0.3, 2.0)
            duration_sec = rng.uniform(300.0, 3600.0)
            latest_start = max(0.0, sim_duration_sec - duration_sec)
            start_time_sec = min(index * slot_width + rng.uniform(0.0, slot_width), latest_start)

            event = TrafficEvent(
                id=f"traffic_event_{index:04d}",
                event_type=event_type,
                latitude=latitude,
                longitude=longitude,
                radius_km=radius_km,
                congestion_factor=self._factor_for_type(event_type, rng),
                start_time_sec=start_time_sec,
                duration_sec=duration_sec,
            )
            self.add_event(event)
            generated.append(event)

        return generated

    @staticmethod
    def _sample_event_type(rng: Random) -> TrafficEventType:
        roll = rng.random() * 100.0
        cumulative = 0.0
        for event_type, weight in EVENT_TYPE_WEIGHTS:
            cumulative += weight
            if roll < cumulative:
                return event_type
        return EVENT_TYPE_WEIGHTS[-1][0]

    @staticmethod
    def _sample_location(rng: Random) -> tuple[float, float]:
        if rng.random() < 0.7:
            _, lat, lon = rng.choice(BANGALORE_HOTSPOTS)
            return (
                lat + rng.uniform(-0.01, 0.01),
                lon + rng.uniform(-0.01, 0.01),
            )
        return (
            rng.uniform(*BANGALORE_LAT_RANGE),
            rng.uniform(*BANGALORE_LON_RANGE),
        )

    @staticmethod
    def _factor_for_type(event_type: TrafficEventType, rng: Random) -> float:
        if event_type == TrafficEventType.ROAD_CLOSURE:
            return ROAD_CLOSURE_CONGESTION_FACTOR
        if event_type == TrafficEventType.CONGESTION_SPIKE:
            return rng.uniform(3.0, 5.0)
        if event_type == TrafficEventType.CONSTRUCTION:
            return rng.uniform(1.5, 2.0)
        return rng.uniform(3.0, 6.0)

    @staticmethod
    def _find_affected_edge_ids(
        network: RoadNetwork,
        event: TrafficEvent,
    ) -> list[str]:
        affected: list[str] = []
        node_coords: dict[str, tuple[float, float]] = {}

        def coords_for(node_id: str) -> tuple[float, float] | None:
            cached = node_coords.get(node_id)
            if cached is not None:
                return cached
            node = network.nodes.get(node_id)
            if node is None:
                return None
            coords = (node.latitude, node.longitude)
            node_coords[node_id] = coords
            return coords

        for edge in network._edges_by_id.values():
            source_coords = coords_for(edge.source_id)
            target_coords = coords_for(edge.target_id)
            if source_coords is not None and haversine_distance_km(
                event.latitude, event.longitude, source_coords[0], source_coords[1]
            ) <= event.radius_km:
                affected.append(edge.id)
                continue
            if target_coords is not None and haversine_distance_km(
                event.latitude, event.longitude, target_coords[0], target_coords[1]
            ) <= event.radius_km:
                affected.append(edge.id)

        return affected

    def _restore_edge(self, network: RoadNetwork, edge_id: str) -> None:
        snapshot = self._edge_snapshots.pop(edge_id, None)
        if snapshot is None:
            return
        edge = network._edges_by_id.get(edge_id)
        if edge is not None:
            edge.congestion_factor = snapshot.congestion_factor
            edge.lanes = snapshot.lanes
