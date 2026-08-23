"""Demo Library — curated, deterministic showcase runs (Phase 10F-1).

A demo is a fully-specified REAL simulation: fixed seed, named scenario,
strategy and pacing. Nothing synthetic is ever rendered — a demo simply
removes configuration friction so the system can be judged on evidence.
Determinism comes from identical seeds over identical generators.
"""

from __future__ import annotations

from typing import Any

DEMOS: dict[str, dict[str, Any]] = {
    "city_pulse": {
        "name": "City Pulse",
        "logline": "A ordinary hour, made visible",
        "description": (
            "Normal operations across Bengaluru under the Aureon hybrid "
            "policy. Watch calls arrive, units glide, and every dispatch "
            "explain itself in real time."
        ),
        "run": {
            "strategy": "aureon",
            "scenario": "normal_operations",
            "duration_minutes": 24,
            "incident_rate_per_hour": 12,
            "seed": 7,
            "wall_clock_factor": 60,
        },
    },
    "evening_gridlock": {
        "name": "Evening Gridlock",
        "logline": "Rush hour, all mission long",
        "description": (
            "The congestion clock pins at evening peak. The adaptive policy "
            "reclassifies the regime city-wide and starts trading distance "
            "for coverage — watch the mode chip shift."
        ),
        "run": {
            "strategy": "adaptive",
            "scenario": "traffic_surge",
            "duration_minutes": 30,
            "incident_rate_per_hour": 16,
            "seed": 11,
            "wall_clock_factor": 60,
        },
    },
    "er_bottleneck": {
        "name": "ER Bottleneck",
        "logline": "When the hospitals, not the streets, are the constraint",
        "description": (
            "Every emergency department starts near capacity. Suitability "
            "scoring earns its keep: receiving choices ripple into offload "
            "queues you can watch build."
        ),
        "run": {
            "strategy": "aureon",
            "scenario": "hospital_congestion",
            "duration_minutes": 28,
            "incident_rate_per_hour": 14,
            "seed": 5,
            "wall_clock_factor": 60,
        },
    },
    "mass_casualty_response": {
        "name": "Mass Casualty Response",
        "logline": "Six casualties, one site, minutes apart",
        "description": (
            "The showcase stress test. A multi-casualty cluster lands at "
            "minute 8; fleet-aware triage must hold gold-standard times for "
            "the critical patients while the walking wounded wait their turn."
        ),
        "run": {
            "strategy": "adaptive",
            "scenario": "mass_casualty_event",
            "duration_minutes": 36,
            "incident_rate_per_hour": 12,
            "seed": 21,
            "wall_clock_factor": 45,
        },
    },
}

DEFAULT_DEMO = "mass_casualty_response"

_DEMO_ORDER = [
    "city_pulse",
    "evening_gridlock",
    "er_bottleneck",
    "mass_casualty_response",
]


def list_demos() -> list[dict[str, Any]]:
    """Registry metadata for API exposure (stable key order)."""
    return [{"key": key, **DEMOS[key]} for key in _DEMO_ORDER]


def get_demo(key: str | None) -> dict[str, Any] | None:
    """Resolve a demo script by key; None when unknown. Defaults to flagship."""
    if not key:
        return {"key": DEFAULT_DEMO, **DEMOS[DEFAULT_DEMO]}
    entry = DEMOS.get(key)
    return {"key": key, **entry} if entry else None
