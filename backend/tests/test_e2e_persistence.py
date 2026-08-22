"""Phase 9B: End-to-end persistence verification.

Proves that the real backend workflow works end-to-end after the Phase 9A
SQLite persistence migration. Each test exercises the actual API/service →
simulation → SQLite path with small, deterministic simulations.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.services.run_store import RunStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_transport = ASGITransport(app=app)
_BASE = "http://test"


async def _post_run(
    *,
    strategy: str = "aureon",
    duration_minutes: float = 5.0,
    incident_rate_per_hour: float = 2.0,
    seed: int = 9901,
) -> dict:
    """POST /api/v1/simulation/run and return the JSON body."""
    async with AsyncClient(transport=_transport, base_url=_BASE) as client:
        resp = await client.post(
            "/api/v1/simulation/run",
            json={
                "strategy": strategy,
                "duration_minutes": duration_minutes,
                "incident_rate_per_hour": incident_rate_per_hour,
                "seed": seed,
            },
        )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _get_run(run_id: str) -> dict:
    """GET /api/v1/simulation/results/{run_id} and return the JSON body."""
    async with AsyncClient(transport=_transport, base_url=_BASE) as client:
        resp = await client.get(f"/api/v1/simulation/results/{run_id}")
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _list_runs() -> list[dict]:
    """GET /api/v1/simulation/results and return the run list."""
    async with AsyncClient(transport=_transport, base_url=_BASE) as client:
        resp = await client.get("/api/v1/simulation/results")
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


# ---------------------------------------------------------------------------
# 1. Full API round-trip: run → persist → retrieve → list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_persists_and_is_retrievable() -> None:
    """POST a simulation, GET it back by run_id, verify data matches."""
    body = await _post_run(seed=9901)
    run_id = body["data"]["run_id"]

    # Retrieve by id
    fetched = await _get_run(run_id)
    fetched_data = fetched["data"]

    # run_id round-trips
    assert fetched_data["run_id"] == run_id

    # Strategy round-trips
    assert fetched_data["strategy"] == body["data"]["strategy"]

    # Parameters round-trip
    assert fetched_data["parameters"]["duration_minutes"] == 5.0
    assert fetched_data["parameters"]["incident_rate_per_hour"] == 2.0
    assert fetched_data["parameters"]["seed"] == 9901

    # Metrics present and have real values
    metrics = fetched_data["metrics"]
    assert metrics["total_incidents_reported"] > 0
    assert metrics["total_incidents_dispatched"] > 0

    # executed_at present
    assert fetched_data["executed_at"]


@pytest.mark.asyncio
async def test_list_runs_includes_persisted_run() -> None:
    """After running a simulation, list-runs includes the new run."""
    body = await _post_run(seed=9902)
    run_id = body["data"]["run_id"]

    runs = await _list_runs()
    ids = [r["run_id"] for r in runs]
    assert run_id in ids

    summary = next(r for r in runs if r["run_id"] == run_id)
    assert summary["type"] == "single_run"
    assert summary["strategy"] == body["data"]["strategy"]
    assert summary["status"] == "completed"


# ---------------------------------------------------------------------------
# 2. Fresh RunStore instance can retrieve the same run
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fresh_runstore_retrieves_persisted_run() -> None:
    """A new RunStore() (no db_path) shares the in-memory DB and can read
    the run written by SimulationService."""
    body = await _post_run(seed=9903)
    run_id = body["data"]["run_id"]

    # Create a fresh RunStore with no db_path → uses the module-level
    # default connection set by init_db(":memory:") in conftest.
    fresh_store = RunStore()
    result = fresh_store.get_run(run_id)
    assert result is not None
    assert result["run_id"] == run_id
    assert result["strategy"] == body["data"]["strategy"]


@pytest.mark.asyncio
async def test_fresh_runstore_sees_run_in_list() -> None:
    """list_runs on a fresh RunStore includes the run written by the service."""
    body = await _post_run(seed=9904)
    run_id = body["data"]["run_id"]

    fresh_store = RunStore()
    runs = fresh_store.list_runs()
    ids = [r["run_id"] for r in runs]
    assert run_id in ids


# ---------------------------------------------------------------------------
# 3. Hybrid strategy confirmed as default
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_default_strategy_is_hybrid() -> None:
    """Running with strategy='aureon' produces a Hybrid strategy result."""
    body = await _post_run(strategy="aureon", seed=9905)
    assert "Hybrid" in body["data"]["strategy"]


# ---------------------------------------------------------------------------
# 4. Comparison run persists
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_comparison_persists_and_is_retrievable() -> None:
    """POST /compare, verify the comparison run is persisted."""
    async with AsyncClient(transport=_transport, base_url=_BASE) as client:
        resp = await client.post(
            "/api/v1/simulation/compare",
            json={
                "duration_minutes": 5.0,
                "incident_rate_per_hour": 2.0,
                "seed": 9906,
            },
        )
    assert resp.status_code == 200, resp.text
    cmp_id = resp.json()["data"]["comparison_id"]

    fetched = await _get_run(cmp_id)
    assert fetched["data"]["comparison_id"] == cmp_id
    assert "baseline" in fetched["data"]
    assert "aureon_intelligence" in fetched["data"]
    assert "improvements" in fetched["data"]


# ---------------------------------------------------------------------------
# 5. Failed simulation is persisted without leaking internals
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_failed_simulation_persisted_with_error_no_internal_leak() -> None:
    """When run_simulation fails, the failed run is persisted with status
    'failed' and the API response does not leak internal details."""
    from unittest.mock import patch

    def _explode(*args: object, **kwargs: object) -> None:
        raise RuntimeError("deliberate test failure: internals must not leak")

    with patch("src.services.simulation_service.CitySimulationEngine.run_scenario", side_effect=_explode):
        async with AsyncClient(transport=_transport, base_url=_BASE) as client:
            resp = await client.post(
                "/api/v1/simulation/run",
                json={
                    "strategy": "aureon",
                    "duration_minutes": 5.0,
                    "incident_rate_per_hour": 2.0,
                    "seed": 9907,
                },
            )

    # API returns 500 with generic message, no internal details
    assert resp.status_code == 500
    detail = resp.json().get("detail", "")
    assert "Traceback" not in detail
    assert "File " not in detail
    assert "RuntimeError" not in detail
    assert "deliberate test failure" not in detail

    # The failed run IS persisted in SQLite with status=failed
    fresh_store = RunStore()
    runs = fresh_store.list_runs()
    failed_runs = [r for r in runs if r["status"] == "failed"]
    assert len(failed_runs) >= 1, "Expected at least one failed run persisted"

    failed = failed_runs[0]
    # The full result contains the error_message
    full = fresh_store.get_run(failed["run_id"])
    assert full is not None
    # run_id is present in the persisted record
    assert "run_id" in full
