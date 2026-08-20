"""Tests for road network graph and routing algorithms."""

import unittest

try:
    from simulation.src.network.bangalore_map import build_bangalore_network
    from simulation.src.network.road_graph import (
        RoadEdge,
        RoadNetwork,
        RoadNode,
        RoadType,
        haversine_distance_km,
    )
except ImportError:
    from src.network.bangalore_map import build_bangalore_network  # type: ignore
    from src.network.road_graph import (  # type: ignore
        RoadEdge,
        RoadNetwork,
        RoadNode,
        RoadType,
        haversine_distance_km,
    )


class TestRouting(unittest.TestCase):
    def test_haversine_distance(self) -> None:
        d = haversine_distance_km(12.9756, 77.6066, 12.9719, 77.6412)
        self.assertTrue(3.5 < d < 4.5)

    def test_road_network_routing(self) -> None:
        net = RoadNetwork()
        n1 = RoadNode("n1", "Node 1", 12.0, 77.0)
        n2 = RoadNode("n2", "Node 2", 12.0, 77.05)
        n3 = RoadNode("n3", "Node 3", 12.0, 77.10)

        net.add_node(n1)
        net.add_node(n2)
        net.add_node(n3)

        net.add_edge(RoadEdge("e1", "n1", "n2", 5.0, RoadType.PRIMARY_ARTERIAL, 50.0))
        net.add_edge(RoadEdge("e2", "n2", "n3", 5.0, RoadType.PRIMARY_ARTERIAL, 50.0))

        route = net.calculate_route("n1", "n3", weight="time")
        self.assertTrue(route.found)
        self.assertEqual(route.path_node_ids, ["n1", "n2", "n3"])
        self.assertEqual(route.total_distance_km, 10.0)
        self.assertAlmostEqual(route.estimated_time_seconds, 720.0, delta=1.0)

    def test_traffic_congestion_impact(self) -> None:
        net = RoadNetwork()
        n1 = RoadNode("n1", "Node 1", 12.0, 77.0)
        n2 = RoadNode("n2", "Node 2", 12.0, 77.05)

        net.add_node(n1)
        net.add_node(n2)

        edge = RoadEdge("e1", "n1", "n2", 10.0, RoadType.PRIMARY_ARTERIAL, 60.0, congestion_factor=1.0)
        net.add_edge(edge)

        route_clear = net.calculate_route("n1", "n2", weight="time")
        self.assertAlmostEqual(route_clear.estimated_time_seconds, 600.0, delta=1.0)

        net.set_corridor_congestion("n1", "n2", 2.0)
        route_traffic = net.calculate_route("n1", "n2", weight="time")
        self.assertAlmostEqual(route_traffic.estimated_time_seconds, 1200.0, delta=1.0)

    def test_bangalore_network_integrity(self) -> None:
        net = build_bangalore_network()
        self.assertGreaterEqual(len(net.nodes), 20)

        route = net.calculate_route("station_central_cbd", "node_indiranagar", weight="time")
        self.assertTrue(route.found)
        self.assertGreaterEqual(len(route.path_node_ids), 2)
        self.assertGreater(route.total_distance_km, 0.0)
        self.assertGreater(route.estimated_time_seconds, 0.0)

        hosp_nodes = [n for n in net.nodes.values() if n.is_hospital]
        self.assertGreaterEqual(len(hosp_nodes), 5)


if __name__ == "__main__":
    unittest.main()
