"""Core simulation engine with time-stepping and state management."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SimulationState:
    """Represents the current state of a simulation.

    Attributes:
        tick: Current simulation tick (step count).
        time: Current simulation time in seconds.
        data: Arbitrary state data specific to the simulation domain.
    """

    tick: int = 0
    time: float = 0.0
    data: dict[str, Any] = field(default_factory=dict)


class BaseEngine(ABC):
    """Abstract base class for simulation engines.

    Subclasses implement domain-specific physics and state update
    logic in the `step` method.
    """

    def __init__(self, dt: float = 0.01) -> None:
        """Initialize the engine.

        Args:
            dt: Time step size in seconds.
        """
        self.dt = dt
        self.state = SimulationState()

    @abstractmethod
    def step(self) -> SimulationState:
        """Advance the simulation by one time step.

        Returns:
            The updated simulation state.
        """
        ...

    def reset(self) -> SimulationState:
        """Reset the simulation to its initial state.

        Returns:
            The reset simulation state.
        """
        self.state = SimulationState()
        return self.state

    def run(self, steps: int) -> list[SimulationState]:
        """Run the simulation for a given number of steps.

        Args:
            steps: Number of time steps to execute.

        Returns:
            List of states captured at each step.
        """
        history: list[SimulationState] = []
        for _ in range(steps):
            state = self.step()
            history.append(state)
        return history
