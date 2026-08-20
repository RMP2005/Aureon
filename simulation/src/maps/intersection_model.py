"""Configurable intersection / traffic-signal delay modelling.

Provides a lightweight, stochastic model of the delay vehicles accumulate
while crossing signalised intersections along a route.  Delay depends on
the road class (expressways are grade-separated and delay-free, arterials
carry major signals, residential streets have minor intersections), on
emergency priority preemption, and on random variation in signal timing.

Use :class:`NoIntersectionDelay` to restore the previous behaviour of the
simulation (zero intersection delay) without changing call sites.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import ClassVar


@dataclass
class IntersectionDelayModel:
    """Stochastic model of per-intersection signal delay."""

    # Base delay per intersection crossing (seconds)
    base_signal_delay_sec: float = 15.0
    # Random variation in signal timing (+/- fraction)
    signal_variation: float = 0.3
    # Emergency vehicle priority reduction (0.0 = no priority, 1.0 = skip all signals)
    emergency_priority_factor: float = 0.5
    # Delay added for left turns / U-turns
    turn_penalty_sec: float = 5.0
    # Road-class-specific multipliers
    expressway_intersection_delay_sec: float = 0.0  # no signals on expressway
    arterial_intersection_delay_sec: float = 20.0
    residential_intersection_delay_sec: float = 10.0
    # Optional seed for reproducible stochastic variation
    seed: int | None = None

    _EXPRESSWAY_KEYWORDS: ClassVar[tuple[str, ...]] = (
        "expressway",
        "freeway",
        "motorway",
        "highway",
        "trunk",
    )
    _ARTERIAL_KEYWORDS: ClassVar[tuple[str, ...]] = ("arterial", "primary", "major")
    _RESIDENTIAL_KEYWORDS: ClassVar[tuple[str, ...]] = (
        "residential",
        "local",
        "minor",
        "service",
        "living",
    )

    def __post_init__(self) -> None:
        self._rng: random.Random = random.Random(self.seed)

    def estimate_total_delay(
        self,
        route_edge_count: int,
        road_types: list[str],
        is_emergency: bool = False,
    ) -> float:
        """Estimate total intersection delay for a route.

        Args:
            route_edge_count: Number of edges (intersections = edges - 1 roughly)
            road_types: List of road type strings on the route
            is_emergency: If True, apply emergency priority reduction

        Returns:
            Total delay in seconds
        """
        intersections = max(route_edge_count - 1, 0)
        if intersections == 0 or not road_types:
            return 0.0

        total_delay = 0.0
        for i in range(intersections):
            entering_type = road_types[min(i, len(road_types) - 1)]
            exiting_type = road_types[min(i + 1, len(road_types) - 1)]
            # A change in road class at an intersection is treated as a
            # turn (left/U-turn onto a different road), which incurs the
            # extra turn penalty.
            is_turn = entering_type != exiting_type
            total_delay += self.per_intersection_delay(
                entering_type,
                is_emergency=is_emergency,
                is_turn=is_turn,
            )
        return total_delay

    def per_intersection_delay(
        self,
        road_type: str,
        is_emergency: bool = False,
        is_turn: bool = False,
    ) -> float:
        """Get delay for a single intersection crossing."""
        base_delay = self._base_delay_for_road_type(road_type)
        variation = self._rng.uniform(
            1.0 - self.signal_variation,
            1.0 + self.signal_variation,
        )
        delay = base_delay * variation

        if is_emergency:
            delay *= 1.0 - self.emergency_priority_factor

        if is_turn:
            delay += self.turn_penalty_sec

        return max(delay, 0.0)

    def _classify_road_type(self, road_type: str) -> str:
        normalized = road_type.strip().lower().replace("-", "_").replace(" ", "_")
        if any(keyword in normalized for keyword in self._EXPRESSWAY_KEYWORDS):
            return "expressway"
        if any(keyword in normalized for keyword in self._ARTERIAL_KEYWORDS):
            return "arterial"
        if any(keyword in normalized for keyword in self._RESIDENTIAL_KEYWORDS):
            return "residential"
        return "unknown"

    def _base_delay_for_road_type(self, road_type: str) -> float:
        category = self._classify_road_type(road_type)
        if category == "expressway":
            return self.expressway_intersection_delay_sec
        if category == "arterial":
            return self.arterial_intersection_delay_sec
        if category == "residential":
            return self.residential_intersection_delay_sec
        return self.base_signal_delay_sec


class NoIntersectionDelay:
    """Null-object variant that models no intersection delay at all."""

    def estimate_total_delay(self, *args: object, **kwargs: object) -> float:
        return 0.0

    def per_intersection_delay(self, *args: object, **kwargs: object) -> float:
        return 0.0
