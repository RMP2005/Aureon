"""API request and response schemas."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# --- Base ---

class ResponseEnvelope(BaseModel):
    """Standard API response wrapper."""

    status: str = "ok"
    data: Any = None
    error: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# --- Health ---

class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str


# --- Simulation ---

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


class SimulationResponse(BaseModel):
    """Simulation state response."""

    id: str
    name: str
    status: SimulationStatus
    tick: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


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
