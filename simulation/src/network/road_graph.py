"""Road network representation, graph algorithms, and geospatial calculations.

Provides realistic routing, shortest path algorithms (Dijkstra/A*),
traffic-adjusted travel times, and OpenStreetMap / NetworkX compatibility.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RoadType(str, Enum):
    """Road hierarchy classifications."""

    EXPRESSWAY = "expressway"
    PRIMARY_ARTERIAL = "primary_arterial"
    SECONDARY = "secondary"
    RESIDENTIAL = "residential"
    CONGESTED_CORRIDOR = "congested_corridor"


# Speed limits in km/h for road classifications
DEFAULT_SPEED_LIMITS: dict[RoadType, float] = {
    RoadType.EXPRESSWAY: 80.0,
    RoadType.PRIMARY_ARTERIAL: 50.0,
    RoadType.SECONDARY: 35.0,
    RoadType.RESIDENTIAL: 25.0,
    RoadType.CONGESTED_CORRIDOR: 20.0,
}


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on Earth in kilometers."""
    r = 6371.0  # Earth's radius in kilometers
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


@dataclass
class RoadNode:
    """A junction, landmark, or point of interest on the road network."""

    id: str
    name: str
    latitude: float
    longitude: float
    zone: str = "general"
    is_hospital: bool = False
    is_station: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RoadEdge:
    """A road segment connecting two nodes."""

    id: str
    source_id: str
    target_id: str
    length_km: float
    road_type: RoadType = RoadType.SECONDARY
    base_speed_kmh: float = 35.0
    congestion_factor: float = 1.0  # 1.0 = normal, 2.0 = double travel time
    lanes: int = 2
    one_way: bool = False

    @property
    def effective_speed_kmh(self) -> float:
        """Calculate effective speed taking congestion into account."""
        speed = self.base_speed_kmh / max(self.congestion_factor, 0.2)
        return max(speed, 5.0)  # minimum 5 km/h creep speed

    @property
    def travel_time_seconds(self) -> float:
        """Travel time across this road segment in seconds."""
        hours = self.length_km / self.effective_speed_kmh
        return hours * 3600.0


@dataclass
class RouteResult:
    """Result of a routing calculation."""

    found: bool
    path_node_ids: list[str] = field(default_factory=list)
    total_distance_km: float = 0.0
    estimated_time_seconds: float = 0.0
    edges: list[RoadEdge] = field(default_factory=list)

    @property
    def estimated_time_minutes(self) -> float:
        """Estimated travel time in minutes."""
        return self.estimated_time_seconds / 60.0


class RoadNetwork:
    """Graph-based urban road network.

    Supports realistic routing, dynamic traffic updates,
    and conversion to/from NetworkX.
    """

    def __init__(self, name: str = "Bangalore Road Network") -> None:
        self.name = name
        self.nodes: dict[str, RoadNode] = {}
        # adjacency: source_id -> list of RoadEdge
        self._adjacency: dict[str, list[RoadEdge]] = {}
        self._edges_by_id: dict[str, RoadEdge] = {}

    def add_node(self, node: RoadNode) -> None:
        """Add a node to the road graph."""
        self.nodes[node.id] = node
        if node.id not in self._adjacency:
            self._adjacency[node.id] = []

    def add_edge(self, edge: RoadEdge) -> None:
        """Add a directed or bidirectional road edge."""
        self._edges_by_id[edge.id] = edge
        if edge.source_id not in self._adjacency:
            self._adjacency[edge.source_id] = []
        self._adjacency[edge.source_id].append(edge)

        if not edge.one_way:
            # Add reverse edge
            reverse_edge = RoadEdge(
                id=f"{edge.id}_rev",
                source_id=edge.target_id,
                target_id=edge.source_id,
                length_km=edge.length_km,
                road_type=edge.road_type,
                base_speed_kmh=edge.base_speed_kmh,
                congestion_factor=edge.congestion_factor,
                lanes=edge.lanes,
                one_way=True,
            )
            self._edges_by_id[reverse_edge.id] = reverse_edge
            if edge.target_id not in self._adjacency:
                self._adjacency[edge.target_id] = []
            self._adjacency[edge.target_id].append(reverse_edge)

    def find_nearest_node(self, lat: float, lon: float) -> RoadNode | None:
        """Find the nearest road network node to given geographic coordinates."""
        if not self.nodes:
            return None

        best_node = None
        min_dist = float("inf")
        for node in self.nodes.values():
            dist = haversine_distance_km(lat, lon, node.latitude, node.longitude)
            if dist < min_dist:
                min_dist = dist
                best_node = node
        return best_node

    def calculate_route(
        self,
        start_node_id: str,
        end_node_id: str,
        weight: str = "time",  # "time" or "distance"
    ) -> RouteResult:
        """Calculate shortest path between two nodes using Dijkstra's algorithm.

        Args:
            start_node_id: ID of origin node.
            end_node_id: ID of destination node.
            weight: Cost function ('time' for fastest ETA, 'distance' for shortest km).

        Returns:
            RouteResult with path, distance, and ETA.
        """
        if start_node_id not in self.nodes or end_node_id not in self.nodes:
            return RouteResult(found=False)

        if start_node_id == end_node_id:
            return RouteResult(
                found=True,
                path_node_ids=[start_node_id],
                total_distance_km=0.0,
                estimated_time_seconds=0.0,
            )

        # Priority queue stores tuples: (cumulative_cost, current_node_id)
        pq: list[tuple[float, str]] = [(0.0, start_node_id)]
        costs: dict[str, float] = {start_node_id: 0.0}
        previous_edge: dict[str, RoadEdge | None] = {start_node_id: None}
        previous_node: dict[str, str | None] = {start_node_id: None}

        while pq:
            current_cost, current_id = heapq.heappop(pq)

            if current_id == end_node_id:
                break

            if current_cost > costs.get(current_id, float("inf")):
                continue

            for edge in self._adjacency.get(current_id, []):
                neighbor_id = edge.target_id
                edge_cost = (
                    edge.travel_time_seconds
                    if weight == "time"
                    else edge.length_km
                )
                new_cost = current_cost + edge_cost

                if new_cost < costs.get(neighbor_id, float("inf")):
                    costs[neighbor_id] = new_cost
                    previous_node[neighbor_id] = current_id
                    previous_edge[neighbor_id] = edge
                    heapq.heappush(pq, (new_cost, neighbor_id))

        if end_node_id not in previous_node or previous_node[end_node_id] is None:
            return RouteResult(found=False)

        # Reconstruct path
        path_nodes: list[str] = []
        edges: list[RoadEdge] = []
        curr: str | None = end_node_id

        while curr is not None:
            path_nodes.append(curr)
            edge = previous_edge.get(curr)
            if edge:
                edges.append(edge)
            curr = previous_node.get(curr)

        path_nodes.reverse()
        edges.reverse()

        total_distance = sum(e.length_km for e in edges)
        total_time = sum(e.travel_time_seconds for e in edges)

        return RouteResult(
            found=True,
            path_node_ids=path_nodes,
            total_distance_km=round(total_distance, 3),
            estimated_time_seconds=round(total_time, 1),
            edges=edges,
        )

    def set_corridor_congestion(
        self,
        node_id_1: str,
        node_id_2: str,
        congestion_factor: float,
    ) -> None:
        """Update traffic congestion between two adjacent nodes."""
        for edge in self._adjacency.get(node_id_1, []):
            if edge.target_id == node_id_2:
                edge.congestion_factor = congestion_factor

        for edge in self._adjacency.get(node_id_2, []):
            if edge.target_id == node_id_1:
                edge.congestion_factor = congestion_factor

    def set_zone_congestion(self, zone: str, congestion_factor: float) -> None:
        """Update congestion on all edges touching a specific zone."""
        for node_id, edges in self._adjacency.items():
            source_node = self.nodes.get(node_id)
            if source_node and source_node.zone == zone:
                for edge in edges:
                    edge.congestion_factor = congestion_factor

    def to_networkx(self) -> Any:
        """Export to NetworkX DiGraph if networkx is installed."""
        try:
            import networkx as nx

            g = nx.DiGraph()
            for node in self.nodes.values():
                g.add_node(
                    node.id,
                    name=node.name,
                    lat=node.latitude,
                    lon=node.longitude,
                    zone=node.zone,
                )
            for edge in self._edges_by_id.values():
                g.add_edge(
                    edge.source_id,
                    edge.target_id,
                    id=edge.id,
                    length_km=edge.length_km,
                    travel_time_seconds=edge.travel_time_seconds,
                    effective_speed_kmh=edge.effective_speed_kmh,
                    road_type=edge.road_type.value,
                )
            return g
        except ImportError:
            return None
