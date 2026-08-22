"""Simulation management and Digital Twin execution endpoints."""

import asyncio
import logging

from fastapi import APIRouter, HTTPException, status

from src.models.schemas import (
    ResponseEnvelope,
    SimulationCompareRequest,
    SimulationRunRequest,
)
from src.services.simulation_service import get_simulation_service

logger = logging.getLogger("aureon.api.simulation")

router = APIRouter(prefix="/simulation", tags=["simulation"])


@router.post("/run", response_model=ResponseEnvelope)
async def run_simulation(request: SimulationRunRequest) -> ResponseEnvelope:
    """Execute a scenario simulation with specified strategy and duration."""
    try:
        result = await asyncio.to_thread(
            get_simulation_service().run_simulation,
            strategy_name=request.strategy,
            duration_minutes=request.duration_minutes,
            incident_rate_per_hour=request.incident_rate_per_hour,
            seed=request.seed,
        )
        return ResponseEnvelope(data=result)
    except Exception as e:
        logger.exception("Simulation execution failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Simulation execution failed",
        ) from e


@router.post("/compare", response_model=ResponseEnvelope)
async def compare_strategies(request: SimulationCompareRequest) -> ResponseEnvelope:
    """Run side-by-side benchmark comparing Baseline vs Aureon intelligence."""
    try:
        report = await asyncio.to_thread(
            get_simulation_service().run_comparison,
            duration_minutes=request.duration_minutes,
            incident_rate_per_hour=request.incident_rate_per_hour,
            seed=request.seed,
        )
        return ResponseEnvelope(data=report)
    except Exception as e:
        logger.exception("Strategy comparison failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Strategy comparison failed",
        ) from e


@router.get("/state", response_model=ResponseEnvelope)
async def get_simulation_state() -> ResponseEnvelope:
    """Retrieve current digital twin city state (hospitals, ambulances, incidents)."""
    state = get_simulation_service().get_city_state()
    return ResponseEnvelope(data=state)


@router.get("/results", response_model=ResponseEnvelope)
async def list_simulation_results() -> ResponseEnvelope:
    """List all completed simulation and comparison runs."""
    runs = get_simulation_service().list_runs()
    return ResponseEnvelope(data=runs)


@router.get("/results/{run_id}", response_model=ResponseEnvelope)
async def get_simulation_result(run_id: str) -> ResponseEnvelope:
    """Get metrics and details of a specific simulation or comparison run."""
    result = get_simulation_service().get_run_results(run_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation run '{run_id}' not found",
        )
    return ResponseEnvelope(data=result)
