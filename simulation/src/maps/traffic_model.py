"""Spatially correlated traffic model for the Bangalore simulation.

Traffic is modeled at *zone* granularity rather than independently per edge:

- Adjacent roads inside the same zone share a single congestion level.
- A congestion spike (e.g. an accident at Silk Board) raises congestion for
  every road within ``radius_km`` of the incident, with distance falloff.
- Time-of-day effects (Bangalore rush hours) apply to whole zones at once,
  never to individual edges.

The model is fully deterministic for a given seed: the stochastic component is
derived from ``(seed, zone, time bucket)`` instead of sequential RNG draws, so
replays reproduce identical traffic regardless of query order.

Performance: zone-level congestion (time-of-day factor x zone multiplier x
noise draw) is memoised per ``(zone, time bucket)``. A per-edge lookup is then
just a dictionary hit, a road-class constant, and a few multiplications.
"""

from __future__ import annotations

import logging
import math
import random
import uuid
from dataclasses import dataclass, field
from enum import Enum

from ..network.road_graph import RoadType, haversine_distance_km

logger = logging.getLogger("aureon.maps.traffic_model")

__all__ = [
    "TimePeriod",
    "TrafficZone",
    "CongestionEvent",
    "SpatialTrafficModel",
    "BANGALORE_ZONES",
]


class TimePeriod(str, Enum):
    """Bangalore-specific time-of-day traffic periods."""

    MORNING_PEAK = "morning_peak"  # 07:30 - 10:30
    MIDDAY = "midday"              # 10:30 - 16:30
    EVENING_PEAK = "evening_peak"  # 16:30 - 20:00
    NIGHT = "night"                # 20:00 - 07:30


TIME_PERIOD_FACTORS: dict[TimePeriod, float] = {
    TimePeriod.MORNING_PEAK: 1.8,
    TimePeriod.MIDDAY: 1.2,
    TimePeriod.EVENING_PEAK: 2.0,
    TimePeriod.NIGHT: 0.8,
}

_PERIOD_BOUNDS: tuple[tuple[float, float, TimePeriod], ...] = (
    (7.5, 10.5, TimePeriod.MORNING_PEAK),
    (10.5, 16.5, TimePeriod.MIDDAY),
    (16.5, 20.0, TimePeriod.EVENING_PEAK),
)


def _period_of_day(hour_of_day: float) -> TimePeriod:
    """Map an hour-of-day (0-24, may wrap) to its traffic period."""
    for start, end, period in _PERIOD_BOUNDS:
        if start <= hour_of_day < end:
            return period
    return TimePeriod.NIGHT


ROAD_TYPE_BASE_CONGESTION: dict[RoadType, float] = {
    RoadType.EXPRESSWAY: 0.8,
    RoadType.PRIMARY_ARTERIAL: 1.2,
    RoadType.SECONDARY: 1.4,
    RoadType.RESIDENTIAL: 1.0,
    RoadType.CONGESTED_CORRIDOR: 2.0,
}

GENERAL_ZONE_KEY = "__general__"

KM_PER_DEG_LATITUDE = 111.0

NOISE_FRACTION = 0.15
TIME_BUCKET_SEC = 300.0
MIN_CONGESTION = 0.4
MAX_CONGESTION = 4.0

_CACHE_MAX_ENTRIES = 4096
_CACHE_PRUNE_MARGIN_BUCKETS = 16


@dataclass(frozen=True)
class TrafficZone:
    """A geographic hotspot whose roads share correlated congestion."""

    name: str
    latitude: float
    longitude: float
    radius_km: float
    period_multipliers: dict[TimePeriod, float] = field(default_factory=dict)

    def multiplier_for(self, period: TimePeriod) -> float:
        """Zone-specific multiplier for a time period (1.0 if unspecified)."""
        return self.period_multipliers.get(period, 1.0)

    def contains(self, lat: float, lon: float) -> bool:
        """Whether a point falls inside this zone's radius."""
        return (
            haversine_distance_km(lat, lon, self.latitude, self.longitude)
            <= self.radius_km
        )


BANGALORE_ZONES: tuple[TrafficZone, ...] = (
    TrafficZone(
        name="silk_board_junction",
        latitude=12.9172,
        longitude=77.6229,
        radius_km=1.5,
        period_multipliers={
            TimePeriod.MORNING_PEAK: 2.5,
            TimePeriod.EVENING_PEAK: 2.5,
        },
    ),
    TrafficZone(
        name="orr_marathahalli",
        latitude=12.9569,
        longitude=77.7011,
        radius_km=2.0,
        period_multipliers={
            TimePeriod.MORNING_PEAK: 2.0,
            TimePeriod.EVENING_PEAK: 2.0,
        },
    ),
    TrafficZone(
        name="mg_road_cbd",
        latitude=12.9757,
        longitude=77.6068,
        radius_km=1.5,
        period_multipliers={
            TimePeriod.MORNING_PEAK: 1.5,
            TimePeriod.MIDDAY: 1.5,
            TimePeriod.EVENING_PEAK: 1.5,
        },
    ),
    TrafficZone(
        name="electronic_city",
        latitude=12.8452,
        longitude=77.6602,
        radius_km=2.5,
        period_multipliers={period: 0.9 for period in TimePeriod},
    ),
)


@dataclass
class CongestionEvent:
    """A temporary, spatially bounded congestion spike (e.g. an accident)."""

    event_id: str
    latitude: float
    longitude: float
    radius_km: float
    factor: float
    start_time_sec: float
    duration_sec: float

    @property
    def end_time_sec(self) -> float:
        return self.start_time_sec + self.duration_sec

    def is_active_at(self, sim_time_sec: float) -> bool:
        return self.start_time_sec <= sim_time_sec < self.end_time_sec

    def multiplier_at(self, lat: float, lon: float) -> float:
        """Attenuated multiplier at a point; linear falloff to 1.0 at the radius."""
        distance = haversine_distance_km(lat, lon, self.latitude, self.longitude)
        if distance >= self.radius_km:
            return 1.0
        intensity = 1.0 - distance / self.radius_km
        return 1.0 + (self.factor - 1.0) * intensity


class SpatialTrafficModel:
    """Fast, reproducible, spatially correlated congestion model.

    Usage:
        model = SpatialTrafficModel(seed=42)
        factor = model.get_edge_congestion(
            12.9172, 77.6229, 12.9200, 77.6250,
            RoadType.SECONDARY, sim_time_sec=18.0 * 3600,
        )
        event_id = model.apply_congestion_event(12.9172, 77.6229, 1.0, 3.0, 1800)
        model.remove_congestion_event(event_id)
    """

    def __init__(
        self,
        seed: int = 42,
        zones: tuple[TrafficZone, ...] | None = None,
    ) -> None:
        self._seed = seed
        self._zones: tuple[TrafficZone, ...] = (
            BANGALORE_ZONES if zones is None else tuple(zones)
        )
        self._events: dict[str, CongestionEvent] = {}
        self._zone_cache: dict[tuple[str, int], float] = {}
        self._last_sim_time: float = 0.0

    @property
    def seed(self) -> int:
        return self._seed

    @property
    def zones(self) -> tuple[TrafficZone, ...]:
        return self._zones

    def get_edge_congestion(
        self,
        source_lat: float,
        source_lon: float,
        target_lat: float,
        target_lon: float,
        road_type: RoadType,
        sim_time_sec: float,
    ) -> float:
        """Returns congestion multiplier (1.0 = free flow, 2.0 = double travel time)."""
        self._last_sim_time = sim_time_sec

        mid_lat = 0.5 * (source_lat + target_lat)
        mid_lon = 0.5 * (source_lon + target_lon)

        bucket = self._bucket_of(sim_time_sec)
        zone = self._zone_for(mid_lat, mid_lon)
        zone_key = zone.name if zone is not None else GENERAL_ZONE_KEY

        congestion = (
            ROAD_TYPE_BASE_CONGESTION.get(road_type, 1.0)
            * self._zone_level(zone_key, zone, bucket)
        )

        for event in self._events.values():
            if event.is_active_at(sim_time_sec):
                congestion *= event.multiplier_at(mid_lat, mid_lon)

        return min(max(congestion, MIN_CONGESTION), MAX_CONGESTION)

    def apply_congestion_event(
        self,
        lat: float,
        lon: float,
        radius_km: float,
        factor: float,
        duration_sec: float,
        start_time_sec: float | None = None,
        event_id: str | None = None,
    ) -> str:
        """Apply a temporary congestion spike at a location.

        Args:
            lat: Epicenter latitude.
            lon: Epicenter longitude.
            radius_km: Affected radius; impact decays linearly to the edge.
            factor: Multiplier at the epicenter (e.g. 3.0 triples travel time).
            duration_sec: How long the spike lasts.
            start_time_sec: Defaults to the last queried simulation time.
            event_id: Optional explicit id; auto-generated when omitted.

        Returns:
            The event id (pass it to :meth:`remove_congestion_event`).
        """
        if event_id is None:
            event_id = f"incident-{uuid.uuid4().hex[:8]}"
        if start_time_sec is None:
            start_time_sec = self._last_sim_time

        self._events[event_id] = CongestionEvent(
            event_id=event_id,
            latitude=lat,
            longitude=lon,
            radius_km=radius_km,
            factor=factor,
            start_time_sec=start_time_sec,
            duration_sec=duration_sec,
        )
        logger.debug(
            "Congestion event '%s' applied at (%.4f, %.4f) r=%.2fkm "
            "factor=%.2f for %.0fs",
            event_id, lat, lon, radius_km, factor, duration_sec,
        )
        return event_id

    def remove_congestion_event(self, event_id: str) -> bool:
        """Remove an active congestion event. Returns True if it existed."""
        removed = self._events.pop(event_id, None)
        if removed is not None:
            logger.debug("Congestion event '%s' removed", event_id)
        return removed is not None

    def active_events(self, sim_time_sec: float) -> list[CongestionEvent]:
        """All congestion events active at the given simulation time."""
        return [
            event
            for event in self._events.values()
            if event.is_active_at(sim_time_sec)
        ]

    def clear_events(self) -> None:
        """Remove every congestion event."""
        self._events.clear()

    @staticmethod
    def _bucket_of(sim_time_sec: float) -> int:
        return max(0, int(sim_time_sec // TIME_BUCKET_SEC))

    def _zone_for(self, lat: float, lon: float) -> TrafficZone | None:
        """Nearest zone containing the point, or None for 'general' areas."""
        best: TrafficZone | None = None
        best_dist = math.inf
        for zone in self._zones:
            if abs(lat - zone.latitude) > zone.radius_km / KM_PER_DEG_LATITUDE:
                continue
            dist = haversine_distance_km(lat, lon, zone.latitude, zone.longitude)
            if dist <= zone.radius_km and dist < best_dist:
                best, best_dist = zone, dist
        return best

    def _zone_level(self, zone_key: str, zone: TrafficZone | None, bucket: int) -> float:
        """Memoised zone-wide congestion: time-of-day x zone x noise draw."""
        cache_key = (zone_key, bucket)
        cached = self._zone_cache.get(cache_key)
        if cached is not None:
            return cached

        hour = ((bucket + 0.5) * TIME_BUCKET_SEC / 3600.0) % 24.0
        period = _period_of_day(hour)
        level = TIME_PERIOD_FACTORS[period]
        if zone is not None:
            level *= zone.multiplier_for(period)

        level *= 1.0 + self._zone_noise(zone_key, bucket)

        self._zone_cache[cache_key] = level
        self._maybe_prune_cache(bucket)
        return level

    def _zone_noise(self, zone_key: str, bucket: int) -> float:
        """Deterministic +/-15% draw shared by every edge in the zone/bucket."""
        rng = random.Random(f"{self._seed}|{zone_key}|{bucket}")
        return rng.uniform(-NOISE_FRACTION, NOISE_FRACTION)

    def _maybe_prune_cache(self, current_bucket: int) -> None:
        if len(self._zone_cache) <= _CACHE_MAX_ENTRIES:
            return
        stale_before = current_bucket - _CACHE_PRUNE_MARGIN_BUCKETS
        self._zone_cache = {
            key: value
            for key, value in self._zone_cache.items()
            if key[1] >= stale_before
        }
