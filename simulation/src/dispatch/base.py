"""Abstract base interface for emergency response dispatch strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ..generators.incident_generator import Incident
from ..models.ambulance import Ambulance
from ..models.hospital import Hospital
from ..network.road_graph import RoadNetwork, RouteResult


@dataclass
class DispatchDecision:
    """The decision recommendation produced by a dispatch strategy."""

    ambulance_id: str | None
    target_hospital_id: str | None
    scene_route: RouteResult | None = None
    hospital_route: RouteResult | None = None
    priority_level: int = 1  # 1 = Code 3 (lights/sirens), 2 = Urgent, 3 = Routine
    rationale: str = ""
    estimated_scene_eta_sec: float = 0.0
    estimated_hospital_eta_sec: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseDispatchStrategy(ABC):
    """Abstract base strategy for assigning ambulances and receiving hospitals to incidents."""

    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    def dispatch(
        self,
        incident: Incident,
        available_ambulances: list[Ambulance],
        hospitals: list[Hospital],
        road_network: RoadNetwork,
        all_ambulances: list[Ambulance] | None = None,
    ) -> DispatchDecision:
        """Evaluate city state and incident to select optimal response units and destination hospital."""
        ...

    @property
    def supports_batch(self) -> bool:
        """Whether this strategy supports batch dispatch for simultaneous incidents."""
        return False

    def dispatch_batch(
        self,
        incidents: list[Incident],
        available_ambulances: list[Ambulance],
        hospitals: list[Hospital],
        road_network: RoadNetwork,
        all_ambulances: list[Ambulance] | None = None,
    ) -> list[tuple[str, DispatchDecision]]:
        """Batch-optimized dispatch for multiple simultaneous incidents.

        Override in strategies that support global optimization.
        Returns list of (incident_id, decision) pairs.
        Default implementation returns empty list (no batch optimization).
        """
        return []
