"""Core simulation engine with time-stepping and state management."""

from __future__ import annotations

import copy
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("aureon.simulation.engine")


class EngineStatus(Enum):
    """Simulation engine lifecycle states."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class SimulationState:
    """Represents the current state of a simulation.

    Attributes:
        tick: Current simulation tick (step count).
        time: Current simulation time in seconds.
        status: Engine lifecycle status.
        data: Arbitrary state data specific to the simulation domain.
    """

    tick: int = 0
    time: float = 0.0
    status: EngineStatus = EngineStatus.IDLE
    data: dict[str, Any] = field(default_factory=dict)


class BaseEngine(ABC):
    """Abstract base class for simulation engines.

    Subclasses implement domain-specific physics and state update
    logic in the `step` method.
    """

    def __init__(self, dt: float = 0.01, max_steps: int = 10000) -> None:
        """Initialize the engine.

        Args:
            dt: Time step size in seconds.
            max_steps: Maximum number of steps before auto-stop.
        """
        self.dt = dt
        self.max_steps = max_steps
        self.state = SimulationState()
        logger.info(
            "Engine initialized: dt=%.4f, max_steps=%d",
            dt,
            max_steps,
        )

    @abstractmethod
    def step(self) -> SimulationState:
        """Advance the simulation by one time step.

        Returns:
            The updated simulation state.
        """
        ...

    def reset(self) -> SimulationState:
        """Reset the simulation to its initial state."""
        self.state = SimulationState()
        logger.info("Engine reset")
        return self.state

    def run(self, steps: int | None = None) -> list[SimulationState]:
        """Run the simulation for a given number of steps.

        Args:
            steps: Number of steps. Defaults to max_steps.

        Returns:
            List of state snapshots at each step.
        """
        n = min(steps or self.max_steps, self.max_steps)
        self.state.status = EngineStatus.RUNNING
        history: list[SimulationState] = []

        logger.info("Starting simulation run for %d steps", n)
        for i in range(n):
            try:
                state = self.step()
                history.append(copy.deepcopy(state))
            except Exception:
                self.state.status = EngineStatus.ERROR
                logger.exception("Engine error at step %d", i)
                break

        if self.state.status == EngineStatus.RUNNING:
            self.state.status = EngineStatus.COMPLETED
            logger.info("Simulation completed: %d steps", len(history))

        return history

    @property
    def is_running(self) -> bool:
        """Check if the engine is currently running."""
        return self.state.status == EngineStatus.RUNNING
