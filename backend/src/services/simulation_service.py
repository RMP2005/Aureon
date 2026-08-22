"""Simulation service bridging FastAPI backend with the Digital Twin Simulation Engine."""

from __future__ import annotations

import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.core.config import settings
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
        logger.info("SimulationService initialized with Bangalore Digital Twin topology")

    def get_city_state(self) -> dict[str, Any]:
        """Retrieve real-time state of the city digital twin."""
        return self.active_engine.get_current_state()

    def run_simulation(
        self,
        strategy_name: str = "aureon",
        duration_minutes: float = 60.0,
        incident_rate_per_hour: float = 12.0,
        seed: int = 42,
    ) -> dict[str, Any]:
        """Execute a full scenario simulation run."""
        run_id = f"sim_{uuid.uuid4().hex[:8]}"

        strategy = (
            HybridAureonStrategy()
            if strategy_name.lower() in ("aureon", "hybrid", "intelligent")
            else AdaptiveAureonStrategy()
            if strategy_name.lower() in ("adaptive",)
            else NearestAvailableStrategy()
            if strategy_name.lower() in ("baseline", "nearest")
            else HybridAureonStrategy()  # default fallback
        )

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

        try:
            metrics = engine.run_scenario(schedule=schedule, duration_minutes=duration_minutes)
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
            "parameters": {
                "duration_minutes": duration_minutes,
                "incident_rate_per_hour": incident_rate_per_hour,
                "seed": seed,
            },
            "metrics": metrics.to_dict(),
            "dispatch_log_sample": engine.dispatch_log[:15],
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }

        self._store.save_run(run_id, result_data)
        return result_data

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
