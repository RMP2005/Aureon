"""Tests for simulation API endpoints."""

import time

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.services.simulation_service import get_simulation_service


@pytest.mark.asyncio
async def test_simulation_state_endpoint() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/simulation/state")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "ambulances" in data["data"]
    assert "hospitals" in data["data"]
    assert len(data["data"]["hospitals"]) > 0


@pytest.mark.asyncio
async def test_simulation_run_endpoint() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/simulation/run",
            json={
                "strategy": "aureon",
                "duration_minutes": 30.0,
                "incident_rate_per_hour": 10.0,
                "seed": 42,
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "run_id" in data["data"]
    assert data["data"]["status"] == "queued"
    assert data["data"]["run_id"].startswith("sim_")


@pytest.mark.asyncio
async def test_simulation_compare_endpoint() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/simulation/compare",
            json={
                "duration_minutes": 30.0,
                "incident_rate_per_hour": 10.0,
                "seed": 42,
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "baseline" in data["data"]
    assert "aureon_intelligence" in data["data"]
    assert "improvements" in data["data"]


# --- Security regression tests ---


@pytest.mark.asyncio
async def test_run_rejects_duration_over_120() -> None:
    """Regression: duration_minutes must be capped at 120."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/simulation/run",
            json={"duration_minutes": 121.0, "seed": 42},
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_run_rejects_incident_rate_over_30() -> None:
    """Regression: incident_rate_per_hour must be capped at 30."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/simulation/run",
            json={"incident_rate_per_hour": 31.0, "seed": 42},
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_compare_rejects_duration_over_120() -> None:
    """Regression: compare endpoint also enforces duration cap."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/simulation/compare",
            json={"duration_minutes": 200.0, "seed": 42},
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_run_error_hides_internal_details() -> None:
    """Regression: error response must not leak exception internals."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/simulation/run",
            json={
                "strategy": "aureon",
                "duration_minutes": 5.0,
                "incident_rate_per_hour": 1.0,
                "seed": 42,
            },
        )
    assert response.status_code == 200
    data = response.json()
    if response.status_code == 500:
        detail = data.get("detail", "")
        assert "Traceback" not in detail
        assert "File " not in detail


@pytest.mark.asyncio
async def test_run_accepts_max_valid_duration() -> None:
    """Regression: duration_minutes=120 (max valid) must be accepted."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/simulation/run",
            json={
                "strategy": "baseline",
                "duration_minutes": 120.0,
                "incident_rate_per_hour": 30.0,
                "seed": 42,
            },
        )
    assert response.status_code == 200
