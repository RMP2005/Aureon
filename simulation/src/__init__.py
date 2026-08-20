"""Aureon Simulation — Digital Twin Emergency Response Simulation Engine."""

from .dispatch import (
    AureonDecisionEngine,
    BaseDispatchStrategy,
    DispatchDecision,
    NearestAvailableStrategy,
)
from .engine.city_engine import CitySimulationEngine, SimulationMetrics
from .generators import (
    INCIDENT_PROFILES,
    Incident,
    IncidentCategory,
    IncidentSeverity,
    ScenarioGenerator,
)
from .models.ambulance import (
    Ambulance,
    AmbulanceCapability,
    AmbulanceStatus,
    create_default_bangalore_fleet,
)
from .models.hospital import (
    Hospital,
    HospitalSpecialty,
    get_default_bangalore_hospitals,
)
from .network.bangalore_map import build_bangalore_network
from .network.road_graph import RoadEdge, RoadNetwork, RoadNode, RoadType, RouteResult

# Lazy imports to avoid circular dependencies with ML modules
def __getattr__(name: str):
    if name == "ComparisonReport":
        from .evaluation.evaluator import ComparisonReport
        return ComparisonReport
    if name == "SimulationEvaluator":
        from .evaluation.evaluator import SimulationEvaluator
        return SimulationEvaluator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "Ambulance",
    "AmbulanceCapability",
    "AmbulanceStatus",
    "AureonDecisionEngine",
    "BaseDispatchStrategy",
    "CitySimulationEngine",
    "ComparisonReport",
    "DispatchDecision",
    "Hospital",
    "HospitalSpecialty",
    "INCIDENT_PROFILES",
    "Incident",
    "IncidentCategory",
    "IncidentSeverity",
    "NearestAvailableStrategy",
    "RoadEdge",
    "RoadNetwork",
    "RoadNode",
    "RoadType",
    "RouteResult",
    "ScenarioGenerator",
    "SimulationEvaluator",
    "SimulationMetrics",
    "build_bangalore_network",
    "create_default_bangalore_fleet",
    "get_default_bangalore_hospitals",
]
