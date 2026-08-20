"""Predictive dispatch strategy: demand-aware ambulance positioning.

Uses the trained demand prediction model to proactively reposition
idle ambulances toward zones with predicted high demand, then dispatches
using both current state and predicted future conditions.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

from ..dispatch.base import BaseDispatchStrategy, DispatchDecision
from ..dispatch.aureon_intelligence import AureonDecisionEngine
from ..generators.incident_generator import Incident, IncidentSeverity
from ..models.ambulance import Ambulance, AmbulanceCapability, AmbulanceStatus
from ..models.dynamic_city import get_zone_weights
from ..models.hospital import Hospital
from ..network.road_graph import RoadNetwork
from ..ml.data_pipeline import (
    NODE_TO_ZONE, TIME_WINDOW_SEC, ALL_ZONES,
    SimulationDataExtractor, TimeWindowFeatures,
)
from ..ml.demand_model import DemandForecast, DemandPredictionModel

logger = logging.getLogger("aureon.dispatch.predictive")


@dataclass
class RepositionCommand:
    """Command to move an idle ambulance to a predicted demand zone."""

    ambulance_id: str
    target_zone: str
    target_node_id: str
    rationale: str


class AureonPredictiveDispatcher(BaseDispatchStrategy):
    """Dispatch strategy that combines demand forecasting with reactive dispatch.

    Two-phase approach:
    1. PROACTIVE: During idle periods, reposition ambulances toward zones
       predicted to have high demand in the next time window.
    2. REACTIVE: When incidents occur, dispatch the nearest available unit
       considering both current proximity and predicted zone demand pressure.
    """

    def __init__(
        self,
        demand_model: DemandPredictionModel,
        feature_extractor: SimulationDataExtractor,
    ) -> None:
        super().__init__(name="aureon_predictive")
        self.demand_model = demand_model
        self.feature_extractor = feature_extractor
        self._heuristic = AureonDecisionEngine()
        self._last_forecast: DemandForecast | None = None
        self._reposition_log: list[dict] = []

    def forecast_demand(
        self,
        sim_time_sec: float,
        ambulances: list[Ambulance],
        hospitals: list[Hospital],
        active_incidents: dict[str, Incident],
    ) -> DemandForecast:
        """Run demand forecast at current simulation state."""
        features = self.feature_extractor.extract_snapshot(
            sim_time_sec=sim_time_sec,
            ambulances=ambulances,
            hospitals=hospitals,
            active_incidents=active_incidents,
        )
        # The extract_snapshot call advances the internal window counter,
        # but we want to peek without consuming. We'll use a simpler approach:
        # just build features from current state directly.
        features = self._build_current_features(
            sim_time_sec, ambulances, hospitals, active_incidents
        )
        forecast = self.demand_model.forecast(features)
        self._last_forecast = forecast
        return forecast

    def _build_current_features(
        self,
        sim_time_sec: float,
        ambulances: list[Ambulance],
        hospitals: list[Hospital],
        active_incidents: dict[str, Incident],
    ) -> list[TimeWindowFeatures]:
        """Build feature snapshots for all zones at current time without advancing extractor."""
        from ..models.dynamic_city import TimePeriod, get_time_period

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

        from collections import defaultdict
        active_by_zone: dict[str, int] = defaultdict(int)
        for inc in active_incidents.values():
            z = NODE_TO_ZONE.get(inc.location_node_id, "Yeshwanthpur")
            active_by_zone[z] += 1

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

        features = []
        for zone in ALL_ZONES:
            center = self.feature_extractor._zone_centers.get(zone, (12.97, 77.60))
            prev_zone = self.feature_extractor._window_incidents.get(zone, [0])
            prev_total = self.feature_extractor._window_total_incidents or [0]
            prev_rt = self.feature_extractor._window_response_times.get(zone, [0.0])

            tf = TimeWindowFeatures(
                zone=zone,
                window_start_sec=sim_time_sec - TIME_WINDOW_SEC,
                window_end_sec=sim_time_sec,
                hour_of_day=hour_of_day,
                is_weekend=0.0,
                zone_latitude=center[0],
                zone_longitude=center[1],
                zone_road_density=self.feature_extractor._zone_road_density.get(zone, 1.0),
                avg_congestion_factor=self.feature_extractor._get_avg_congestion(),
                available_ambulances=float(available_count),
                busy_ambulances=float(busy_count),
                er_occupancy_ratio=avg_er_occ,
                icu_occupancy_ratio=avg_icu_occ,
                active_incidents_in_zone=float(active_by_zone.get(zone, 0)),
                incidents_in_zone_prev_window=float(prev_zone[-1]) if prev_zone else 0.0,
                incidents_in_zone_prev_2_windows=float(prev_zone[-2]) if len(prev_zone) > 1 else 0.0,
                total_incidents_prev_window=float(prev_total[-1]) if prev_total else 0.0,
                avg_response_time_prev_window=float(prev_rt[-1]) if prev_rt else 0.0,
                incident_count_next_window=0.0,  # This is what we're predicting
            )

            for tp_key in period_onehot.values():
                setattr(tf, tp_key, 1.0 if period_onehot[period] == tp_key else 0.0)

            features.append(tf)

        return features

    def reposition_idle_ambulances(
        self,
        ambulances: list[Ambulance],
        road_network: RoadNetwork,
        forecast: DemandForecast,
    ) -> list[RepositionCommand]:
        """Recommend repositioning idle ambulances based on demand forecast.

        Only repositions if demand prediction shows clear imbalance across zones.
        """
        idle_ambulances = [a for a in ambulances if a.is_available]
        if not idle_ambulances or not forecast.predictions:
            return []

        # Rank zones by predicted demand
        zone_demands = {p.zone: p.predicted_incidents for p in forecast.predictions}
        max_demand = max(zone_demands.values()) if zone_demands else 0.0
        if max_demand < 0.3:
            return []  # Don't reposition for negligible demand

        # Compute demand-weighted zone scores (normalized)
        total_demand = sum(zone_demands.values())
        zone_scores = {
            z: d / max(total_demand, 0.01) for z, d in zone_demands.items()
        }

        # Count idle ambulances per zone
        from collections import defaultdict
        idle_per_zone: dict[str, int] = defaultdict(int)
        for amb in idle_ambulances:
            zone = NODE_TO_ZONE.get(amb.current_node_id, "Yeshwanthpur")
            idle_per_zone[zone] += 1

        # Find under-served zones: high demand but few idle ambulances
        commands: list[RepositionCommand] = []
        zone_to_node = {
            zone: node_ids[0]
            for zone, node_ids in {
                "Indiranagar": ["station_indiranagar"],
                "Koramangala": ["station_koramangala"],
                "Whitefield": ["station_whitefield"],
                "Electronic City": ["station_ecity"],
                "Hebbal": ["station_hebbal"],
                "Yeshwanthpur": ["station_central_cbd"],
            }.items()
        }

        # Sort zones by demand score (descending)
        ranked_zones = sorted(zone_scores.items(), key=lambda x: -x[1])

        repositioned = 0
        for zone, score in ranked_zones:
            if repositioned >= min(2, len(idle_ambulances)):
                break  # Don't reposition too many at once

            needed = max(0, int(round(score * len(idle_ambulances))) - idle_per_zone.get(zone, 0))
            if needed <= 0:
                continue

            # Find the farthest idle ambulance from this zone
            target_node_id = zone_to_node.get(zone, "station_central_cbd")
            for amb in idle_ambulances:
                if amb.current_node_id == target_node_id:
                    continue  # Already there
                amb_zone = NODE_TO_ZONE.get(amb.current_node_id, "Yeshwanthpur")
                if amb_zone == zone:
                    continue  # Already in zone

                commands.append(RepositionCommand(
                    ambulance_id=amb.id,
                    target_zone=zone,
                    target_node_id=target_node_id,
                    rationale=f"Demand forecast: {zone}={score:.2f}, repositioning from {amb_zone}",
                ))
                repositioned += 1
                if repositioned >= needed:
                    break

        return commands

    def dispatch(
        self,
        incident: Incident,
        available_ambulances: list[Ambulance],
        hospitals: list[Hospital],
        road_network: RoadNetwork,
        all_ambulances: list[Ambulance] | None = None,
    ) -> DispatchDecision:
        """Dispatch with demand-aware scoring.

        Combines:
        1. Nearest-available ETA (base signal)
        2. Demand pressure bonus: ambulances in high-demand zones get penalty
           (they should stay there), ambulances in low-demand zones get bonus
           for repositioning efficiency
        3. Falls back to heuristic dispatch for the actual ambulance selection
        """
        if not available_ambulances:
            return DispatchDecision(ambulance_id=None, target_hospital_id=None)

        incident_zone = NODE_TO_ZONE.get(incident.location_node_id, "Yeshwanthpur")

        # If we have a forecast, use demand-aware scoring
        if self._last_forecast and self._last_forecast.predictions:
            zone_demands = {
                p.zone: p.predicted_incidents for p in self._last_forecast.predictions
            }

            # Score each ambulance with demand-aware weighting
            best_score = -float("inf")
            best_amb: Ambulance | None = None
            best_hosp: str | None = None
            best_scene_route = None

            for amb in available_ambulances:
                scene_route = road_network.calculate_route(
                    start_node_id=amb.current_node_id,
                    end_node_id=incident.location_node_id,
                    weight="time",
                )
                if not scene_route.found:
                    continue

                eta_sec = scene_route.estimated_time_seconds

                # Base score: inverse of ETA
                eta_score = min(eta_sec / 900.0, 2.0)

                # Capability match
                cap_match = amb.can_handle(incident.required_capability)
                cap_penalty = 0.0 if cap_match else 0.8

                # Demand pressure: penalize ambulances in high-demand zones
                amb_zone = NODE_TO_ZONE.get(amb.current_node_id, "Yeshwanthpur")
                amb_zone_demand = zone_demands.get(amb_zone, 0.0)
                incident_zone_demand = zone_demands.get(incident_zone, 0.0)

                # If ambulance is in a high-demand zone and the incident is in a low-demand zone,
                # penalize (the ambulance is better used staying in its high-demand zone)
                demand_penalty = 0.0
                if amb_zone_demand > 0.5 and incident_zone_demand < amb_zone_demand * 0.5:
                    demand_penalty = 0.3

                # Multi-incident pressure (from heuristic)
                if all_ambulances:
                    active_count = sum(
                        1 for a in all_ambulances
                        if not a.is_available and a.current_node_id == amb.current_node_id
                    )
                    pressure = (active_count / max(len(all_ambulances), 1)) * 0.2
                else:
                    pressure = 0.0

                total_score = -(eta_score + cap_penalty + demand_penalty + pressure)

                if total_score > best_score:
                    best_score = total_score
                    best_amb = amb
                    best_scene_route = scene_route

                    # Hospital selection (reuse heuristic)
                    hosp_decision = self._heuristic.dispatch(
                        incident=incident,
                        available_ambulances=[amb],
                        hospitals=hospitals,
                        road_network=road_network,
                        all_ambulances=all_ambulances,
                    )
                    best_hosp = hosp_decision.target_hospital_id

            if best_amb is None:
                return DispatchDecision(ambulance_id=None, target_hospital_id=None)

            return DispatchDecision(
                ambulance_id=best_amb.id,
                target_hospital_id=best_hosp,
                scene_route=best_scene_route,
                estimated_scene_eta_sec=best_scene_route.estimated_time_seconds if best_scene_route else 0.0,
                priority_level=1 if incident.severity in (IncidentSeverity.CRITICAL, IncidentSeverity.HIGH) else 2,
                rationale=f"Predictive dispatch: demand-weighted scoring for {incident_zone}",
                metadata={
                    "is_capability_matched": best_amb.can_handle(incident.required_capability),
                    "strategy": "predictive",
                },
            )

        # Fallback to heuristic if no forecast available
        return self._heuristic.dispatch(
            incident=incident,
            available_ambulances=available_ambulances,
            hospitals=hospitals,
            road_network=road_network,
            all_ambulances=all_ambulances,
        )
