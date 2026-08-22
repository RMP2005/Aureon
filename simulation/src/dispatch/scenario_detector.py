"""Scenario detection for adaptive dispatch policy.

Analyzes live simulation state to classify the current operating regime.
No future information is used — only current/observable state.

Threshold rationale:
- fleet_pressure 0.7: At 70% fleet utilization, remaining units cannot maintain
  coverage in multiple zones. Based on standard EMS staffing models where
  >70% simultaneous utilization degrades response times (NFPA 1710).
- critical_pressure 0.3: When >30% of available capacity is consumed by
  critical incidents, elective dispatch (capability optimization) is
  justified over proximity-first.
- spatial_cluster_score 0.6: When incidents are concentrated within 3km
  radius (measured via node coordinate variance), strategic repositioning
  can reduce future ETAs.
- hospital_pressure 0.8: At 80% hospital bed occupancy, diverting to
  alternative facilities prevents ambulance queueing at ER.
- coverage_deficit 0.3: When 30%+ of zones have no nearby unit, coverage
  preservation should override proximity optimization.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

from ..generators.incident_generator import Incident, IncidentSeverity
from ..models.ambulance import Ambulance, AmbulanceStatus
from ..models.hospital import Hospital
from ..network.road_graph import RoadNetwork


class DispatchMode(str, Enum):
    """Operating mode selected by the adaptive policy."""
    NORMAL = "normal"
    HIGH_DEMAND = "high_demand"
    FLEET_SCARCITY = "fleet_scarcity"
    CRITICAL_SURGE = "critical_surge"
    SPATIAL_HOTSPOT = "spatial_hotspot"
    HOSPITAL_CONGESTION = "hospital_congestion"
    ROAD_DISRUPTION = "road_disruption"
    MULTI_INCIDENT = "multi_incident"


@dataclass
class ScenarioState:
    """Observable metrics characterizing the current simulation state.

    All fields are computed from current/observable state only.
    No future information is used.
    """
    demand_level: str = "normal"            # normal / elevated / high / surge
    fleet_pressure: float = 0.0             # 0.0 to 1.0, fraction of fleet busy
    critical_pressure: float = 0.0          # critical incidents per available ambulance
    spatial_cluster_score: float = 0.0      # 0.0 (dispersed) to 1.0 (clustered)
    hospital_pressure: float = 0.0          # 0.0 (empty) to 1.0 (full)
    network_disruption: bool = False        # any corridor with congestion_factor > 2.5
    coverage_deficit: float = 0.0           # 0.0 (good) to 1.0 (bad), fraction of zones uncovered
    pending_incident_count: int = 0         # incidents waiting for dispatch
    available_ambulance_count: int = 0      # idle ambulances

    def recommended_mode(self) -> DispatchMode:
        """Select the best dispatch mode based on detected state.

        Priority ordering:
        1. Fleet scarcity — highest priority, resource-constrained
        2. Critical surge — life-threatening batch
        3. Multi-incident — simultaneous allocation
        4. Hospital congestion — avoid ER queueing
        5. Road disruption — reroute
        6. Spatial hotspot — reposition
        7. High demand — coverage-aware
        8. Normal — proximity-first hybrid
        """
        if self.fleet_pressure > 0.75:
            return DispatchMode.FLEET_SCARCITY
        if self.critical_pressure > 0.4:
            return DispatchMode.CRITICAL_SURGE
        if self.pending_incident_count >= 3:
            return DispatchMode.MULTI_INCIDENT
        if self.hospital_pressure > 0.8:
            return DispatchMode.HOSPITAL_CONGESTION
        if self.network_disruption:
            return DispatchMode.ROAD_DISRUPTION
        if self.spatial_cluster_score > 0.6:
            return DispatchMode.SPATIAL_HOTSPOT
        if self.fleet_pressure > 0.55:
            return DispatchMode.HIGH_DEMAND
        return DispatchMode.NORMAL


class ScenarioDetector:
    """Analyzes simulation state to detect the current operating regime.

    Uses measurable thresholds with documented rationale (see module docstring).
    No future information is used — only current observable state.
    """

    def __init__(
        self,
        network: RoadNetwork | None = None,
        all_ambulances: list[Ambulance] | None = None,
    ) -> None:
        self.network = network
        self.all_ambulances = all_ambulances or []
        self._station_zones: list[str] = []
        if self.all_ambulances:
            self._station_zones = list({a.base_station_id for a in self.all_ambulances})

    def detect(
        self,
        available_ambulances: list[Ambulance],
        pending_incidents: list[Incident],
        hospitals: list[Hospital],
        road_network: RoadNetwork | None = None,
    ) -> ScenarioState:
        """Detect the current scenario state from live simulation data.

        Args:
            available_ambulances: Currently idle ambulances.
            pending_incidents: Incidents waiting for dispatch.
            hospitals: Hospital entities for congestion check.
            road_network: Road network for spatial analysis (uses instance default if None).

        Returns:
            ScenarioState with all computed metrics.
        """
        net = road_network or self.network
        state = ScenarioState()

        # --- Fleet metrics ---
        total = len(self.all_ambulances) if self.all_ambulances else 1
        busy = total - len(available_ambulances)
        state.fleet_pressure = busy / total
        state.available_ambulance_count = len(available_ambulances)

        # --- Demand level ---
        n_pending = len(pending_incidents)
        state.pending_incident_count = n_pending
        if n_pending == 0:
            state.demand_level = "normal"
        elif n_pending <= 2:
            state.demand_level = "elevated"
        elif n_pending <= 4:
            state.demand_level = "high"
        else:
            state.demand_level = "surge"

        # --- Critical pressure ---
        critical_count = sum(
            1 for inc in pending_incidents
            if inc.severity in (IncidentSeverity.CRITICAL, IncidentSeverity.HIGH)
        )
        avail = max(len(available_ambulances), 1)
        state.critical_pressure = critical_count / avail

        # --- Spatial clustering ---
        if len(pending_incidents) >= 2 and net:
            state.spatial_cluster_score = self._compute_spatial_cluster(pending_incidents)

        # --- Hospital pressure ---
        if hospitals:
            total_beds = sum(h.total_er_beds + h.total_icu_beds for h in hospitals)
            occupied = sum(h.occupied_er_beds + h.occupied_icu_beds for h in hospitals)
            state.hospital_pressure = occupied / total_beds if total_beds > 0 else 0.0

        # --- Network disruption ---
        if net:
            state.network_disruption = self._detect_disruption(net)

        # --- Coverage deficit ---
        if net and self._station_zones and available_ambulances:
            state.coverage_deficit = self._compute_coverage_deficit(
                available_ambulances, net,
            )

        return state

    def _compute_spatial_cluster(self, incidents: list[Incident]) -> float:
        """Measure spatial concentration of incidents.

        Returns 0.0 (dispersed) to 1.0 (highly clustered).
        Uses coefficient of variation of pairwise distances — lower CV = more clustered.
        """
        if len(incidents) < 2:
            return 0.0

        coords = [(inc.latitude, inc.longitude) for inc in incidents]

        # Compute centroid
        mean_lat = sum(c[0] for c in coords) / len(coords)
        mean_lon = sum(c[1] for c in coords) / len(coords)

        # Compute distances from centroid
        distances = []
        for lat, lon in coords:
            d = math.sqrt((lat - mean_lat) ** 2 + (lon - mean_lon) ** 2)
            distances.append(d)

        mean_dist = sum(distances) / len(distances)
        if mean_dist < 1e-10:
            return 1.0  # All at same location

        # Coefficient of variation (lower = more clustered)
        variance = sum((d - mean_dist) ** 2 for d in distances) / len(distances)
        std_dist = math.sqrt(variance)
        cv = std_dist / mean_dist

        # Map CV to cluster score: CV=0 -> score=1.0, CV=1 -> score=0.5, CV>2 -> score~0
        score = max(0.0, 1.0 / (1.0 + cv))
        return round(score, 4)

    def _detect_disruption(self, net: RoadNetwork) -> bool:
        """Check if any road segment has extreme congestion (>2.5x base travel time)."""
        for edges in net._adjacency.values():
            for edge in edges:
                if edge.congestion_factor > 2.5:
                    return True
        return False

    def _compute_coverage_deficit(
        self,
        available_ambulances: list[Ambulance],
        net: RoadNetwork,
    ) -> float:
        """Fraction of station zones with no available ambulance within 15 minutes.

        Returns 0.0 (all zones covered) to 1.0 (no zones covered).
        Threshold: 900 seconds (15 minutes) — based on NFPA 1710 target.
        """
        if not self._station_zones:
            return 0.0

        COVERAGE_THRESHOLD_SEC = 900.0
        uncovered = 0

        for station_id in self._station_zones:
            # Check if any available ambulance is within threshold
            covered = False
            for amb in available_ambulances:
                route = net.calculate_route(
                    start_node_id=amb.current_node_id,
                    end_node_id=station_id,
                    weight="time",
                )
                if route.found and route.estimated_time_seconds <= COVERAGE_THRESHOLD_SEC:
                    covered = True
                    break
            if not covered:
                uncovered += 1

        return uncovered / len(self._station_zones)
