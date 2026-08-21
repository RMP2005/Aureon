"""Road network representation, graph algorithms, and geospatial calculations.

Provides realistic routing, shortest path algorithms (Dijkstra/A*),
traffic-adjusted travel times, and OpenStreetMap / NetworkX compatibility.
"""

from __future__ import annotations

import heapq
import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("aureon.network.road_graph")


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
        self._nx_graph: Any = None  # Optional NetworkX graph for fast routing
        self._route_cache: dict[tuple[str, str, str], RouteResult] = {}
        self._scipy_csr: Any = None  # scipy sparse CSR matrix for C-backed Dijkstra
        self._scipy_node_index: dict[str, int] = {}  # node_id -> matrix row index
        self._scipy_index_node: list[str] = []  # matrix row index -> node_id
        self._scipy_dist_cache: dict[str, dict[str, float]] = {}  # src -> {dst: cost}

    def __deepcopy__(self, memo: dict) -> "RoadNetwork":
        """Optimized deepcopy: shares immutable NX graph and scipy matrix.

        The NX graph, scipy CSR matrix, and node index mappings are read-only
        during simulation and can be safely shared. Only mutable state
        (nodes, edges, congestion factors, caches) is deep-copied.
        """
        import copy as _copy
        new = RoadNetwork(name=self.name)
        new.nodes = _copy.deepcopy(self.nodes, memo)
        new._adjacency = _copy.deepcopy(self._adjacency, memo)
        new._edges_by_id = _copy.deepcopy(self._edges_by_id, memo)
        # Share immutable routing infrastructure (saves ~40s on large graphs)
        new._nx_graph = self._nx_graph
        new._scipy_csr = self._scipy_csr
        new._scipy_node_index = self._scipy_node_index
        new._scipy_index_node = self._scipy_index_node
        new._route_cache = {}
        new._scipy_dist_cache = {}
        return new

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

    def set_nx_graph(self, g: Any) -> None:
        """Set a NetworkX graph for fast C-backed routing.

        Also builds a scipy sparse CSR matrix for sub-millisecond Dijkstra.
        """
        self._nx_graph = g
        self._build_scipy_matrix(g)

    def _build_scipy_matrix(self, g: Any) -> None:
        """Build a scipy sparse CSR matrix from the NX DiGraph for C-backed Dijkstra."""
        import numpy as np
        from scipy import sparse

        nodes = list(g.nodes)
        node_index = {nid: idx for idx, nid in enumerate(nodes)}
        n = len(nodes)

        rows, cols, weights = [], [], []
        for u, v, data in g.edges(data=True):
            if u in node_index and v in node_index:
                rows.append(node_index[u])
                cols.append(node_index[v])
                weights.append(data.get("travel_time_seconds", 1.0))

        if not rows:
            return

        matrix = sparse.csr_matrix(
            (np.array(weights, dtype=np.float64), (np.array(rows), np.array(cols))),
            shape=(n, n),
        )
        self._scipy_csr = matrix
        self._scipy_node_index = node_index
        self._scipy_index_node = nodes
        logger.info("Built scipy CSR matrix: %d nodes, %d edges", n, len(rows))

    def invalidate_route_cache(self) -> None:
        """Clear all routing caches."""
        self._route_cache.clear()
        self._scipy_dist_cache.clear()

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
        """Calculate shortest path between two nodes.

        Uses NetworkX C-backed Dijkstra when a NetworkX graph is available
        (set via set_nx_graph), falling back to pure-Python Dijkstra.

        Results are cached per (start, end, weight) to eliminate redundant
        calls for the same origin-destination pair.

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

        cache_key = (start_node_id, end_node_id, weight)
        cached = self._route_cache.get(cache_key)
        if cached is not None:
            return cached

        if self._nx_graph is not None:
            result = self._calculate_route_nx(start_node_id, end_node_id, weight)
        else:
            result = self._calculate_route_dijkstra(start_node_id, end_node_id, weight)

        self._route_cache[cache_key] = result
        return result

    def _calculate_route_nx(
        self, start_node_id: str, end_node_id: str, weight: str,
    ) -> RouteResult:
        """Fast routing via scipy C-backed Dijkstra or NetworkX fallback."""
        if self._scipy_csr is not None and weight == "time":
            return self._calculate_route_scipy(start_node_id, end_node_id)
        # Fallback to NetworkX Python Dijkstra
        return self._calculate_route_nx_fallback(start_node_id, end_node_id, weight)

    def _calculate_route_scipy(
        self, start_node_id: str, end_node_id: str,
    ) -> RouteResult:
        """C-backed Dijkstra via scipy.sparse.csgraph.

        Uses single-source Dijkstra from start_node, caches all distances.
        Subsequent queries from the same source are O(1) lookups.
        """
        import numpy as np
        from scipy.sparse.csgraph import dijkstra

        src_idx = self._scipy_node_index.get(start_node_id)
        tgt_idx = self._scipy_node_index.get(end_node_id)
        if src_idx is None or tgt_idx is None:
            return RouteResult(found=False)

        # Check distance cache for this source
        dists = self._scipy_dist_cache.get(start_node_id)
        if dists is None:
            dist_array = dijkstra(
                self._scipy_csr, directed=True, indices=src_idx, return_predecessors=False,
            )
            # Build a sparse lookup: only store finite distances
            dists = {}
            finite_mask = np.isfinite(dist_array) & (dist_array < 1e15)
            indices = np.where(finite_mask)[0]
            for idx in indices:
                dists[self._scipy_index_node[idx]] = float(dist_array[idx])
            self._scipy_dist_cache[start_node_id] = dists

        cost = dists.get(end_node_id)
        if cost is None:
            return RouteResult(found=False)

        # Estimate distance from time: assume avg speed ~30 km/h if not known
        total_distance = cost * 30.0 / 3600.0  # rough km from seconds at 30 km/h

        return RouteResult(
            found=True,
            path_node_ids=[start_node_id, end_node_id],
            total_distance_km=round(total_distance, 3),
            estimated_time_seconds=round(cost, 1),
            edges=[],
        )

    def _calculate_route_nx_fallback(
        self, start_node_id: str, end_node_id: str, weight: str,
    ) -> RouteResult:
        """NetworkX Python Dijkstra fallback (for distance weight or no scipy)."""
        import networkx as nx

        edge_weight = "travel_time_seconds" if weight == "time" else "length_km"
        try:
            path = nx.shortest_path(
                self._nx_graph, start_node_id, end_node_id, weight=edge_weight,
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return RouteResult(found=False)

        total_distance = 0.0
        total_time = 0.0
        edges: list[RoadEdge] = []

        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            raw = self._nx_graph[u][v]
            if hasattr(raw, "values") and "length_km" not in raw:
                edge_data = next(iter(raw.values()))
            else:
                edge_data = raw
            length = edge_data.get("length_km", 0.0)
            speed = edge_data.get("effective_speed_kmh", 30.0)
            travel_time = (length / max(speed, 5.0)) * 3600.0 if speed > 0 else (length / 30.0) * 3600.0
            total_distance += length
            total_time += travel_time

        return RouteResult(
            found=True,
            path_node_ids=path,
            total_distance_km=round(total_distance, 3),
            estimated_time_seconds=round(total_time, 1),
            edges=edges,
        )

    def _calculate_route_dijkstra(
        self, start_node_id: str, end_node_id: str, weight: str,
    ) -> RouteResult:
        """Pure-Python Dijkstra fallback."""
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
        self._route_cache.clear()

    def set_zone_congestion(self, zone: str, congestion_factor: float) -> None:
        """Update congestion on all edges touching a specific zone."""
        for node_id, edges in self._adjacency.items():
            source_node = self.nodes.get(node_id)
            if source_node and source_node.zone == zone:
                for edge in edges:
                    edge.congestion_factor = congestion_factor
        self._route_cache.clear()

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
