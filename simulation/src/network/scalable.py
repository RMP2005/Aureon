"""Scalable simulation environment with abstract graph interface.

Provides architecture for scaling from 32-node Bangalore graph
to hundreds/thousands of nodes via OSMnx import.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from .road_graph import RoadEdge, RoadNetwork, RoadNode, RoadType, haversine_distance_km


@runtime_checkable
class GraphProvider(Protocol):
    """Protocol for any graph that can drive the simulation.

    Implement this to use OSMnx, NetworkX, or custom graphs.
    """

    @property
    def node_count(self) -> int: ...

    @property
    def edge_count(self) -> int: ...

    def get_node_ids(self) -> list[str]: ...

    def get_neighbors(self, node_id: str) -> list[str]: ...

    def get_edge_weight(self, source: str, target: str) -> float: ...


class RoadNetworkAdapter:
    """Adapts RoadNetwork to GraphProvider protocol.

    Wraps the existing RoadNetwork for backward compatibility
    while enabling future OSMnx integration.
    """

    def __init__(self, network: RoadNetwork) -> None:
        self._network = network

    @property
    def node_count(self) -> int:
        return len(self._network.nodes)

    @property
    def edge_count(self) -> int:
        return sum(len(edges) for edges in self._network._adjacency.values())

    def get_node_ids(self) -> list[str]:
        return list(self._network.nodes.keys())

    def get_neighbors(self, node_id: str) -> list[str]:
        return [e.target_id for e in self._network._adjacency.get(node_id, [])]

    def get_edge_weight(self, source: str, target: str) -> float:
        for edge in self._network._adjacency.get(source, []):
            if edge.target_id == target:
                return edge.travel_time_seconds
        return float("inf")

    @property
    def underlying(self) -> RoadNetwork:
        return self._network


class ScalableRoadNetwork:
    """Extended road network that supports variable-size graphs.

    Wraps RoadNetwork and adds:
    - Dynamic node/edge insertion
    - Zone-based queries at any scale
    - Precomputed all-pairs shortest paths for small graphs
    - Lazy computation for large graphs
    """

    def __init__(self, base_network: RoadNetwork | None = None) -> None:
        self._base = base_network or RoadNetwork()
        self._adapter = RoadNetworkAdapter(self._base)
        self._zone_index: dict[str, list[str]] = {}
        self._built_index = False

    @property
    def adapter(self) -> GraphProvider:
        return self._adapter

    @property
    def base(self) -> RoadNetwork:
        return self._base

    @property
    def node_count(self) -> int:
        return self._adapter.node_count

    @property
    def edge_count(self) -> int:
        return self._adapter.edge_count

    def add_node(self, node: RoadNode) -> None:
        self._base.add_node(node)
        self._built_index = False

    def add_edge(self, edge: RoadEdge) -> None:
        self._base.add_edge(edge)
        self._built_index = False

    def build_zone_index(self) -> None:
        """Index nodes by zone for fast zone-based queries."""
        self._zone_index.clear()
        for node_id, node in self._base.nodes.items():
            zone = node.zone
            if zone not in self._zone_index:
                self._zone_index[zone] = []
            self._zone_index[zone].append(node_id)
        self._built_index = True

    def get_nodes_in_zone(self, zone: str) -> list[str]:
        if not self._built_index:
            self.build_zone_index()
        return self._zone_index.get(zone, [])

    def get_zones(self) -> list[str]:
        if not self._built_index:
            self.build_zone_index()
        return list(self._zone_index.keys())

    def calculate_route(self, start: str, end: str, weight: str = "time") -> Any:
        """Delegate routing to underlying network."""
        return self._base.calculate_route(start, end, weight)

    def find_nearest_node(self, lat: float, lon: float) -> RoadNode | None:
        return self._base.find_nearest_node(lat, lon)

    def set_zone_congestion(self, zone: str, factor: float) -> None:
        self._base.set_zone_congestion(zone, factor)

    def set_corridor_congestion(self, n1: str, n2: str, factor: float) -> None:
        self._base.set_corridor_congestion(n1, n2, factor)

    @classmethod
    def from_osmnx_graph(cls, G: Any, zone_attr: str = "zone") -> ScalableRoadNetwork:
        """Create from an OSMnx graph (future use).

        Expected G to be a NetworkX MultiDiGraph with node attributes:
        - lat, lon: coordinates
        - zone: zone label (optional)

        Edge attributes:
        - length: meters
        - speed_kph: speed limit
        - road_type: classification
        """
        try:
            import networkx as nx
        except ImportError:
            raise ImportError("networkx required for OSMnx import")

        network = RoadNetwork(name="OSMnx Import")

        for node_id, data in G.nodes(data=True):
            lat = data.get("lat", data.get("y", 0.0))
            lon = data.get("lon", data.get("x", 0.0))
            zone = data.get(zone_attr, "general")
            rn = RoadNode(
                id=str(node_id), name=str(node_id),
                latitude=lat, longitude=lon, zone=zone,
            )
            network.add_node(rn)

        edge_counter = 0
        for u, v, data in G.edges(data=True):
            u_data = G.nodes[u]
            v_data = G.nodes[v]
            lat1, lon1 = u_data.get("lat", u_data.get("y", 0)), u_data.get("lon", u_data.get("x", 0))
            lat2, lon2 = v_data.get("lat", v_data.get("y", 0)), v_data.get("lon", v_data.get("x", 0))
            dist = haversine_distance_km(lat1, lon1, lat2, lon2)
            speed = data.get("speed_kph", 35.0)
            road_type_str = data.get("road_type", "secondary")
            try:
                road_type = RoadType(road_type_str)
            except ValueError:
                road_type = RoadType.SECONDARY

            edge_counter += 1
            edge = RoadEdge(
                id=f"osm_e{edge_counter}",
                source_id=str(u), target_id=str(v),
                length_km=dist, road_type=road_type,
                base_speed_kmh=speed, one_way=True,
            )
            network.add_edge(edge)

        return cls(network)
