"""Tests for live simulation status tracking (Phase 9D)."""

import asyncio
import time
import uuid

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


# --- Phase 10A-BE: run-scoped live twin state ---


@pytest.mark.asyncio
async def test_live_state_endpoint_returns_city_snapshot() -> None:
    """A registered engine snapshots deterministically through the API."""
    svc = get_simulation_service()
    run_id, engine, _schedule, strategy, params = svc._create_run(
        strategy_name="aureon",
        duration_minutes=30.0,
        incident_rate_per_hour=12.0,
        seed=11,
    )
    svc._tracker.create(run_id, strategy.name, params["duration_minutes"] * 60.0)
    svc._active_engines[run_id] = engine
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get(f"/api/v1/simulation/{run_id}/state")
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["run_id"] == run_id
        assert len(data["ambulances"]) == 14
        assert data["hospitals"]
        assert "tick" in data and "sim_time_sec" in data
        assert data["run_status"]["run_id"] == run_id

        # After the engine is deregistered (run finished), the endpoint must 404
        svc._active_engines.pop(run_id, None)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            gone = await client.get(f"/api/v1/simulation/{run_id}/state")
        assert gone.status_code == 404
    finally:
        svc._active_engines.pop(run_id, None)


def test_get_run_state_unknown_run_returns_none() -> None:
    assert get_simulation_service().get_run_state("sim_does_not_exist") is None


@pytest.mark.asyncio
async def test_live_state_endpoint_404_after_completion() -> None:
    svc = get_simulation_service()
    info = svc.start_simulation_background(
        strategy_name="baseline",
        duration_minutes=5.0,
        incident_rate_per_hour=3.0,
        seed=21,
    )
    run_id = info["run_id"]
    deadline = time.time() + 60
    while time.time() < deadline:
        prog = svc._tracker.get(run_id)
        if prog and prog["status"] in ("completed", "failed"):
            break
        await asyncio.sleep(0.2)
    assert prog["status"] == "completed"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(f"/api/v1/simulation/{run_id}/state")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_live_state_endpoint_unknown_run_returns_404() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/simulation/sim_nonexistent/state")
    assert res.status_code == 404


# --- Phase 10B: wall-clock pacing keeps runs observable ---


@pytest.mark.asyncio
async def test_paced_run_stays_live_and_serves_snapshots() -> None:
    """wall_clock_factor stretches a run over real time so the twin can poll it."""
    svc = get_simulation_service()
    info = svc.start_simulation_background(
        strategy_name="baseline",
        duration_minutes=10.0,
        incident_rate_per_hour=6.0,
        seed=5,
        wall_clock_factor=60.0,
    )
    run_id = info["run_id"]

    transport = ASGITransport(app=app)
    snapshots: list[dict] = []
    deadline = time.time() + 30
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        while time.time() < deadline and len(snapshots) < 2:
            res = await client.get(f"/api/v1/simulation/{run_id}/state")
            if res.status_code == 200:
                data = res.json()["data"]
                assert data["run_status"]["run_id"] == run_id
                if not snapshots or data["tick"] > snapshots[-1]["tick"]:
                    snapshots.append(data)
            await asyncio.sleep(0.25)

    # A 10-min scenario at 60× spans ≥10 wall seconds — two distinct ticks
    # must be observable through the endpoint.
    assert len(snapshots) >= 2, "paced run finished before two snapshots"
    assert snapshots[1]["sim_time_sec"] > snapshots[0]["sim_time_sec"]

    # Wait for completion; engine must then be deregistered (404).
    prog = svc._tracker.get(run_id)
    while time.time() < deadline + 60:
        prog = svc._tracker.get(run_id)
        if prog and prog["status"] in ("completed", "failed"):
            break
        await asyncio.sleep(0.5)
    assert prog["status"] == "completed"
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        gone = await client.get(f"/api/v1/simulation/{run_id}/state")
    assert gone.status_code == 404


@pytest.mark.asyncio
async def test_unpaced_run_rejects_invalid_wall_clock_factor() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/simulation/run",
            json={
                "strategy": "baseline",
                "duration_minutes": 5.0,
                "incident_rate_per_hour": 3.0,
                "seed": 1,
                "wall_clock_factor": 0.5,
            },
        )
    assert res.status_code == 422


# --- Phase 9E: ProgressTracker retention cleanup tests ---


class TestProgressTrackerCleanup:
    def test_finished_entries_pruned_beyond_max(self) -> None:
        t = ProgressTracker()
        limit = t._MAX_FINISHED
        for i in range(limit + 5):
            t.create(f"run_{i}", "Hybrid", 60.0)
            t.set_status(f"run_{i}", "completed")
        assert len([k for k in t._runs if t._runs[k]["status"] == "completed"]) <= limit
        assert t.get(f"run_{limit + 4}") is not None
        assert t.get("run_0") is None

    def test_active_runs_never_pruned(self) -> None:
        t = ProgressTracker()
        limit = t._MAX_FINISHED
        t.create("active_1", "Hybrid", 60.0)
        t.set_status("active_1", "running")
        for i in range(limit + 10):
            t.create(f"done_{i}", "Nearest", 30.0)
            t.set_status(f"done_{i}", "completed")
        assert t.get("active_1") is not None
        assert t.get("active_1")["status"] == "running"
        assert t.is_running("active_1")

    def test_queued_runs_never_pruned(self) -> None:
        t = ProgressTracker()
        limit = t._MAX_FINISHED
        t.create("queued_1", "Hybrid", 60.0)
        for i in range(limit + 10):
            t.create(f"done_{i}", "Nearest", 30.0)
            t.set_status(f"done_{i}", "failed")
        assert t.get("queued_1") is not None
        assert t.get("queued_1")["status"] == "queued"

    def test_cleanup_is_bounded(self) -> None:
        t = ProgressTracker()
        limit = t._MAX_FINISHED
        for _ in range(200):
            rid = f"r_{uuid.uuid4().hex[:4]}"
            t.create(rid, "Hybrid", 60.0)
            t.set_status(rid, "completed")
        active_count = sum(1 for v in t._runs.values() if v["status"] in ("completed", "failed"))
        assert active_count <= limit

    def test_persisted_result_survives_progress_cleanup(self) -> None:
        svc = get_simulation_service()
        result = svc.run_simulation(
            strategy_name="aureon", duration_minutes=5.0,
            incident_rate_per_hour=3.0, seed=200,
        )
        run_id = result["run_id"]
        t = svc._tracker
        t.create(run_id, result["strategy"], 300.0)
        t.set_status(run_id, "completed", progress_percent=100.0)
        fresh_limit = t._MAX_FINISHED
        for i in range(fresh_limit + 5):
            extra_id = f"prune_me_{i}"
            t.create(extra_id, "Nearest", 60.0)
            t.set_status(extra_id, "completed")
        from src.services.run_store import RunStore
        store = RunStore()
        persisted = store.get_run(run_id)
        assert persisted is not None
        assert persisted["run_id"] == run_id
        assert "metrics" in persisted
