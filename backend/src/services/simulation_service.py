"""Simulation orchestration service."""

import logging

logger = logging.getLogger("aureon.services.simulation")


class SimulationService:
    """Manages simulation lifecycle and state.

    This service will integrate with the simulation engine
    package to create, run, and manage digital twin simulations.
    """

    def __init__(self) -> None:
        self._simulations: dict[str, dict] = {}
        logger.info("SimulationService initialized")

    async def create(self, name: str, config: dict) -> str:
        """Create a new simulation instance."""
        import uuid
        sim_id = str(uuid.uuid4())
        self._simulations[sim_id] = {
            "name": name,
            "config": config,
            "status": "idle",
        }
        logger.info("Created simulation %s: %s", sim_id, name)
        return sim_id

    async def get(self, sim_id: str) -> dict | None:
        """Get a simulation by ID."""
        return self._simulations.get(sim_id)

    async def list_all(self) -> list[dict]:
        """List all simulations."""
        return [
            {"id": sid, **data}
            for sid, data in self._simulations.items()
        ]
