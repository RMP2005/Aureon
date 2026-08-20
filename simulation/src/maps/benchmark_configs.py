"""Standard benchmark configurations for scale testing.

Defines SMALL / MEDIUM / LARGE simulation setups used to measure how
routing, dispatch, and traffic performance scale with network size:
  - SMALL:  legacy 32-node Bangalore graph (fast, deterministic baseline)
  - MEDIUM: OSM subset covering central Bangalore (~5k nodes)
  - LARGE:  full Bangalore OSM graph (~50k nodes)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..models.ambulance import create_default_bangalore_fleet
from ..models.hospital import get_default_bangalore_hospitals
from ..network.bangalore_map import build_bangalore_network

__all__ = [
    "BenchmarkScale",
    "BenchmarkConfig",
    "SMALL_CONFIG",
    "MEDIUM_CONFIG",
    "LARGE_CONFIG",
    "get_config",
    "get_all_configs",
]


class BenchmarkScale(str, Enum):
    """Supported benchmark graph scales."""

    SMALL = "small"    # 32-node legacy graph
    MEDIUM = "medium"  # OSM subset (~5k nodes)
    LARGE = "large"    # Full OSM graph (~50k nodes)


@dataclass
class BenchmarkConfig:
    """Parameters describing a single benchmark scenario."""

    scale: BenchmarkScale
    description: str
    num_seeds: int
    duration_minutes: float
    incident_rate_per_hour: float
    # How to build the network
    use_osm: bool  # True = load from OSM cache, False = use legacy 32-node
    # Fleet size
    fleet_size: int
    # Traffic
    enable_dynamic_traffic: bool
    enable_traffic_events: bool
    enable_intersection_delays: bool
    # Optional bounding box restricting the OSM graph to a subset (MEDIUM)
    osm_subset_bbox: tuple[float, float, float, float] | None = None


SMALL_CONFIG = BenchmarkConfig(
    scale=BenchmarkScale.SMALL,
    description="32-node legacy Bangalore graph",
    num_seeds=20,
    duration_minutes=60.0,
    incident_rate_per_hour=14.0,
    use_osm=False,
    fleet_size=14,
    enable_dynamic_traffic=True,
    enable_traffic_events=False,
    enable_intersection_delays=False,
)

MEDIUM_CONFIG = BenchmarkConfig(
    scale=BenchmarkScale.MEDIUM,
    description="OSM subset covering central Bangalore (~5k nodes)",
    num_seeds=20,
    duration_minutes=60.0,
    incident_rate_per_hour=14.0,
    use_osm=True,
    osm_subset_bbox=(12.97, 12.93, 77.65, 77.61),  # CBD + Koramangala + Indiranagar
    fleet_size=30,
    enable_dynamic_traffic=True,
    enable_traffic_events=True,
    enable_intersection_delays=True,
)

LARGE_CONFIG = BenchmarkConfig(
    scale=BenchmarkScale.LARGE,
    description="Full Bangalore OSM graph (~50k nodes)",
    num_seeds=20,
    duration_minutes=60.0,
    incident_rate_per_hour=14.0,
    use_osm=True,
    osm_subset_bbox=None,  # Use full Bangalore bbox
    fleet_size=50,
    enable_dynamic_traffic=True,
    enable_traffic_events=True,
    enable_intersection_delays=True,
)


def get_config(scale: BenchmarkScale) -> BenchmarkConfig:
    """Return the standard benchmark configuration for ``scale``."""
    return get_all_configs()[scale]


def get_all_configs() -> dict[BenchmarkScale, BenchmarkConfig]:
    """Return every standard benchmark configuration keyed by scale."""
    return {
        BenchmarkScale.SMALL: SMALL_CONFIG,
        BenchmarkScale.MEDIUM: MEDIUM_CONFIG,
        BenchmarkScale.LARGE: LARGE_CONFIG,
    }
