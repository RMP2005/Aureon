"""Tests for API resource abuse protection (Phase 8C)."""

from collections import OrderedDict

import pytest
from httpx import ASGITransport, AsyncClient

import src.core.rate_limit as _rl_mod
from src.main import app
from src.services.simulation_service import SimulationService


# --- Rate limiting tests ---


@pytest.mark.asyncio
async def test_rate_limit_allows_requests_under_limit() -> None:
    """Requests below the rate limit succeed."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_rejects_excessive_simulation_requests() -> None:
    """Excessive requests to protected endpoints are rejected with 429."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Send more requests than the limit allows in a burst
        responses = []
        for _ in range(35):
            r = await client.get("/api/v1/simulation/state")
            responses.append(r.status_code)
        # Some should be 200, some should be 429
        assert 429 in responses
        assert 200 in responses


@pytest.mark.asyncio
async def test_rate_limit_does_not_affect_health_endpoint() -> None:
    """Health endpoint is not rate-limited."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        responses = []
        for _ in range(35):
            r = await client.get("/api/v1/health")
            responses.append(r.status_code)
        # All should be 200 - health is not protected
        assert all(code == 200 for code in responses)


# --- In-memory run storage eviction tests ---


def test_eviction_removes_oldest_when_at_capacity() -> None:
    """When max_stored_runs is exceeded, the oldest entry is evicted."""
    svc = SimulationService.__new__(SimulationService)
    svc._max_stored_runs = 3
    svc._runs = OrderedDict()

    # Insert 3 entries
    svc._store_run("run_1", {"data": "a"})
    svc._store_run("run_2", {"data": "b"})
    svc._store_run("run_3", {"data": "c"})
    assert len(svc._runs) == 3
    assert "run_1" in svc._runs

    # Insert a 4th — run_1 should be evicted
    svc._store_run("run_4", {"data": "d"})
    assert len(svc._runs) == 3
    assert "run_1" not in svc._runs
    assert "run_2" in svc._runs
    assert "run_3" in svc._runs
    assert "run_4" in svc._runs


def test_eviction_preserves_retrieval() -> None:
    """get_run_results returns None for evicted runs, data for retained runs."""
    svc = SimulationService.__new__(SimulationService)
    svc._max_stored_runs = 2
    svc._runs = OrderedDict()

    svc._store_run("old_run", {"data": "old"})
    svc._store_run("new_run", {"data": "new"})
    assert svc.get_run_results("old_run") == {"data": "old"}

    # Trigger eviction of old_run
    svc._store_run("newest_run", {"data": "newest"})
    assert svc.get_run_results("old_run") is None
    assert svc.get_run_results("new_run") == {"data": "new"}
    assert svc.get_run_results("newest_run") == {"data": "newest"}


def test_list_runs_reflects_eviction() -> None:
    """list_runs only returns entries that haven't been evicted."""
    svc = SimulationService.__new__(SimulationService)
    svc._max_stored_runs = 2
    svc._runs = OrderedDict()

    svc._store_run("a", {"executed_at": "t1"})
    svc._store_run("b", {"executed_at": "t2"})
    svc._store_run("c", {"executed_at": "t3"})

    run_ids = [r["run_id"] for r in svc.list_runs()]
    assert "a" not in run_ids
    assert "b" in run_ids
    assert "c" in run_ids
