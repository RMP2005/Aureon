"""Tests for live simulation status tracking (Phase 9D)."""

import time

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.services.simulation_service import ProgressTracker, get_simulation_service


# --- ProgressTracker unit tests ---


class TestProgressTracker:
    def test_create_and_get(self) -> None:
        t = ProgressTracker()
        t.create("sim_001", "Hybrid", 600.0)
        prog = t.get("sim_001")
        assert prog is not None
        assert prog["run_id"] == "sim_001"
        assert prog["status"] == "queued"
        assert prog["progress_percent"] == 0.0
        assert prog["duration_seconds"] == 600.0

    def test_get_unknown_returns_none(self) -> None:
        t = ProgressTracker()
        assert t.get("nonexistent") is None

    def test_set_status(self) -> None:
        t = ProgressTracker()
        t.create("sim_002", "Nearest", 300.0)
        t.set_status("sim_002", "running")
        assert t.get("sim_002")["status"] == "running"

    def test_is_running(self) -> None:
        t = ProgressTracker()
        t.create("sim_003", "Hybrid", 100.0)
        assert not t.is_running("sim_003")
        t.set_status("sim_003", "running")
        assert t.is_running("sim_003")
        t.set_status("sim_003", "completed")
        assert not t.is_running("sim_003")

    def test_progress_bounded_0_to_100(self) -> None:
        t = ProgressTracker()
        t.create("sim_004", "Hybrid", 100.0)
        t.set_status("sim_004", "running")

        class FakeEngine:
            sim_time_seconds = 99999.0
            completed_incidents = []
            active_incidents = {}
            pending_queue = []
            ambulances = []

        t.snapshot_engine("sim_004", FakeEngine())
        prog = t.get("sim_004")
        assert prog is not None
        assert prog["progress_percent"] <= 100.0
        assert prog["progress_percent"] >= 0.0

    def test_snapshot_only_when_running(self) -> None:
        t = ProgressTracker()
        t.create("sim_005", "Hybrid", 60.0)

        class FakeEngine:
            sim_time_seconds = 30.0
            completed_incidents = [1, 2]
            active_incidents = {1: 2}
            pending_queue = [3]
            ambulances = []

        t.snapshot_engine("sim_005", FakeEngine())
        prog = t.get("sim_005")
        assert prog is not None
        assert prog["elapsed_seconds"] == 0.0
        assert prog["completed_incidents"] == 0

    def test_no_duplicate_workers(self) -> None:
        t = ProgressTracker()
        t.create("sim_006", "Hybrid", 60.0)
        t.set_status("sim_006", "running")
        t.set_status("sim_006", "running")
        assert t.is_running("sim_006")
        t.set_status("sim_006", "completed")
        assert t.get("sim_006")["status"] == "completed"


# --- API integration tests ---


@pytest.mark.asyncio
async def test_post_run_returns_immediately_with_run_id() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/simulation/run",
            json={
                "strategy": "aureon",
                "duration_minutes": 5.0,
                "incident_rate_per_hour": 5.0,
                "seed": 1,
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "run_id" in data["data"]
    assert data["data"]["status"] == "queued"
    assert data["data"]["run_id"].startswith("sim_")


@pytest.mark.asyncio
async def test_status_endpoint_returns_queued_or_running() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/simulation/run",
            json={"strategy": "aureon", "duration_minutes": 5.0, "incident_rate_per_hour": 5.0, "seed": 2},
        )
        run_id = res.json()["data"]["run_id"]
        time.sleep(0.2)
        status_res = await client.get(f"/api/v1/simulation/{run_id}/status")
    assert status_res.status_code == 200
    body = status_res.json()
    assert body["data"]["status"] in ("queued", "running", "completed")
    assert body["data"]["run_id"] == run_id


@pytest.mark.asyncio
async def test_completed_run_retrievable_via_results() -> None:
    svc = get_simulation_service()
    result = svc.run_simulation(
        strategy_name="aureon",
        duration_minutes=5.0,
        incident_rate_per_hour=3.0,
        seed=99,
    )
    run_id = result["run_id"]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(f"/api/v1/simulation/results/{run_id}")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["run_id"] == run_id
    assert "metrics" in data


@pytest.mark.asyncio
async def test_status_endpoint_unknown_run_returns_404() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/simulation/sim_nonexistent/status")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_background_run_eventually_completes() -> None:
    svc = get_simulation_service()
    info = svc.start_simulation_background(
        strategy_name="aureon",
        duration_minutes=5.0,
        incident_rate_per_hour=3.0,
        seed=77,
    )
    run_id = info["run_id"]
    deadline = time.time() + 60
    while time.time() < deadline:
        prog = svc._tracker.get(run_id)
        if prog and prog["status"] in ("completed", "failed"):
            break
        time.sleep(0.5)
    prog = svc._tracker.get(run_id)
    assert prog is not None
    assert prog["status"] == "completed"
    assert prog["progress_percent"] == 100.0


@pytest.mark.asyncio
async def test_background_run_error_leaks_no_internals() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/simulation/run",
            json={"strategy": "aureon", "duration_minutes": 5.0, "incident_rate_per_hour": 5.0, "seed": 3},
        )
        run_id = res.json()["data"]["run_id"]
        time.sleep(0.2)
        status_res = await client.get(f"/api/v1/simulation/{run_id}/status")
    body = status_res.json()["data"]
    if body["status"] == "failed":
        assert body["error"] is not None
        assert "Traceback" not in body["error"]
        assert "File " not in body["error"]
