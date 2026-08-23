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
    """Start a scenario simulation in the background and return run_id immediately."""
    try:
        result = get_simulation_service().start_simulation_background(
            strategy_name=request.strategy,
            duration_minutes=request.duration_minutes,
            incident_rate_per_hour=request.incident_rate_per_hour,
            seed=request.seed,
            wall_clock_factor=request.wall_clock_factor,
            scenario=request.scenario,
        )
        return ResponseEnvelope(data=result)
    except Exception as e:
        logger.exception("Simulation start failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Simulation start failed",
        ) from e


@router.get("/scenarios", response_model=ResponseEnvelope)
async def list_scenarios() -> ResponseEnvelope:
    """Expose the Scenario Library: named world-state presets for runs."""
    return ResponseEnvelope(data=get_simulation_service().get_scenarios())


@router.get("/demos", response_model=ResponseEnvelope)
async def list_demos() -> ResponseEnvelope:
    """Expose the Demo Library: curated, deterministic showcase runs."""
    return ResponseEnvelope(data=get_simulation_service().get_demos())


@router.post("/demos/{key}/launch", response_model=ResponseEnvelope)
async def launch_demo(key: str) -> ResponseEnvelope:
    """Launch a curated demo run with scripted, deterministic parameters.

    ``key="default"`` resolves the server's flagship demo.
    """
    svc = get_simulation_service()
    try:
        result = svc.launch_demo(None if key == "default" else key)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown demo '{key}'",
        )
    except Exception as e:
        logger.exception("Demo launch failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Demo launch failed",
        ) from e
    return ResponseEnvelope(data=result)


@router.get("/{run_id}/status", response_model=ResponseEnvelope)
async def get_run_status(run_id: str) -> ResponseEnvelope:
    """Get live progress status of a simulation run."""
    svc = get_simulation_service()
    progress = svc._tracker.get(run_id)
    if progress is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation run '{run_id}' not found",
        )
    return ResponseEnvelope(data=progress)


@router.get("/{run_id}/state", response_model=ResponseEnvelope)
async def get_run_live_state(run_id: str) -> ResponseEnvelope:
    """Snapshot the living digital-twin state of an in-flight run.

    Returns the engine's full city state (ambulances, hospitals, incidents)
    plus run progress. 404 once the run has completed — fetch
    /simulation/results/{run_id} for persisted outcomes instead.
    """
    state = get_simulation_service().get_run_state(run_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No live engine for run '{run_id}' "
                "(unknown id or already finished — see /simulation/results)"
            ),
        )
    return ResponseEnvelope(data=state)


@router.get("/{run_id}/replay", response_model=ResponseEnvelope)
async def get_run_replay(run_id: str) -> ResponseEnvelope:
    """Fetch a completed run's replay recording.

    Returns the sim-time-sampled state frames and the event journal
    (incidents, dispatches, hospital admissions) captured during execution.
    404 for unknown runs or runs executed before the evidence layer existed.
    """
    recording = get_simulation_service().get_run_replay(run_id)
    if recording is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No replay recording for run '{run_id}'",
        )
    return ResponseEnvelope(data=recording)


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
