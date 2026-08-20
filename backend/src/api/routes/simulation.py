"""Simulation management endpoints."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter

from src.models.schemas import (
    ResponseEnvelope,
    SimulationCreateRequest,
    SimulationResponse,
    SimulationStatus,
)

router = APIRouter(prefix="/simulations", tags=["simulation"])


@router.post("", response_model=ResponseEnvelope)
async def create_simulation(
    request: SimulationCreateRequest,
) -> ResponseEnvelope:
    """Create and initialize a new simulation."""
    sim = SimulationResponse(
        id=str(uuid.uuid4()),
        name=request.name,
        status=SimulationStatus.IDLE,
        tick=0,
        created_at=datetime.now(timezone.utc),
    )
    return ResponseEnvelope(data=sim.model_dump())


@router.get("/{simulation_id}", response_model=ResponseEnvelope)
async def get_simulation(simulation_id: str) -> ResponseEnvelope:
    """Get simulation status by ID."""
    # Placeholder — will integrate with simulation engine
    sim = SimulationResponse(
        id=simulation_id,
        name="placeholder",
        status=SimulationStatus.IDLE,
        tick=0,
    )
    return ResponseEnvelope(data=sim.model_dump())


@router.get("", response_model=ResponseEnvelope)
async def list_simulations() -> ResponseEnvelope:
    """List all simulations."""
    return ResponseEnvelope(data=[])


@router.delete("/{simulation_id}", response_model=ResponseEnvelope)
async def delete_simulation(simulation_id: str) -> ResponseEnvelope:
    """Stop and remove a simulation."""
    return ResponseEnvelope(data={"id": simulation_id, "deleted": True})
