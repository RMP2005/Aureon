"""Dynamic traffic and incident distribution models for city-wide simulation."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

from ..network.road_graph import RoadNetwork, RoadType


class TimePeriod(str, Enum):
    """Time-of-day periods for Bangalore traffic patterns."""

    LATE_NIGHT = "late_night"      # 00:00 - 05:59
    EARLY_MORNING = "early_morning"  # 06:00 - 08:59
    MORNING_PEAK = "morning_peak"    # 09:00 - 11:59
    MIDDAY = "midday"                # 12:00 - 16:59
    EVENING_PEAK = "evening_peak"    # 17:00 - 20:59
    NIGHT = "night"                  # 21:00 - 23:59


# Bangalore-specific traffic congestion multipliers by road type and time period
# Factor > 1.0 means slower travel (more congestion)
# Factor < 1.0 means faster travel (less congestion)
CONGESTION_PROFILES: dict[TimePeriod, dict[RoadType, float]] = {
    TimePeriod.LATE_NIGHT: {
        RoadType.EXPRESSWAY: 0.7,
        RoadType.PRIMARY_ARTERIAL: 0.8,
        RoadType.SECONDARY: 0.9,
        RoadType.RESIDENTIAL: 0.9,
        RoadType.CONGESTED_CORRIDOR: 0.8,
    },
    TimePeriod.EARLY_MORNING: {
        RoadType.EXPRESSWAY: 1.2,
        RoadType.PRIMARY_ARTERIAL: 1.4,
        RoadType.SECONDARY: 1.2,
        RoadType.RESIDENTIAL: 1.1,
        RoadType.CONGESTED_CORRIDOR: 1.5,
    },
    TimePeriod.MORNING_PEAK: {
        RoadType.EXPRESSWAY: 2.2,
        RoadType.PRIMARY_ARTERIAL: 2.5,
        RoadType.SECONDARY: 2.0,
        RoadType.RESIDENTIAL: 1.5,
        RoadType.CONGESTED_CORRIDOR: 3.0,
    },
    TimePeriod.MIDDAY: {
        RoadType.EXPRESSWAY: 1.3,
        RoadType.PRIMARY_ARTERIAL: 1.5,
        RoadType.SECONDARY: 1.4,
        RoadType.RESIDENTIAL: 1.2,
        RoadType.CONGESTED_CORRIDOR: 1.8,
    },
    TimePeriod.EVENING_PEAK: {
        RoadType.EXPRESSWAY: 2.5,
        RoadType.PRIMARY_ARTERIAL: 2.8,
        RoadType.SECONDARY: 2.2,
        RoadType.RESIDENTIAL: 1.6,
        RoadType.CONGESTED_CORRIDOR: 3.5,
    },
    TimePeriod.NIGHT: {
        RoadType.EXPRESSWAY: 0.9,
        RoadType.PRIMARY_ARTERIAL: 1.0,
        RoadType.SECONDARY: 1.1,
        RoadType.RESIDENTIAL: 1.0,
        RoadType.CONGESTED_CORRIDOR: 1.2,
    },
}


def get_time_period(sim_time_sec: float) -> TimePeriod:
    """Determine the time period from simulation seconds (starting at 08:00 AM).

    The simulation clock starts at 8:00 AM (typical Bangalore workday start).
    sim_time_sec=0 corresponds to 08:00.
    """
    # Simulation starts at 08:00
    hour_of_day = (8 + sim_time_sec / 3600.0) % 24

    if hour_of_day < 6:
        return TimePeriod.LATE_NIGHT
    elif hour_of_day < 9:
        return TimePeriod.EARLY_MORNING
    elif hour_of_day < 12:
        return TimePeriod.MORNING_PEAK
    elif hour_of_day < 17:
        return TimePeriod.MIDDAY
    elif hour_of_day < 21:
        return TimePeriod.EVENING_PEAK
    else:
        return TimePeriod.NIGHT


def interpolate_congestion(
    time_sec_a: float,
    time_sec_b: float,
    road_type: RoadType,
) -> float:
    """Smoothly interpolate congestion factor between two time points.

    Uses cosine interpolation to avoid abrupt congestion jumps at period boundaries.
    """
    period_a = get_time_period(time_sec_a)
    period_b = get_time_period(time_sec_b)

    if period_a == period_b:
        return CONGESTION_PROFILES[period_a][road_type]

    # Smooth interpolation using cosine curve
    hour_a = (8 + time_sec_a / 3600.0) % 24
    hour_b = (8 + time_sec_b / 3600.0) % 24

    # Normalize progress within the transition (0 to 1)
    if time_sec_b > time_sec_a:
        progress = min((hour_b - hour_a) % 24 / 3.0, 1.0)  # 3-hour transition
    else:
        progress = 0.0

    factor_a = CONGESTION_PROFILES[period_a][road_type]
    factor_b = CONGESTION_PROFILES[period_b][road_type]

    # Cosine interpolation for smooth transition
    mu = (1 - math.cos(progress * math.pi)) / 2.0
    return factor_a + (factor_b - factor_a) * mu


class DynamicTrafficModel:
    """Time-of-day dynamic traffic congestion model for Bangalore roads.

    Updates road network congestion factors based on simulation time
    to create realistic rush-hour and off-peak conditions.
    """

    def __init__(
        self,
        road_network: RoadNetwork,
        override_period: TimePeriod | None = None,
    ) -> None:
        self.road_network = road_network
        # Scenario Library (Phase 10E-2): when set, congestion is pinned to a
        # single time period for the whole run (e.g. evening peak) instead of
        # following the simulation clock.
        self.override_period = override_period
        self._last_update_sec: float = -1.0
        self._current_period: TimePeriod | None = None

    def update(self, sim_time_sec: float) -> None:
        """Update road network congestion factors for current simulation time.

        Only recalculates when the time period changes to avoid redundant work.
        """
        new_period = self.override_period or get_time_period(sim_time_sec)
        if new_period == self._current_period:
            return

        self._current_period = new_period
        self._last_update_sec = sim_time_sec

        profile = CONGESTION_PROFILES[new_period]
        for node_id, edges in self.road_network._adjacency.items():
            for edge in edges:
                edge.congestion_factor = profile.get(edge.road_type, 1.0)

    def get_congestion_at_time(self, sim_time_sec: float, road_type: RoadType) -> float:
        """Get the congestion factor for a specific road type at given time."""
        period = get_time_period(sim_time_sec)
        return CONGESTION_PROFILES[period][road_type]

    def get_current_period(self, sim_time_sec: float) -> TimePeriod:
        """Get the current time period."""
        return get_time_period(sim_time_sec)


# ---------------------------------------------------------------------------
# Zone-weighted incident distribution
# ---------------------------------------------------------------------------

# Bangalore zone incident weights by time period (relative probability of incidents)
# Higher weight = more incidents in that zone during that time
ZONE_WEIGHT_PROFILES: dict[TimePeriod, dict[str, float]] = {
    TimePeriod.LATE_NIGHT: {
        "Indiranagar": 0.8,
        "Koramangala": 0.7,
        "Whitefield": 0.5,
        "Electronic City": 0.4,
        "Hebbal": 0.6,
        "Yeshwanthpur": 0.5,
    },
    TimePeriod.EARLY_MORNING: {
        "Indiranagar": 1.0,
        "Koramangala": 1.0,
        "Whitefield": 0.8,
        "Electronic City": 0.7,
        "Hebbal": 0.9,
        "Yeshwanthpur": 0.8,
    },
    TimePeriod.MORNING_PEAK: {
        "Indiranagar": 1.5,
        "Koramangala": 1.8,
        "Whitefield": 1.4,
        "Electronic City": 1.3,
        "Hebbal": 1.6,
        "Yeshwanthpur": 1.2,
    },
    TimePeriod.MIDDAY: {
        "Indiranagar": 1.2,
        "Koramangala": 1.3,
        "Whitefield": 1.1,
        "Electronic City": 1.0,
        "Hebbal": 1.1,
        "Yeshwanthpur": 1.0,
    },
    TimePeriod.EVENING_PEAK: {
        "Indiranagar": 1.8,
        "Koramangala": 2.0,
        "Whitefield": 1.6,
        "Electronic City": 1.5,
        "Hebbal": 1.7,
        "Yeshwanthpur": 1.3,
    },
    TimePeriod.NIGHT: {
        "Indiranagar": 1.0,
        "Koramangala": 1.1,
        "Whitefield": 0.7,
        "Electronic City": 0.6,
        "Hebbal": 0.8,
        "Yeshwanthpur": 0.7,
    },
}


def get_zone_weights(sim_time_sec: float) -> dict[str, float]:
    """Get incident probability weights by zone for given simulation time."""
    period = get_time_period(sim_time_sec)
    return ZONE_WEIGHT_PROFILES[period]
