"""Tests for simulation API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


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
    assert "metrics" in data["data"]
    assert data["data"]["metrics"]["total_incidents_reported"] > 0


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
