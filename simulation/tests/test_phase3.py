"""Tests for Phase 3: Predictive intelligence layer."""

from __future__ import annotations

import pytest

from simulation.src.ml.data_pipeline import (
    ALL_ZONES, NODE_TO_ZONE, TIME_WINDOW_SEC,
    SimulationDataExtractor, TrainingDataset, TimeWindowFeatures,
)
from simulation.src.ml.demand_model import DemandPredictionModel, DemandForecast
from simulation.src.dispatch.predictive import AureonPredictiveDispatcher
from simulation.src.evaluation.evaluator import PredictionAwareEngine
from simulation.src.network.bangalore_map import build_bangalore_network


# ---------------------------------------------------------------------------
# Data Pipeline
# ---------------------------------------------------------------------------

class TestDataPipeline:
    def test_zone_mapping_completeness(self) -> None:
        assert len(ALL_ZONES) == 6
        for zone in ALL_ZONES:
            assert zone in ["Indiranagar", "Koramangala", "Whitefield",
                            "Electronic City", "Hebbal", "Yeshwanthpur"]

    def test_node_to_zone_coverage(self) -> None:
        net = build_bangalore_network()
        non_hospital_non_station = [
            n for n in net.nodes.values()
            if not n.is_hospital and not n.is_station
        ]
        for node in non_hospital_non_station:
            assert node.id in NODE_TO_ZONE, f"Node {node.id} has no zone mapping"

    def test_extractor_initialization(self) -> None:
        net = build_bangalore_network()
        ext = SimulationDataExtractor(net)
        assert len(ext._zone_centers) == 6
        assert len(ext._zone_road_density) == 6

    def test_feature_dict_keys(self) -> None:
        tf = TimeWindowFeatures(
            zone="Koramangala",
            window_start_sec=0, window_end_sec=1800,
        )
        d = tf.to_feature_dict()
        assert len(d) == 21
        assert "hour_of_day" in d
        assert "prev_window_zone_incidents" in d

    def test_training_data_generation(self) -> None:
        net = build_bangalore_network()
        ext = SimulationDataExtractor(net)
        dataset = ext.generate_training_data(num_seeds=2, duration_minutes=40, incident_rate_per_hour=14)
        assert dataset.size > 0
        X, y = dataset.to_X_y()
        assert len(X) == len(y)
        assert len(X[0]) == 21  # Feature count


# ---------------------------------------------------------------------------
# Demand Model
# ---------------------------------------------------------------------------

class TestDemandModel:
    def _trained_model(self) -> DemandPredictionModel:
        net = build_bangalore_network()
        ext = SimulationDataExtractor(net)
        dataset = ext.generate_training_data(num_seeds=3, duration_minutes=40, incident_rate_per_hour=14)
        model = DemandPredictionModel()
        model.train(dataset)
        return model

    def test_training_succeeds(self) -> None:
        model = self._trained_model()
        assert model.is_trained
        assert model.metrics.rmse >= 0
        assert model.metrics.mae >= 0

    def test_prediction_non_negative(self) -> None:
        model = self._trained_model()
        tf = TimeWindowFeatures(
            zone="Koramangala", window_start_sec=3600, window_end_sec=5400,
            hour_of_day=9.0, available_ambulances=10.0, busy_ambulances=4.0,
        )
        pred = model.predict(tf)
        assert pred.predicted_incidents >= 0
        assert pred.zone == "Koramangala"

    def test_forecast_all_zones(self) -> None:
        model = self._trained_model()
        net = build_bangalore_network()
        ext = SimulationDataExtractor(net)
        features = []
        for zone in ALL_ZONES:
            features.append(TimeWindowFeatures(
                zone=zone, window_start_sec=3600, window_end_sec=5400,
                hour_of_day=9.0,
            ))
        forecast = model.forecast(features)
        assert len(forecast.predictions) == 6
        assert forecast.total_predicted_incidents >= 0

    def test_feature_importance(self) -> None:
        model = self._trained_model()
        fi = model.metrics.feature_importance
        assert len(fi) == 21
        total = sum(fi.values())
        assert abs(total - 1.0) < 0.01  # XGBoost importances sum to ~1.0


# ---------------------------------------------------------------------------
# Predictive Dispatcher
# ---------------------------------------------------------------------------

class TestPredictiveDispatcher:
    def test_dispatch_returns_decision(self) -> None:
        net = build_bangalore_network()
        ext = SimulationDataExtractor(net)
        model = DemandPredictionModel()
        dataset = ext.generate_training_data(num_seeds=2, duration_minutes=40)
        model.train(dataset)

        dispatcher = AureonPredictiveDispatcher(demand_model=model, feature_extractor=ext)
        from simulation.src.models.ambulance import create_default_bangalore_fleet
        from simulation.src.models.hospital import get_default_bangalore_hospitals
        from simulation.src.generators.incident_generator import (
            Incident, IncidentCategory, IncidentSeverity,
        )
        from simulation.src.models.ambulance import AmbulanceCapability

        amb = create_default_bangalore_fleet()
        hosp = get_default_bangalore_hospitals()
        inc = Incident(
            id="test", category=IncidentCategory.CARDIAC_ARREST,
            severity=IncidentSeverity.CRITICAL,
            required_capability=AmbulanceCapability.ALS,
            location_node_id="node_koramangala_sony",
            location_name="Koramangala", latitude=12.935, longitude=77.624,
            reported_at_tick=0, reported_at_sim_time_sec=0.0,
        )
        decision = dispatcher.dispatch(inc, amb[:3], hosp[:2], net, amb)
        assert decision.ambulance_id is not None

    def test_reposition_returns_commands(self) -> None:
        net = build_bangalore_network()
        ext = SimulationDataExtractor(net)
        model = DemandPredictionModel()
        dataset = ext.generate_training_data(num_seeds=2, duration_minutes=40)
        model.train(dataset)

        dispatcher = AureonPredictiveDispatcher(demand_model=model, feature_extractor=ext)
        from simulation.src.models.ambulance import create_default_bangalore_fleet
        from simulation.src.evaluation.evaluator import PredictionAwareEngine
        from simulation.src.models.hospital import get_default_bangalore_hospitals

        amb = create_default_bangalore_fleet()
        hosp = get_default_bangalore_hospitals()
        from simulation.src.engine.city_engine import CitySimulationEngine
        engine = CitySimulationEngine(ambulances=amb, hospitals=hosp, enable_dynamic_traffic=True)

        forecast = dispatcher.forecast_demand(3600, amb, hosp, {})
        commands = dispatcher.reposition_idle_ambulances(amb, net, forecast)
        # Commands may be empty if demand is balanced; that's valid
        assert isinstance(commands, list)
