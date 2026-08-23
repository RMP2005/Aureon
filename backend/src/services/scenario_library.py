"""Scenario Library — named, deterministic operating conditions for runs.

Each scenario applies a set of world-state modifiers to a freshly created
engine + schedule pair BEFORE execution. Scenarios never change dispatch
logic; they change the city the strategy must operate in, so comparisons
remain apples-to-apples across strategies under identical stress.

Follows the RunRecorder convention: no hard imports from the simulation
package at module scope — engine objects are used structurally (duck typed)
and the few needed symbols are resolved lazily behind try/except guards.

Phase 10E-2.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("aureon.services.scenario_library")


def _resolve_time_period(value: str) -> Any | None:
    """Lazily resolve the simulation TimePeriod enum member by value."""
    try:
        from simulation.src.models.dynamic_city import TimePeriod  # type: ignore
    except ImportError:
        from src.models.dynamic_city import TimePeriod  # type: ignore
    return TimePeriod(value)


SCENARIOS: dict[str, dict[str, Any]] = {
    "normal_operations": {
        "name": "Normal Operations",
        "tagline": "Steady demand, clear roads",
        "description": (
            "Typical day in Bangalore: moderate call volume, free-flowing "
            "traffic, hospitals with headroom. The reference condition every "
            "other scenario is measured against."
        ),
        "stress_vector": "none",
    },
    "hospital_congestion": {
        "name": "Hospital Congestion",
        "tagline": "ERs near capacity city-wide",
        "description": (
            "Every emergency department starts ~85% full with ICUs at ~90%. "
            "Receiving-hospital choice matters immediately: crews face queues "
            "and offload delays compound across the city."
        ),
        "stress_vector": "receiving capacity",
    },
    "traffic_surge": {
        "name": "Evening Peak Surge",
        "tagline": "Rush-hour congestion, all run",
        "description": (
            "The clock is pinned at evening peak: arterial roads crawl well "
            "past free-flow time for the entire mission window. ETAs stretch, "
            "coverage thins, and nearest-unit choices get expensive."
        ),
        "stress_vector": "road network",
    },
    "mass_casualty_event": {
        "name": "Mass Casualty Event",
        "tagline": "Six casualties, one site, minutes apart",
        "description": (
            "At minute 8 a multi-casualty cluster hits a single location: two "
            "critical traumas, then high-acuity and walking wounded over two "
            "minutes. Fleet-aware triage decides whether critical patients "
            "still meet gold-standard response times."
        ),
        "stress_vector": "demand spike",
    },
}

DEFAULT_SCENARIO = "normal_operations"

_SCENARIO_ORDER = [
    "normal_operations",
    "hospital_congestion",
    "traffic_surge",
    "mass_casualty_event",
]


def list_scenarios() -> list[dict[str, Any]]:
    """Registry metadata for API exposure (stable key order)."""
    return [{"key": key, **SCENARIOS[key]} for key in _SCENARIO_ORDER]


def scenario_display(key: str | None) -> str:
    """Human-readable name for persistence in run records."""
    entry = SCENARIOS.get(key or DEFAULT_SCENARIO)
    return entry["name"] if entry else SCENARIOS[DEFAULT_SCENARIO]["name"]


# --------------------------------------------------------------------------
# Modifiers — each receives (engine, schedule, hospitals) and mutates state
# in place BEFORE the run starts. Deterministic given identical inputs.
# --------------------------------------------------------------------------


def _apply_normal(engine: Any, schedule: list[Any], hospitals: list[Any]) -> None:
    """Baseline conditions — no modifications."""


def _apply_hospital_congestion(
    engine: Any, schedule: list[Any], hospitals: list[Any]
) -> None:
    """Preload ER and ICU capacity so receiving decisions face real scarcity.

    Beds are filled proportionally per facility, preserving each hospital's
    relative character (large trauma centers stay busier than small ones).
    """
    er_fill = 0.85
    icu_fill = 0.90
    for h in hospitals:
        h.occupied_er_beds = max(
            1, min(h.total_er_beds - 1, int(h.total_er_beds * er_fill))
        )
        if h.total_icu_beds > 0:
            h.occupied_icu_beds = max(
                1, min(h.total_icu_beds - 1, int(h.total_icu_beds * icu_fill))
            )


def _apply_traffic_surge(
    engine: Any, schedule: list[Any], hospitals: list[Any]
) -> None:
    """Pin the whole run at evening-peak congestion regardless of sim clock."""
    model = getattr(engine, "traffic_model", None)
    if model is None:
        logger.warning("traffic_surge skipped: engine has no dynamic traffic model")
        return
    period = _resolve_time_period("evening_peak")
    if period is None:
        return
    model.override_period = period


def _apply_mass_casualty_event(
    engine: Any, schedule: list[Any], hospitals: list[Any]
) -> None:
    """Inject a clustered multi-casualty burst early in the run.

    Six casualties of mixed severity arrive within a tight window at a single
    location — the classic MCE signature that overwhelms proximity-first
    assignment and rewards capability-aware, fleet-aware triage.
    """
    try:
        from simulation.src.generators.incident_generator import (
            INCIDENT_PROFILES,
            IncidentCategory,
            IncidentSeverity,
        )
    except ImportError:
        from src.generators.incident_generator import (  # type: ignore
            INCIDENT_PROFILES,
            IncidentCategory,
            IncidentSeverity,
        )

    candidate_nodes = [
        (n.id, n.name, n.latitude, n.longitude)
        for n in engine.road_network.nodes.values()
        if not n.is_station and not n.is_hospital
    ]
    if not candidate_nodes:
        logger.warning("MCE scenario skipped: no civilian nodes available")
        return

    # Deterministic site choice keeps runs stable for a given network build.
    node_id, node_name, lat, lon = sorted(candidate_nodes, key=lambda n: n[1])[0]

    burst_profile: list[tuple[str, str]] = [
        ("major_trauma", "critical"),
        ("traffic_collision", "critical"),
        ("traffic_collision", "high"),
        ("respiratory_distress", "high"),
        ("minor_injury", "moderate"),
        ("general_medical", "moderate"),
    ]

    IncidentCls = type(schedule[0][1]) if schedule else None
    if IncidentCls is None:
        # Empty-schedule edge case: build via the generator's own dataclasses.
        IncidentCls = _incident_cls()

    burst_start_sec = 480.0  # minute 8 — after initial warm-up calls exist
    spacing_sec = 25.0

    injected: list[tuple[float, Any]] = []
    for idx, (category_value, severity_value) in enumerate(burst_profile):
        category = IncidentCategory(category_value)
        severity = IncidentSeverity(severity_value)
        profile = INCIDENT_PROFILES[category]
        sim_time = burst_start_sec + idx * spacing_sec
        incident = IncidentCls(
            id=f"mce_{idx + 1:02d}",
            category=category,
            severity=severity,
            required_capability=profile.required_capability,
            location_node_id=node_id,
            location_name=f"{node_name} (MCE site)",
            latitude=lat,
            longitude=lon,
            reported_at_tick=int(sim_time),
            reported_at_sim_time_sec=sim_time,
            target_response_time_sec=profile.target_response_time_sec,
            base_on_scene_time_sec=profile.base_on_scene_time_sec,
        )
        injected.append((sim_time, incident))

    schedule.extend(injected)
    schedule.sort(key=lambda pair: pair[0])
    logger.info(
        "MCE scenario injected %d casualties at %s (%s)",
        len(injected),
        node_name,
        node_id,
    )


def _incident_cls() -> Any:
    try:
        from simulation.src.generators.incident_generator import (
            Incident,  # type: ignore
        )
    except ImportError:
        from src.generators.incident_generator import Incident  # type: ignore
    return Incident


_APPLIERS: dict[str, Callable[[Any, list[Any], list[Any]], None]] = {
    "normal_operations": _apply_normal,
    "hospital_congestion": _apply_hospital_congestion,
    "traffic_surge": _apply_traffic_surge,
    "mass_casualty_event": _apply_mass_casualty_event,
}


def apply_scenario(
    key: str,
    engine: Any,
    schedule: list[Any],
    hospitals: list[Any],
) -> None:
    """Apply named scenario modifiers in place. Unknown keys fall back to baseline."""
    applier = _APPLIERS.get(key)
    if applier is None:
        logger.warning("Unknown scenario '%s' — using normal operations", key)
        applier = _apply_normal
    applier(engine, schedule, hospitals)
