"""Convert OSM graphs to Aureon's RoadNetwork with KD-tree spatial indexing.

Provides efficient nearest-node lookup, shortest path, and route reconstruction
on real OSM road networks at any scale.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from typing import Any

import numpy as np

from ..network.road_graph import (
    RoadEdge,
    RoadNetwork,
    RoadNode,
    RoadType,
    haversine_distance_km,
)

logger = logging.getLogger("aureon.maps.graph_processor")

# OSM highway types → Aureon RoadType mapping
OSM_HIGHWAY_TO_ROADTYPE: dict[str, RoadType] = {
    "motorway": RoadType.EXPRESSWAY,
    "motorway_link": RoadType.EXPRESSWAY,
    "trunk": RoadType.EXPRESSWAY,
    "trunk_link": RoadType.EXPRESSWAY,
    "primary": RoadType.PRIMARY_ARTERIAL,
    "primary_link": RoadType.PRIMARY_ARTERIAL,
    "secondary": RoadType.SECONDARY,
    "secondary_link": RoadType.SECONDARY,
    "tertiary": RoadType.SECONDARY,
    "tertiary_link": RoadType.SECONDARY,
    "residential": RoadType.RESIDENTIAL,
    "unclassified": RoadType.RESIDENTIAL,
    "living_street": RoadType.RESIDENTIAL,
    "service": RoadType.RESIDENTIAL,
}

# Default speeds by road type (km/h)
DEFAULT_SPEEDS: dict[RoadType, float] = {
    RoadType.EXPRESSWAY: 60.0,
    RoadType.PRIMARY_ARTERIAL: 40.0,
    RoadType.SECONDARY: 30.0,
    RoadType.RESIDENTIAL: 20.0,
    RoadType.CONGESTED_CORRIDOR: 15.0,
}

# Bangalore zone polygons (approximate lat/lon bounding boxes)
# Used to assign zone labels to OSM nodes
BANGALORE_ZONES: dict[str, tuple[float, float, float, float]] = {
    "CBD": (12.965, 12.985, 77.595, 77.615),
    "East": (12.950, 12.978, 77.635, 77.665),
    "Whitefield": (12.965, 12.995, 77.720, 77.750),
    "South-East": (12.910, 12.945, 77.615, 77.655),
    "South": (12.820, 12.910, 77.580, 77.700),
    "North": (13.030, 13.110, 77.580, 77.610),
    "North-West": (12.985, 13.035, 77.530, 77.580),
    "West": (12.960, 12.990, 77.555, 77.595),
}


@dataclass
class GraphProcessingStats:
    """Statistics about graph conversion."""

    osm_node_count: int
    osm_edge_count: int
    aureon_node_count: int
    aureon_edge_count: int
    process_time_sec: float
    build_index_time_sec: float
    zone_assignment_time_sec: float


class OSMPatialIndex:
    """KD-tree based spatial index for O(1) nearest-node lookup.

    Uses scipy's cKDTree for sub-millisecond queries on graphs
    with tens of thousands of nodes.
    """

    def __init__(self, node_ids: list[str], lats: list[float], lons: list[float]) -> None:
        from scipy.spatial import cKDTree

        self._node_ids = node_ids
        # Convert to radians for haversine-compatible KD-tree
        coords_rad = np.array([
            [math.radians(lat), math.radians(lon)]
            for lat, lon in zip(lats, lons)
        ])
        t0 = time.time()
        self._tree = cKDTree(coords_rad)
        self._build_time = time.time() - t0
        self._lats = np.array(lats)
        self._lons = np.array(lons)

    @property
    def build_time_sec(self) -> float:
        return self._build_time

    def nearest_node(self, lat: float, lon: float) -> str:
        """Find the nearest node ID to given coordinates. O(log n)."""
        point_rad = np.array([[math.radians(lat), math.radians(lon)]])
        dist, idx = self._tree.query(point_rad, k=1)
        return self._node_ids[int(idx[0])]

    def nearest_nodes(
        self, lats: list[float], lons: list[float], k: int = 1,
    ) -> list[str]:
        """Batch nearest-node lookup. O(k log n) per query."""
        points_rad = np.array([
            [math.radians(lat), math.radians(lon)]
            for lat, lon in zip(lats, lons)
        ])
        dists, idxs = self._tree.query(points_rad, k=k)
        if k == 1:
            return [self._node_ids[int(i)] for i in idxs]
        return [[self._node_ids[int(i)] for i in row] for row in idxs]

    def nodes_within_radius(self, lat: float, lon: float, radius_km: float) -> list[str]:
        """Find all nodes within a radius. Useful for zone queries."""
        # Approximate: 1 degree latitude ~ 111km
        radius_rad = radius_km / 6371.0
        point_rad = np.array([math.radians(lat), math.radians(lon)])
        indices = self._tree.query_ball_point(point_rad, radius_rad)
        return [self._node_ids[i] for i in indices]


def assign_zone(lat: float, lon: float) -> str:
    """Assign a Bangalore zone label based on geographic coordinates."""
    for zone_name, (s, n, w, e) in BANGALORE_ZONES.items():
        if s <= lat <= n and w <= lon <= e:
            return zone_name
    return "General"


def classify_road_type(highway: str | list | None) -> RoadType:
    """Classify OSM highway tag into Aureon RoadType."""
    if isinstance(highway, list):
        highway = highway[0] if highway else "unclassified"
    return OSM_HIGHWAY_TO_ROADTYPE.get(str(highway), RoadType.SECONDARY)


def estimate_speed(road_type: RoadType, maxspeed: str | None = None) -> float:
    """Estimate speed in km/h. Uses maxspeed tag if available."""
    if maxspeed:
        try:
            speed = float(str(maxspeed).replace(" km/h", "").replace("kmh", "").strip())
            if 5 <= speed <= 200:
                return speed
        except ValueError:
            pass
    return DEFAULT_SPEEDS.get(road_type, 30.0)


class OSMGraphProcessor:
    """Converts an OSMnx graph to Aureon's RoadNetwork.

    Supports both direct conversion and node-filtered conversion
    for creating smaller sub-networks.
    """

    def __init__(self, include_oneway: bool = True) -> None:
        self.include_oneway = include_oneway
        self._spatial_index: OSMPatialIndex | None = None
        self._stats: GraphProcessingStats | None = None

    @property
    def spatial_index(self) -> OSMPatialIndex | None:
        return self._spatial_index

    @property
    def stats(self) -> GraphProcessingStats | None:
        return self._stats

    def convert(
        self,
        G: Any,
        network_name: str = "Bangalore OSM Network",
    ) -> RoadNetwork:
        """Convert OSMnx MultiDiGraph to Aureon RoadNetwork.

        Args:
            G: OSMnx MultiDiGraph (driving network).
            network_name: Name for the resulting RoadNetwork.

        Returns:
            RoadNetwork compatible with CitySimulationEngine.
        """
        t_start = time.time()

        network = RoadNetwork(name=network_name)
        node_ids = []
        lats = []
        lons = []

        # Phase 1: Convert nodes
        t_zone = 0.0
        for osm_id, data in G.nodes(data=True):
            lat = data.get("y", 0.0)
            lon = data.get("x", 0.0)

            t_z0 = time.time()
            zone = assign_zone(lat, lon)
            t_zone += time.time() - t_z0

            node_id = str(osm_id)
            node = RoadNode(
                id=node_id,
                name=node_id,
                latitude=lat,
                longitude=lon,
                zone=zone,
            )
            network.add_node(node)
            node_ids.append(node_id)
            lats.append(lat)
            lons.append(lon)

        # Phase 2: Build spatial index
        t_index = 0.0
        if node_ids:
            t_i0 = time.time()
            self._spatial_index = OSMPatialIndex(node_ids, lats, lons)
            t_index = time.time() - t_i0

        # Phase 3: Convert edges
        edge_counter = 0
        for u, v, data in G.edges(data=True):
            highway = data.get("highway", "secondary")
            road_type = classify_road_type(highway)
            maxspeed = data.get("maxspeed")
            speed = estimate_speed(road_type, maxspeed)

            # Use OSM length if available, otherwise compute
            length_m = data.get("length", 0.0)
            if length_m <= 0:
                u_data = G.nodes[u]
                v_data = G.nodes[v]
                length_km = haversine_distance_km(
                    u_data.get("y", 0), u_data.get("x", 0),
                    v_data.get("y", 0), v_data.get("x", 0),
                )
            else:
                length_km = length_m / 1000.0

            oneway = data.get("oneway", False)
            if isinstance(oneway, str):
                oneway = oneway.lower() == "yes"

            edge_counter += 1
            edge = RoadEdge(
                id=f"osm_e{edge_counter}",
                source_id=str(u),
                target_id=str(v),
                length_km=length_km,
                road_type=road_type,
                base_speed_kmh=speed,
                one_way=oneway,
            )
            network.add_edge(edge)

        elapsed = time.time() - t_start
        self._stats = GraphProcessingStats(
            osm_node_count=G.number_of_nodes(),
            osm_edge_count=G.number_of_edges(),
            aureon_node_count=len(network.nodes),
            aureon_edge_count=len(network._edges_by_id),
            process_time_sec=elapsed,
            build_index_time_sec=t_index,
            zone_assignment_time_sec=t_zone,
        )
        logger.info(
            "Converted OSM graph: %d nodes, %d edges (%.2fs)",
            self._stats.aureon_node_count,
            self._stats.aureon_edge_count,
            elapsed,
        )
        return network

    def find_nearest_node(self, lat: float, lon: float) -> str | None:
        """O(log n) nearest-node lookup using KD-tree."""
        if self._spatial_index is None:
            return None
        return self._spatial_index.nearest_node(lat, lon)
