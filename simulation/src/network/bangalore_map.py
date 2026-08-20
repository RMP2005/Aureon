"""Realistic Bangalore road topology and geospatial nodes for Aureon."""

from __future__ import annotations

from .road_graph import RoadEdge, RoadNetwork, RoadNode, RoadType


def build_bangalore_network() -> RoadNetwork:
    """Construct a high-fidelity graph representation of Bangalore central and peripheral corridors."""
    net = RoadNetwork(name="Bangalore Digital Twin Network")

    # 1. Road Nodes (Junctions, Hubs, Hospitals, Ambulance Stations)
    nodes_data = [
        # Central Bangalore
        RoadNode("node_mg_road", "MG Road / Brigade Rd", 12.9756, 77.6066, zone="CBD"),
        RoadNode("node_majestic", "Majestic / City Railway", 12.9781, 77.5696, zone="West"),
        RoadNode("node_shivajinagar", "Shivajinagar / Commercial St", 12.9856, 77.6050, zone="CBD"),
        RoadNode("node_richmond", "Richmond Town / Victoria Hosp", 12.9631, 77.5970, zone="CBD"),
        
        # East Bangalore & IT Corridors
        RoadNode("node_indiranagar", "Indiranagar 100ft Rd", 12.9719, 77.6412, zone="East"),
        RoadNode("node_domlur", "Domlur / EGL Flyover", 12.9609, 77.6387, zone="East"),
        RoadNode("node_old_airport_rd", "Old Airport Rd Junction", 12.9575, 77.6580, zone="East"),
        RoadNode("node_manipal_hosp", "Manipal Hospital HAL Rd", 12.9583, 77.6486, zone="East", is_hospital=True),
        RoadNode("node_marathahalli", "Marathahalli Bridge (ORR)", 12.9591, 77.6974, zone="East"),
        RoadNode("node_whitefield_itpl", "Whitefield / ITPL", 12.9863, 77.7342, zone="Whitefield"),
        RoadNode("node_vydehi_hosp", "Vydehi Super Specialty Hospital", 12.9754, 77.7291, zone="Whitefield", is_hospital=True),

        # South & South-East (Koramangala, HSR, Electronic City)
        RoadNode("node_koramangala_sony", "Koramangala Sony World Signal", 12.9352, 77.6245, zone="South-East"),
        RoadNode("node_st_johns_hosp", "St. John's Medical College & Hospital", 12.9318, 77.6186, zone="South-East", is_hospital=True),
        RoadNode("node_hsr_layout", "HSR Layout BDA Complex", 12.9121, 77.6446, zone="South-East"),
        RoadNode("node_silk_board", "Central Silk Board Junction", 12.9176, 77.6238, zone="South-East"),
        RoadNode("node_electronic_city", "Electronic City Phase 1", 12.8399, 77.6770, zone="South"),
        RoadNode("node_narayana_health", "Narayana Institute of Cardiac Sciences", 12.8182, 77.6914, zone="South", is_hospital=True),

        # South & South-West (Jayanagar, Bannerghatta)
        RoadNode("node_jayanagar_4th", "Jayanagar 4th Block", 12.9299, 77.5824, zone="South"),
        RoadNode("node_apollo_bannerghatta", "Apollo Hospital Bannerghatta Rd", 12.8954, 77.5986, zone="South", is_hospital=True),
        RoadNode("node_fortis_bannerghatta", "Fortis Hospital Bannerghatta Rd", 12.8941, 77.5979, zone="South", is_hospital=True),
        RoadNode("node_btm_layout", "BTM Layout 2nd Stage", 12.9166, 77.6101, zone="South"),

        # North Bangalore (Hebbal, Malleshwaram, Yelahanka)
        RoadNode("node_malleshwaram", "Malleshwaram 8th Cross", 12.9982, 77.5704, zone="North-West"),
        RoadNode("node_yeshwanthpur", "Yeshwanthpur Junction", 13.0280, 77.5408, zone="North-West"),
        RoadNode("node_hebbal_flyover", "Hebbal Flyover (ORR/Airport Rd)", 13.0358, 77.5970, zone="North"),
        RoadNode("node_aster_cmi_hosp", "Aster CMI Hospital Hebbal", 13.0560, 77.5919, zone="North", is_hospital=True),
        RoadNode("node_yelahanka", "Yelahanka Old Town", 13.1007, 77.5963, zone="North"),

        # Dedicated Ambulance Stations
        RoadNode("station_central_cbd", "CBD Emergency Response Station", 12.9730, 77.6080, zone="CBD", is_station=True),
        RoadNode("station_indiranagar", "Indiranagar Fire & EMS Depot", 12.9700, 77.6390, zone="East", is_station=True),
        RoadNode("station_koramangala", "Koramangala EMS Station", 12.9340, 77.6200, zone="South-East", is_station=True),
        RoadNode("station_whitefield", "Whitefield EMS Hub", 12.9800, 77.7300, zone="Whitefield", is_station=True),
        RoadNode("station_hebbal", "Hebbal North EMS Post", 13.0380, 77.5950, zone="North", is_station=True),
        RoadNode("station_ecity", "Electronic City Quick Response Base", 12.8420, 77.6750, zone="South", is_station=True),
    ]

    for node in nodes_data:
        net.add_node(node)

    # 2. Road Edges
    edges_data = [
        # CBD Mesh
        RoadEdge("e_majestic_mg", "node_majestic", "node_mg_road", 4.2, RoadType.PRIMARY_ARTERIAL, 40.0, congestion_factor=1.5),
        RoadEdge("e_mg_shivaji", "node_mg_road", "node_shivajinagar", 1.8, RoadType.SECONDARY, 30.0, congestion_factor=1.2),
        RoadEdge("e_mg_richmond", "node_mg_road", "node_richmond", 1.9, RoadType.SECONDARY, 35.0, congestion_factor=1.2),
        RoadEdge("e_richmond_jayanagar", "node_richmond", "node_jayanagar_4th", 4.1, RoadType.PRIMARY_ARTERIAL, 45.0, congestion_factor=1.3),
        RoadEdge("e_mg_station", "node_mg_road", "station_central_cbd", 0.5, RoadType.RESIDENTIAL, 25.0, congestion_factor=1.0),

        # CBD to East & Old Airport Rd
        RoadEdge("e_mg_indiranagar", "node_mg_road", "node_indiranagar", 4.3, RoadType.PRIMARY_ARTERIAL, 45.0, congestion_factor=1.4),
        RoadEdge("e_indira_station", "node_indiranagar", "station_indiranagar", 0.4, RoadType.RESIDENTIAL, 25.0, congestion_factor=1.0),
        RoadEdge("e_indira_domlur", "node_indiranagar", "node_domlur", 2.1, RoadType.PRIMARY_ARTERIAL, 40.0, congestion_factor=1.3),
        RoadEdge("e_domlur_oldairport", "node_domlur", "node_old_airport_rd", 2.2, RoadType.PRIMARY_ARTERIAL, 40.0, congestion_factor=1.4),
        RoadEdge("e_oldairport_manipal", "node_old_airport_rd", "node_manipal_hosp", 1.1, RoadType.PRIMARY_ARTERIAL, 35.0, congestion_factor=1.2),
        RoadEdge("e_manipal_domlur", "node_manipal_hosp", "node_domlur", 1.4, RoadType.PRIMARY_ARTERIAL, 35.0, congestion_factor=1.1),
        RoadEdge("e_oldairport_marathahalli", "node_old_airport_rd", "node_marathahalli", 4.8, RoadType.PRIMARY_ARTERIAL, 45.0, congestion_factor=1.6),

        # Marathahalli to Whitefield & ITPL
        RoadEdge("e_maratha_whitefield", "node_marathahalli", "node_whitefield_itpl", 5.2, RoadType.PRIMARY_ARTERIAL, 40.0, congestion_factor=1.5),
        RoadEdge("e_whitefield_vydehi", "node_whitefield_itpl", "node_vydehi_hosp", 1.5, RoadType.SECONDARY, 30.0, congestion_factor=1.1),
        RoadEdge("e_whitefield_station", "node_whitefield_itpl", "station_whitefield", 0.8, RoadType.RESIDENTIAL, 25.0, congestion_factor=1.0),

        # Domlur / Koramangala / HSR / Silk Board
        RoadEdge("e_domlur_kora", "node_domlur", "node_koramangala_sony", 3.4, RoadType.PRIMARY_ARTERIAL, 40.0, congestion_factor=1.5),
        RoadEdge("e_kora_stjohns", "node_koramangala_sony", "node_st_johns_hosp", 0.9, RoadType.SECONDARY, 30.0, congestion_factor=1.2),
        RoadEdge("e_kora_station", "node_koramangala_sony", "station_koramangala", 0.5, RoadType.RESIDENTIAL, 25.0, congestion_factor=1.0),
        RoadEdge("e_stjohns_silkboard", "node_st_johns_hosp", "node_silk_board", 2.3, RoadType.PRIMARY_ARTERIAL, 35.0, congestion_factor=1.8),
        RoadEdge("e_kora_hsr", "node_koramangala_sony", "node_hsr_layout", 3.2, RoadType.SECONDARY, 35.0, congestion_factor=1.3),
        RoadEdge("e_hsr_silkboard", "node_hsr_layout", "node_silk_board", 2.4, RoadType.PRIMARY_ARTERIAL, 35.0, congestion_factor=1.7),
        RoadEdge("e_hsr_marathahalli", "node_hsr_layout", "node_marathahalli", 7.6, RoadType.EXPRESSWAY, 65.0, congestion_factor=1.8),

        # Silk Board to Electronic City
        RoadEdge("e_silkboard_ecity", "node_silk_board", "node_electronic_city", 9.8, RoadType.EXPRESSWAY, 75.0, congestion_factor=1.2),
        RoadEdge("e_ecity_narayana", "node_electronic_city", "node_narayana_health", 3.1, RoadType.PRIMARY_ARTERIAL, 45.0, congestion_factor=1.1),
        RoadEdge("e_ecity_station", "node_electronic_city", "station_ecity", 0.6, RoadType.RESIDENTIAL, 25.0, congestion_factor=1.0),

        # South Bangalore: BTM, Jayanagar, Bannerghatta Hospitals
        RoadEdge("e_silkboard_btm", "node_silk_board", "node_btm_layout", 1.8, RoadType.PRIMARY_ARTERIAL, 35.0, congestion_factor=1.4),
        RoadEdge("e_btm_jayanagar", "node_btm_layout", "node_jayanagar_4th", 3.3, RoadType.SECONDARY, 35.0, congestion_factor=1.3),
        RoadEdge("e_btm_apollo", "node_btm_layout", "node_apollo_bannerghatta", 3.0, RoadType.PRIMARY_ARTERIAL, 40.0, congestion_factor=1.4),
        RoadEdge("e_apollo_fortis", "node_apollo_bannerghatta", "node_fortis_bannerghatta", 0.3, RoadType.SECONDARY, 30.0, congestion_factor=1.0),
        RoadEdge("e_jayanagar_stjohns", "node_jayanagar_4th", "node_st_johns_hosp", 3.9, RoadType.PRIMARY_ARTERIAL, 40.0, congestion_factor=1.3),

        # North Bangalore: CBD to Malleshwaram, Hebbal, Yelahanka
        RoadEdge("e_majestic_malleswaram", "node_majestic", "node_malleshwaram", 2.6, RoadType.PRIMARY_ARTERIAL, 40.0, congestion_factor=1.3),
        RoadEdge("e_malleswaram_yeshwanth", "node_malleshwaram", "node_yeshwanthpur", 3.8, RoadType.PRIMARY_ARTERIAL, 45.0, congestion_factor=1.4),
        RoadEdge("e_shivaji_hebbal", "node_shivajinagar", "node_hebbal_flyover", 6.8, RoadType.PRIMARY_ARTERIAL, 50.0, congestion_factor=1.4),
        RoadEdge("e_yeshwanth_hebbal", "node_yeshwanthpur", "node_hebbal_flyover", 5.9, RoadType.PRIMARY_ARTERIAL, 50.0, congestion_factor=1.3),
        RoadEdge("e_hebbal_aster", "node_hebbal_flyover", "node_aster_cmi_hosp", 2.3, RoadType.PRIMARY_ARTERIAL, 50.0, congestion_factor=1.1),
        RoadEdge("e_hebbal_station", "node_hebbal_flyover", "station_hebbal", 0.4, RoadType.RESIDENTIAL, 25.0, congestion_factor=1.0),
        RoadEdge("e_hebbal_yelahanka", "node_hebbal_flyover", "node_yelahanka", 7.4, RoadType.EXPRESSWAY, 70.0, congestion_factor=1.2),
        RoadEdge("e_hebbal_marathahalli", "node_hebbal_flyover", "node_marathahalli", 13.5, RoadType.EXPRESSWAY, 60.0, congestion_factor=1.6),
    ]

    for edge in edges_data:
        net.add_edge(edge)

    return net
