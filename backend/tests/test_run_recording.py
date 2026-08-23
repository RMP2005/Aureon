"""Tests for the Phase 10E-1 replay evidence layer.

Covers: engine recorder hook, event journal integrity, persistence
round-trip, and the /simulation/{run_id}/replay endpoint.
"""

import asyncio
import time

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.services.run_recorder import RunRecorder
from src.services.simulation_service import get_simulation_service


def _run_short_scenario(recorder: RunRecorder | None = None):
    """Execute a small synchronous scenario, optionally recorded."""
    svc = get_simulation_service()
    _, engine, schedule, _, params = svc._create_run(
        "aureon", duration_minutes=20.0, incident_rate_per_hour=12.0, seed=42,
    )
    metrics = engine.run_scenario(
        schedule=schedule,
        duration_minutes=params["duration_minutes"],
        recorder=recorder,
    )
    return engine, metrics


class TestRecorderHook:
    def test_recorder_captures_frames_and_events(self) -> None:
        recorder = RunRecorder(sample_interval_sec=60.0)
        engine, _metrics = _run_short_scenario(recorder)

        # Frames sampled at fixed SIM-TIME cadence regardless of wall speed.
        assert len(recorder._frames) >= 2
        sim_times = [f["sim_time_sec"] for f in recorder._frames]
        assert sim_times == sorted(sim_times)
        assert abs(sim_times[-1] - engine.sim_time_seconds) < 120.0

    def test_event_journal_kinds_and_ordering(self) -> None:
        recorder = RunRecorder()
        _engine, _metrics = _run_short_scenario(recorder)

        kinds = {e["kind"] for e in recorder._events}
        assert "INCIDENT" in kinds
        assert "DISPATCH" in kinds

        sim_times = [e["sim_time_sec"] for e in recorder.to_recording(
            run_id="t", strategy="s", duration_seconds=1,
        )["events"]]
        assert sim_times == sorted(sim_times)

        # Dispatch events carry the engine's own rationale text.
        dispatches = [
            e for e in recorder._events if e["kind"] == "DISPATCH"
        ]
        assert all(e["entity_kind"] == "ambulance" for e in dispatches)
        if dispatches:
            assert all("·" in e["text"] for e in dispatches)

    def test_no_recorder_is_zero_overhead_path(self) -> None:
        """run_scenario without a recorder stays compatible."""
        _engine, metrics = _run_short_scenario(None)
        assert metrics.total_incidents_reported > 0


class TestRecordingPersistence:
    def test_save_and_get_roundtrip(self) -> None:
        svc = get_simulation_service()
        store = svc._store

        recorder = RunRecorder()
        _engine, _m = _run_short_scenario(recorder)
        recording = recorder.to_recording(
            run_id="sim_rectest",
            strategy="HybridAureonStrategy",
            duration_seconds=1200.0,
        )
        store.save_recording(recording)

        loaded = store.get_recording("sim_rectest")
        assert loaded is not None
        assert loaded["strategy"] == "HybridAureonStrategy"
        assert loaded["frame_count"] == len(recording["frames"])
        assert len(loaded["frames"]) == len(recording["frames"])
        assert loaded["events"] == recording["events"]

    def test_missing_recording_returns_none(self) -> None:
        svc = get_simulation_service()
        assert svc.get_run_replay("sim_does_not_exist") is None


@pytest.mark.asyncio
async def test_replay_endpoint_after_background_run() -> None:
    """Background runs must produce a recording consumable via the API."""
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        start = await client.post(
            "/api/v1/simulation/run",
            json={
                "strategy": "baseline",
                "duration_minutes": 15.0,
                "incident_rate_per_hour": 10.0,
                "seed": 11,
            },
        )
        assert start.status_code == 200
        run_id = start.json()["data"]["run_id"]

        svc = get_simulation_service()
        deadline = time.monotonic() + 90.0
        while time.monotonic() < deadline:
            prog = svc._tracker.get(run_id)
            if prog and prog["status"] in ("completed", "failed"):
                break
            await asyncio.sleep(0.2)

        assert prog is not None and prog["status"] == "completed", (
            "background run did not complete in time"
        )

        response = await client.get(f"/api/v1/simulation/{run_id}/replay")
        assert response.status_code == 200
        body = response.json()
        rec = body["data"]
        assert rec["run_id"] == run_id
        assert rec["frame_count"] == len(rec["frames"]) > 0
        assert isinstance(rec["events"], list)
        frames = rec["frames"]
        assert {"ambulances", "hospitals", "active_incidents"} <= set(frames[0])


@pytest.mark.asyncio
async def test_replay_endpoint_404_for_unknown_run() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/simulation/sim_nope/replay")
    assert response.status_code == 404
