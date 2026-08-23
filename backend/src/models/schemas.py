"""API request and response schemas."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# --- Base ---

class ResponseEnvelope(BaseModel):
    """Standard API response wrapper."""

    status: str = "ok"
    data: Any = None
    error: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# --- Health ---

class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str


# --- Simulation ---

class SimulationRunRequest(BaseModel):
    """Request to execute a digital twin simulation run."""

    strategy: str = Field(default="aureon", description="'aureon' or 'baseline'")
    duration_minutes: float = Field(default=60.0, ge=5.0, le=120.0)
    incident_rate_per_hour: float = Field(default=12.0, ge=1.0, le=30.0)
    seed: int = Field(default=42)
    wall_clock_factor: float | None = Field(
        default=None,
        ge=1.0,
        le=600.0,
        description=(
            "Optional live-view pacing: advance N sim-seconds per wall second. "
            "Omit for maximum-speed execution."
        ),
    )


class SimulationCompareRequest(BaseModel):
    """Request to benchmark Baseline vs Aureon on identical conditions."""

    duration_minutes: float = Field(default=60.0, ge=5.0, le=120.0)
    incident_rate_per_hour: float = Field(default=14.0, ge=1.0, le=30.0)
    seed: int = Field(default=42)


class SimulationStatus(str, Enum):
    """Simulation lifecycle states."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


class SimulationCreateRequest(BaseModel):
    """Request to create a new simulation."""

    name: str = Field(..., min_length=1, max_length=128)
    description: str = ""
    config: dict[str, Any] = Field(default_factory=dict)


class RunProgressResponse(BaseModel):
    """Live progress status for a background simulation run."""

    run_id: str
    status: str = "queued"
    progress_percent: float = 0.0
    elapsed_seconds: float = 0.0
    duration_seconds: float = 0.0
    completed_incidents: int = 0
    reported_incidents: int = 0
    active_ambulances: int = 0
    available_ambulances: int = 0
    error: str | None = None


class SimulationResponse(BaseModel):
    """Simulation state response."""

    id: str
    name: str
    status: SimulationStatus
    tick: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# --- ML ---

class PredictionRequest(BaseModel):
    """Request for ML model inference."""

    model_id: str
    input_data: dict[str, Any]


class PredictionResponse(BaseModel):
    """ML inference result."""

    model_id: str
    prediction: Any
    confidence: float | None = None
    latency_ms: float | None = None
