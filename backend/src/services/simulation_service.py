"""Simulation service bridging FastAPI backend with the Digital Twin Simulation Engine."""

from __future__ import annotations

import logging
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.core.config import settings
from src.services.run_recorder import RunRecorder
from src.services.run_store import RunStore

# Ensure workspace root and simulation are in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
SIMULATION_PATH = WORKSPACE_ROOT / "simulation"

for p in (str(WORKSPACE_ROOT), str(SIMULATION_PATH)):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from simulation.src.dispatch.aureon_intelligence import AureonDecisionEngine
    from simulation.src.dispatch.baseline import NearestAvailableStrategy
    from simulation.src.dispatch.hybrid_intelligence import HybridAureonStrategy
    from simulation.src.dispatch.adaptive_policy import AdaptiveAureonStrategy
    from simulation.src.engine.city_engine import CitySimulationEngine
    from simulation.src.evaluation.evaluator import SimulationEvaluator
    from simulation.src.generators.incident_generator import ScenarioGenerator
    from simulation.src.models.ambulance import create_default_bangalore_fleet
    from simulation.src.models.hospital import get_default_bangalore_hospitals
    from simulation.src.network.bangalore_map import build_bangalore_network
except ImportError:
    from src.dispatch.aureon_intelligence import AureonDecisionEngine  # type: ignore
    from src.dispatch.baseline import NearestAvailableStrategy  # type: ignore
    from src.dispatch.hybrid_intelligence import HybridAureonStrategy  # type: ignore
    from src.dispatch.adaptive_policy import AdaptiveAureonStrategy  # type: ignore
    from src.engine.city_engine import CitySimulationEngine  # type: ignore
    from src.evaluation.evaluator import SimulationEvaluator  # type: ignore
    from src.generators.incident_generator import ScenarioGenerator  # type: ignore
    from src.models.ambulance import create_default_bangalore_fleet  # type: ignore
    from src.models.hospital import get_default_bangalore_hospitals  # type: ignore
    from src.network.bangalore_map import build_bangalore_network  # type: ignore

logger = logging.getLogger("aureon.services.simulation")


class ProgressTracker:
    """Thread-safe in-memory progress tracking for background simulation runs."""

    _MAX_FINISHED: int = 50

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._runs: dict[str, dict[str, Any]] = {}
        self._finished_order: list[str] = []

    def create(self, run_id: str, strategy: str, duration_seconds: float) -> None:
        with self._lock:
            self._runs[run_id] = {
                "run_id": run_id,
                "status": "queued",
                "progress_percent": 0.0,
                "elapsed_seconds": 0.0,
                "duration_seconds": duration_seconds,
                "completed_incidents": 0,
                "reported_incidents": 0,
                "active_ambulances": 0,
                "available_ambulances": 0,
                "error": None,
            }

    def set_status(self, run_id: str, status: str, **kwargs: Any) -> None:
        with self._lock:
            if run_id in self._runs:
                self._runs[run_id]["status"] = status
                self._runs[run_id].update(kwargs)
                if status in ("completed", "failed"):
                    self._finished_order.append(run_id)
                    self._prune_locked()

    def _prune_locked(self) -> None:
        """Remove oldest finished entries while staying under _MAX_FINISHED. Caller holds lock."""
        while len(self._finished_order) > self._MAX_FINISHED:
            old_id = self._finished_order.pop(0)
            if old_id in self._runs and self._runs[old_id]["status"] in ("completed", "failed"):
                del self._runs[old_id]

    def snapshot_engine(self, run_id: str, engine: Any) -> None:
        """Read live state from the synchronous engine and update progress."""
        with self._lock:
            prog = self._runs.get(run_id)
            if not prog or prog["status"] != "running":
                return
            total = prog["duration_seconds"]
            elapsed = engine.sim_time_seconds
            prog["elapsed_seconds"] = round(elapsed, 1)
            prog["progress_percent"] = (
                round(min(100.0, elapsed / total * 100.0), 1) if total > 0 else 0.0
            )
            prog["completed_incidents"] = len(engine.completed_incidents)
            prog["reported_incidents"] = (
                len(engine.completed_incidents)
                + len(engine.active_incidents)
                + len(engine.pending_queue)
            )
            prog["active_ambulances"] = sum(
                1 for a in engine.ambulances if not a.is_available
            )
            prog["available_ambulances"] = sum(
                1 for a in engine.ambulances if a.is_available
            )

    def get(self, run_id: str) -> dict[str, Any] | None:
        with self._lock:
            return dict(self._runs[run_id]) if run_id in self._runs else None

    def is_running(self, run_id: str) -> bool:
        with self._lock:
            return self._runs.get(run_id, {}).get("status") == "running"


class SimulationService:
    """Manages digital twin simulation runs, state snapshots, and strategy comparisons."""

    def __init__(self, db_path: str | None = None) -> None:
        self.road_network = build_bangalore_network()
        self.hospitals = get_default_bangalore_hospitals()
        self.ambulances = create_default_bangalore_fleet()

        # Active default simulation engine (uses validated hybrid strategy)
        self.active_engine = CitySimulationEngine(
            road_network=self.road_network,
            hospitals=self.hospitals,
            ambulances=self.ambulances,
            strategy=HybridAureonStrategy(),
        )

        # Persistent run storage
        self._store = RunStore(db_path=db_path)
        self._tracker = ProgressTracker()
        # Live engines for runs executing in background threads (Phase 10A-BE).
        # Keyed by run_id; enables run-scoped twin state polling.
        self._active_engines: dict[str, Any] = {}
        logger.info("SimulationService initialized with Bangalore Digital Twin topology")

    def get_city_state(self) -> dict[str, Any]:
        """Retrieve real-time state of the city digital twin."""
        return self.active_engine.get_current_state()

    def _resolve_strategy(self, strategy_name: str) -> Any:
        """Resolve strategy name string to a strategy instance."""
        return (
            HybridAureonStrategy()
            if strategy_name.lower() in ("aureon", "hybrid", "intelligent")
            else AdaptiveAureonStrategy()
            if strategy_name.lower() in ("adaptive",)
            else NearestAvailableStrategy()
            if strategy_name.lower() in ("baseline", "nearest")
            else HybridAureonStrategy()  # default fallback
        )

    def _create_run(
        self,
        strategy_name: str,
        duration_minutes: float,
        incident_rate_per_hour: float,
        seed: int,
    ) -> tuple[str, CitySimulationEngine, list[tuple[float, Any]], Any, dict[str, Any]]:
        """Set up simulation components without executing. Returns (run_id, engine, schedule, strategy, params)."""
        run_id = f"sim_{uuid.uuid4().hex[:8]}"
        strategy = self._resolve_strategy(strategy_name)

        fleet = create_default_bangalore_fleet()
        engine = CitySimulationEngine(
            road_network=self.road_network,
            hospitals=get_default_bangalore_hospitals(),
            ambulances=fleet,
            strategy=strategy,
        )

        candidate_nodes = [
            (n.id, n.name, n.latitude, n.longitude)
            for n in self.road_network.nodes.values()
            if not n.is_station and not n.is_hospital
        ]
        generator = ScenarioGenerator(node_ids_with_coords=candidate_nodes, seed=seed)
        schedule = generator.generate_scenario_schedule(
            duration_minutes=duration_minutes,
            incident_rate_per_hour=incident_rate_per_hour,
        )

        params = {
            "duration_minutes": duration_minutes,
            "incident_rate_per_hour": incident_rate_per_hour,
            "seed": seed,
        }
        return run_id, engine, schedule, strategy, params

    def run_simulation(
        self,
        strategy_name: str = "aureon",
        duration_minutes: float = 60.0,
        incident_rate_per_hour: float = 12.0,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Execute a full scenario simulation run (synchronous, blocking)."""
        run_id, engine, schedule, strategy, params = self._create_run(
            strategy_name, duration_minutes, incident_rate_per_hour, seed,
        )

        try:
            metrics = engine.run_scenario(schedule=schedule, duration_minutes=params["duration_minutes"])
        except Exception as exc:
            self._store.save_run(
                run_id,
                {"run_id": run_id, "strategy": strategy.name},
                status="failed",
                error_message=str(exc),
            )
            raise

        result_data = {
            "run_id": run_id,
            "strategy": strategy.name,
            "parameters": params,
            "metrics": metrics.to_dict(),
            "dispatch_log_sample": engine.dispatch_log[:15],
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }

        self._store.save_run(run_id, result_data)
        return result_data

    def start_simulation_background(
        self,
        strategy_name: str = "aureon",
        duration_minutes: float = 60.0,
        incident_rate_per_hour: float = 12.0,
        seed: int = 42,
        wall_clock_factor: float | None = None,
    ) -> dict[str, Any]:
        """Start a simulation in a background thread and return run_id immediately."""
        run_id, engine, schedule, strategy, params = self._create_run(
            strategy_name, duration_minutes, incident_rate_per_hour, seed,
        )

        duration_seconds = params["duration_minutes"] * 60.0
        self._tracker.create(run_id, strategy.name, duration_seconds)
        self._active_engines[run_id] = engine

        thread = threading.Thread(
            target=self._run_background,
            args=(run_id, engine, schedule, strategy, params),
            kwargs={"wall_clock_factor": wall_clock_factor},
            daemon=True,
        )
        thread.start()
        return {"run_id": run_id, "status": "queued"}

    def _run_background(
        self,
        run_id: str,
        engine: CitySimulationEngine,
        schedule: list[tuple[float, Any]],
        strategy: Any,
        params: dict[str, Any],
        wall_clock_factor: float | None = None,
    ) -> None:
        """Execute simulation in background thread with progress monitoring."""
        duration_seconds = params["duration_minutes"] * 60.0
        # Evidence layer (Phase 10E-1): record frames + event journal for
        # replay. Sampling is sim-time based, so pacing does not affect it.
        recorder = RunRecorder()

        mon = threading.Thread(
            target=self._monitor_run,
            args=(run_id, engine, duration_seconds),
            daemon=True,
        )

        try:
            self._tracker.set_status(run_id, "running")
            mon.start()
            metrics = engine.run_scenario(
                schedule=schedule,
                duration_minutes=params["duration_minutes"],
                wall_clock_factor=wall_clock_factor,
                recorder=recorder,
            )
            recorder.finish(engine)

            result_data = {
                "run_id": run_id,
                "strategy": strategy.name,
                "parameters": params,
                "metrics": metrics.to_dict(),
                "dispatch_log_sample": engine.dispatch_log[:15],
                "executed_at": datetime.now(timezone.utc).isoformat(),
            }
            self._store.save_run(run_id, result_data)
            try:
                self._store.save_recording(
                    recorder.to_recording(
                        run_id=run_id,
                        strategy=strategy.name,
                        duration_seconds=duration_seconds,
                    )
                )
            except Exception:
                # Recording persistence must never fail the run itself.
                logger.exception("Failed to persist replay recording for %s", run_id)
            self._tracker.set_status(
                run_id, "completed", progress_percent=100.0,
                elapsed_seconds=duration_seconds,
                completed_incidents=len(engine.completed_incidents),
                reported_incidents=(
                    len(engine.completed_incidents)
                    + len(engine.active_incidents)
                    + len(engine.pending_queue)
                ),
                active_ambulances=sum(1 for a in engine.ambulances if not a.is_available),
                available_ambulances=sum(1 for a in engine.ambulances if a.is_available),
            )
        except Exception:
            logger.exception("Background simulation %s failed", run_id)
            self._tracker.set_status(run_id, "failed", error="Simulation execution failed")
            self._store.save_run(
                run_id,
                {"run_id": run_id, "strategy": strategy.name},
                status="failed",
                error_message="Background simulation failed",
            )
        finally:
            # Keep the engine briefly queryable for final-state reads; the
            # ProgressTracker retains terminal status for its retention window.
            self._active_engines.pop(run_id, None)

    def get_run_state(self, run_id: str) -> dict[str, Any] | None:
        """Snapshot the live engine state of an in-flight background run.

        Returns None when no live engine exists for the run (unknown id,
        already completed/evicted). The snapshot is defensively retried —
        the engine mutates its incident dict on a worker thread.
        """
        engine = self._active_engines.get(run_id)
        if engine is None:
            return None

        state: dict[str, Any] | None = None
        for _ in range(3):
            try:
                state = engine.get_current_state()
                break
            except RuntimeError:
                # dict changed size during iteration — retry shortly
                time.sleep(0.01)
        if state is None:
            return None

        progress = self._tracker.get(run_id)
        if progress is not None:
            state["run_status"] = progress
        state["run_id"] = run_id
        return state

    def _monitor_run(self, run_id: str, engine: CitySimulationEngine, duration_seconds: float) -> None:
        """Periodically snapshot engine state for progress tracking."""
        while self._tracker.is_running(run_id):
            self._tracker.snapshot_engine(run_id, engine)
            time.sleep(1.0)

    def run_comparison(
        self,
        duration_minutes: float = 60.0,
        incident_rate_per_hour: float = 14.0,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Run identical scenario comparison between Baseline and Aureon intelligence."""
        run_id = f"cmp_{uuid.uuid4().hex[:8]}"
        try:
            comparison = SimulationEvaluator.run_benchmark(
                duration_minutes=duration_minutes,
                incident_rate_per_hour=incident_rate_per_hour,
                seed=seed,
            )
        except Exception as exc:
            self._store.save_run(
                run_id,
                {"comparison_id": run_id},
                status="failed",
                error_message=str(exc),
            )
            raise
        report = comparison.to_dict()
        report["comparison_id"] = run_id
        report["executed_at"] = datetime.now(timezone.utc).isoformat()
        self._store.save_run(run_id, report, run_type="comparison")
        return report

    def get_run_results(self, run_id: str) -> dict[str, Any] | None:
        """Get metrics and logs of a past simulation run."""
        return self._store.get_run(run_id)

    def get_run_replay(self, run_id: str) -> dict[str, Any] | None:
        """Fetch a completed run's replay recording (frames + event journal)."""
        return self._store.get_recording(run_id)

    def list_runs(self) -> list[dict[str, Any]]:
        """List summary of all completed simulation runs."""
        return self._store.list_runs()


# Lazy singleton — created on first access so DB is initialized before construction
_simulation_service: SimulationService | None = None


def get_simulation_service() -> SimulationService:
    global _simulation_service
    if _simulation_service is None:
        _simulation_service = SimulationService()
    return _simulation_service
