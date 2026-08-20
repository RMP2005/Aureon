"""Simulation data pipeline: extract features from simulation runs for ML training.

Generates structured training data from simulation execution, producing
features per zone per time window for demand prediction.
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field

from ..generators.incident_generator import ScenarioGenerator
from ..models.ambulance import AmbulanceStatus, create_default_bangalore_fleet
from ..models.dynamic_city import TimePeriod, get_time_period, get_zone_weights
from ..models.hospital import get_default_bangalore_hospitals
from ..network.bangalore_map import build_bangalore_network
from ..network.road_graph import RoadNetwork, RoadNode

logger = logging.getLogger("aureon.ml.data_pipeline")


# ---------------------------------------------------------------------------
# Zone mapping: bangalore_map node zones → dynamic_city prediction zones
# ---------------------------------------------------------------------------

ZONE_TO_NODE_IDS: dict[str, list[str]] = {
    "Indiranagar": ["node_indiranagar", "node_domlur", "node_old_airport_rd"],
    "Koramangala": ["node_koramangala_sony", "node_st_johns_hosp", "node_hsr_layout",
                     "node_silk_board", "node_btm_layout"],
    "Whitefield": ["node_whitefield_itpl", "node_vydehi_hosp", "node_marathahalli"],
    "Electronic City": ["node_electronic_city", "node_narayana_health",
                         "node_jayanagar_4th", "node_apollo_bannerghatta",
                         "node_fortis_bannerghatta"],
    "Hebbal": ["node_hebbal_flyover", "node_aster_cmi_hosp", "node_yelahanka",
                "node_malleshwaram"],
    "Yeshwanthpur": ["node_yeshwanthpur", "node_majestic", "node_mg_road",
                      "node_shivajinagar", "node_richmond"],
}

# Reverse mapping: node_id → prediction zone
NODE_TO_ZONE: dict[str, str] = {}
for _zone, _node_ids in ZONE_TO_NODE_IDS.items():
    for _nid in _node_ids:
        NODE_TO_ZONE[_nid] = _zone

ALL_ZONES = list(ZONE_TO_NODE_IDS.keys())

# Time window: 30 minutes = 1800 seconds
TIME_WINDOW_SEC = 1800.0


@dataclass
class TimeWindowFeatures:
    """Features for a single zone in a single time window."""

    # Identifiers
    zone: str
    window_start_sec: float
    window_end_sec: float

    # Temporal features
    hour_of_day: float = 0.0
    is_weekend: float = 0.0
    time_period_early_morning: float = 0.0
    time_period_morning_peak: float = 0.0
    time_period_midday: float = 0.0
    time_period_evening_peak: float = 0.0
    time_period_night: float = 0.0
    time_period_late_night: float = 0.0

    # Location features (static per zone)
    zone_latitude: float = 0.0
    zone_longitude: float = 0.0
    zone_road_density: float = 0.0  # Number of nodes in zone

    # Traffic features
    avg_congestion_factor: float = 1.0

    # Operational features
    available_ambulances: float = 0.0
    busy_ambulances: float = 0.0
    er_occupancy_ratio: float = 0.0
    icu_occupancy_ratio: float = 0.0
    active_incidents_in_zone: float = 0.0

    # Historical features (rolling)
    incidents_in_zone_prev_window: float = 0.0
    incidents_in_zone_prev_2_windows: float = 0.0
    total_incidents_prev_window: float = 0.0
    avg_response_time_prev_window: float = 0.0

    # Target
    incident_count_next_window: float = 0.0

    def to_feature_dict(self) -> dict[str, float]:
        """Convert to flat dictionary for ML model input."""
        return {
            "hour_of_day": self.hour_of_day,
            "is_weekend": self.is_weekend,
            "tp_early_morning": self.time_period_early_morning,
            "tp_morning_peak": self.time_period_morning_peak,
            "tp_midday": self.time_period_midday,
            "tp_evening_peak": self.time_period_evening_peak,
            "tp_night": self.time_period_night,
            "tp_late_night": self.time_period_late_night,
            "zone_latitude": self.zone_latitude,
            "zone_longitude": self.zone_longitude,
            "zone_road_density": self.zone_road_density,
            "avg_congestion": self.avg_congestion_factor,
            "available_ambulances": self.available_ambulances,
            "busy_ambulances": self.busy_ambulances,
            "er_occupancy": self.er_occupancy_ratio,
            "icu_occupancy": self.icu_occupancy_ratio,
            "active_incidents_zone": self.active_incidents_in_zone,
            "prev_window_zone_incidents": self.incidents_in_zone_prev_window,
            "prev_2windows_zone_incidents": self.incidents_in_zone_prev_2_windows,
            "prev_window_total_incidents": self.total_incidents_prev_window,
            "prev_window_avg_rt": self.avg_response_time_prev_window,
        }


@dataclass
class TrainingDataset:
    """Collected training data from simulation runs."""

    features: list[TimeWindowFeatures] = field(default_factory=list)
    feature_names: list[str] = field(default_factory=list)

    @property
    def size(self) -> int:
        return len(self.features)

    def to_X_y(self) -> tuple[list[list[float]], list[float]]:
        """Convert to feature matrix and target vector."""
        if not self.features:
            return [], []
        self.feature_names = list(self.features[0].to_feature_dict().keys())
        X = [list(f.to_feature_dict().values()) for f in self.features]
        y = [f.incident_count_next_window for f in self.features]
        return X, y

    def to_dicts(self) -> list[dict[str, float]]:
        """Convert to list of feature dictionaries."""
        return [f.to_feature_dict() for f in self.features]


class SimulationDataExtractor:
    """Extracts structured features from a running simulation engine.

    Hooks into the CitySimulationEngine step() method to observe state
    at each time window boundary and record features.
    """

    def __init__(
        self,
        road_network: RoadNetwork,
        time_window_sec: float = TIME_WINDOW_SEC,
    ) -> None:
        self.road_network = road_network
        self.time_window_sec = time_window_sec

        # Zone geographic centers (lat/lon averages from node data)
        self._zone_centers: dict[str, tuple[float, float]] = {}
        self._zone_road_density: dict[str, float] = {}
        self._compute_zone_stats()

        # Rolling history
        self._window_incidents: dict[str, list[int]] = defaultdict(list)
        self._window_response_times: dict[str, list[float]] = defaultdict(list)
        self._window_total_incidents: list[int] = []
        self._current_window_start: float = 0.0
        self._current_window_incidents: dict[str, int] = defaultdict(int)
        self._current_window_rts: dict[str, list[float]] = defaultdict(list)

    def _compute_zone_stats(self) -> None:
        """Pre-compute zone centers and road density."""
        for zone, node_ids in ZONE_TO_NODE_IDS.items():
            lats, lons = [], []
            for nid in node_ids:
                node = self.road_network.nodes.get(nid)
                if node:
                    lats.append(node.latitude)
                    lons.append(node.longitude)
            if lats:
                self._zone_centers[zone] = (
                    sum(lats) / len(lats),
                    sum(lons) / len(lons),
                )
            self._zone_road_density[zone] = float(len(node_ids))

    def _get_avg_congestion(self) -> float:
        """Compute average congestion across all edges."""
        total = 0.0
        count = 0
        for edges in self.road_network._adjacency.values():
            for edge in edges:
                total += edge.congestion_factor
                count += 1
        return total / count if count > 0 else 1.0

    def record_incident(self, incident_node_id: str, response_time_sec: float | None) -> None:
        """Record an incident occurrence during the current time window."""
        zone = NODE_TO_ZONE.get(incident_node_id, "Yeshwanthpur")
        self._current_window_incidents[zone] += 1
        if response_time_sec is not None:
            self._current_window_rts[zone].append(response_time_sec)

    def extract_snapshot(
        self,
        sim_time_sec: float,
        ambulances: list,
        hospitals: list,
        active_incidents: dict,
    ) -> list[TimeWindowFeatures]:
        """Extract features at a time window boundary.

        Call this every `time_window_sec`. Returns features for all zones.
        """
        window_start = self._current_window_start
        window_end = sim_time_sec

        # Finalize current window counts
        for zone in ALL_ZONES:
            self._window_incidents[zone].append(
                self._current_window_incidents.get(zone, 0)
            )
            self._window_response_times[zone].append(
                sum(self._current_window_rts.get(zone, []))
                / max(len(self._current_window_rts.get(zone, [])), 1)
            )
        self._window_total_incidents.append(sum(self._current_window_incidents.values()))

        # Keep only last 2 windows of history
        for zone in ALL_ZONES:
            if len(self._window_incidents[zone]) > 2:
                self._window_incidents[zone] = self._window_incidents[zone][-2:]
            if len(self._window_response_times[zone]) > 2:
                self._window_response_times[zone] = self._window_response_times[zone][-2:]
        if len(self._window_total_incidents) > 2:
            self._window_total_incidents = self._window_total_incidents[-2:]

        # Compute operational state
        available_count = sum(1 for a in ambulances if a.is_available)
        busy_count = len(ambulances) - available_count
        avg_er_occ = (
            sum(h.occupied_er_beds / max(h.total_er_beds, 1) for h in hospitals)
            / max(len(hospitals), 1)
        )
        avg_icu_occ = (
            sum(h.occupied_icu_beds / max(h.total_icu_beds, 1) for h in hospitals)
            / max(len(hospitals), 1)
        )

        # Active incidents per zone
        active_by_zone: dict[str, int] = defaultdict(int)
        for inc in active_incidents.values():
            z = NODE_TO_ZONE.get(inc.location_node_id, "Yeshwanthpur")
            active_by_zone[z] += 1

        # Temporal features
        hour_of_day = (8 + sim_time_sec / 3600.0) % 24
        period = get_time_period(sim_time_sec)
        period_onehot = {
            TimePeriod.EARLY_MORNING: "tp_early_morning",
            TimePeriod.MORNING_PEAK: "tp_morning_peak",
            TimePeriod.MIDDAY: "tp_midday",
            TimePeriod.EVENING_PEAK: "tp_evening_peak",
            TimePeriod.NIGHT: "tp_night",
            TimePeriod.LATE_NIGHT: "tp_late_night",
        }

        features_list: list[TimeWindowFeatures] = []
        avg_congestion = self._get_avg_congestion()

        for zone in ALL_ZONES:
            center = self._zone_centers.get(zone, (12.97, 77.60))
            prev_zone = self._window_incidents.get(zone, [0])
            prev_total = self._window_total_incidents or [0]
            prev_rt = self._window_response_times.get(zone, [0.0])

            tf = TimeWindowFeatures(
                zone=zone,
                window_start_sec=window_start,
                window_end_sec=window_end,
                hour_of_day=hour_of_day,
                is_weekend=0.0,
                zone_latitude=center[0],
                zone_longitude=center[1],
                zone_road_density=self._zone_road_density.get(zone, 1.0),
                avg_congestion_factor=avg_congestion,
                available_ambulances=float(available_count),
                busy_ambulances=float(busy_count),
                er_occupancy_ratio=avg_er_occ,
                icu_occupancy_ratio=avg_icu_occ,
                active_incidents_in_zone=float(active_by_zone.get(zone, 0)),
                incidents_in_zone_prev_window=float(prev_zone[-1]) if prev_zone else 0.0,
                incidents_in_zone_prev_2_windows=float(prev_zone[-2]) if len(prev_zone) > 1 else 0.0,
                total_incidents_prev_window=float(prev_total[-1]) if prev_total else 0.0,
                avg_response_time_prev_window=float(prev_rt[-1]) if prev_rt else 0.0,
                incident_count_next_window=float(self._current_window_incidents.get(zone, 0)),
            )

            # One-hot encode time period
            for tp_key in period_onehot.values():
                setattr(tf, tp_key, 1.0 if period_onehot[period] == tp_key else 0.0)

            features_list.append(tf)

        # Reset for next window
        self._current_window_start = window_end
        self._current_window_incidents = defaultdict(int)
        self._current_window_rts = defaultdict(list)

        return features_list

    def generate_training_data(
        self,
        num_seeds: int = 20,
        duration_minutes: float = 60.0,
        incident_rate_per_hour: float = 14.0,
    ) -> TrainingDataset:
        """Run multiple simulations and extract training features.

        Uses the heuristic dispatch strategy to collect realistic operational data.
        """
        from ..dispatch.aureon_intelligence import AureonDecisionEngine
        from ..engine.city_engine import CitySimulationEngine

        dataset = TrainingDataset()

        for seed_idx in range(num_seeds):
            seed = 42 + seed_idx * 7  # Non-sequential seeds for diversity
            road_network = build_bangalore_network()
            hospitals = get_default_bangalore_hospitals()
            ambulances = create_default_bangalore_fleet()

            candidate_nodes = [
                (n.id, n.name, n.latitude, n.longitude)
                for n in road_network.nodes.values()
                if not n.is_station and not n.is_hospital
            ]

            gen = ScenarioGenerator(node_ids_with_coords=candidate_nodes, seed=seed)
            schedule = gen.generate_scenario_schedule(
                duration_minutes=duration_minutes,
                incident_rate_per_hour=incident_rate_per_hour,
                use_dynamic_zones=True,
            )

            extractor = SimulationDataExtractor(road_network)
            engine = CitySimulationEngine(
                road_network=road_network,
                hospitals=hospitals,
                ambulances=ambulances,
                strategy=AureonDecisionEngine(),
                enable_dynamic_traffic=True,
            )

            engine.reset()
            total_seconds = duration_minutes * 60.0
            schedule_queue = list(schedule)
            next_window_time = TIME_WINDOW_SEC

            while engine.sim_time_seconds < total_seconds:
                due: list = []
                while schedule_queue and schedule_queue[0][0] <= engine.sim_time_seconds:
                    _, inc = schedule_queue.pop(0)
                    due.append(inc)

                engine.step(new_incidents=due)

                # Record each new incident
                for inc in due:
                    extractor.record_incident(inc.location_node_id, None)

                # Record completed incident response times
                for inc in engine.completed_incidents:
                    if inc.response_time_seconds is not None:
                        zone = NODE_TO_ZONE.get(inc.location_node_id, "Yeshwanthpur")
                        extractor.record_incident(inc.location_node_id, inc.response_time_seconds)

                # Extract features at window boundaries
                if engine.sim_time_seconds >= next_window_time:
                    features = extractor.extract_snapshot(
                        sim_time_sec=engine.sim_time_seconds,
                        ambulances=engine.ambulances,
                        hospitals=engine.hospitals,
                        active_incidents=engine.active_incidents,
                    )
                    dataset.features.extend(features)
                    next_window_time += TIME_WINDOW_SEC

            logger.info(
                "Seed %d: extracted %d feature windows", seed, len(dataset.features)
            )

        logger.info("Training dataset: %d samples across %d seeds", dataset.size, num_seeds)
        return dataset
