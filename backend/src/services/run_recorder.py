"""Evidence-layer recorder for simulation runs (Phase 10E-1).

Attached to a background run's engine via the ``recorder`` hook of
``CitySimulationEngine.run_scenario``. Produces two artifacts per run:

* Frames — full ``engine.get_current_state()`` snapshots sampled at a fixed
  SIM-TIME cadence (independent of wall-clock pacing), so a recording exists
  even for max-speed benchmark-style runs.
* Events — an append-only journal of INCIDENT / DISPATCH / ADMISSION facts
  observed directly from engine structures. Dispatch entries reuse the
  engine's own ``dispatch_log`` records verbatim, rationale included.

Nothing here is synthesized: every frame and event is an engine observation.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("aureon.services.run_recorder")


class RunRecorder:
    """Observe engine ticks, sample state frames, and journal events."""

    def __init__(
        self,
        sample_interval_sec: float = 30.0,
        max_frames: int = 600,
    ) -> None:
        self.sample_interval_sec = sample_interval_sec
        self.max_frames = max_frames

        self._frames: list[dict[str, Any]] = []
        self._events: list[dict[str, Any]] = []
        self._seq = 0

        self._last_sample_sec = float("-inf")
        self._seen_incident_ids: set[str] = set()
        self._seen_completed_ids: set[str] = set()
        # hospital_id -> (occupied_er_beds, occupied_icu_beds)
        self._prev_hospital_loads: dict[str, tuple[int, int]] = {}
        self._dispatch_log_len = 0

    # ------------------------------------------------------------------
    # Engine hook — called after every tick by run_scenario.
    # ------------------------------------------------------------------
    def observe(self, engine: Any) -> None:
        sim_t = engine.sim_time_seconds

        # DISPATCH — verbatim from the engine's own dispatch log.
        new_entries = engine.dispatch_log[self._dispatch_log_len :]
        for entry in new_entries:
            self._emit(
                kind="DISPATCH",
                sim_time_sec=float(entry["sim_time_sec"]),
                text=(
                    f"{entry['callsign']} → {entry['incident_id']} "
                    f"({entry['category']}) · {entry['rationale']}"
                ),
                severity=entry.get("severity"),
                entity_kind="ambulance",
                entity_id=entry["ambulance_id"],
                details=entry.get("decision"),
                incident_id=entry.get("incident_id"),
            )
        self._dispatch_log_len = len(engine.dispatch_log)

        # RESOLVED — incidents that left the active set as completed.
        # The outcome fields are the engine's own measurements.
        for inc in engine.completed_incidents:
            if inc.id in self._seen_completed_ids:
                continue
            self._seen_completed_ids.add(inc.id)
            rt = inc.response_time_seconds
            outcome = (
                f"response {rt / 60:.1f} min" if rt is not None else "response time n/a"
            )
            if not inc.capability_matched:
                outcome += " · capability gap"
            self._emit(
                kind="RESOLVED",
                sim_time_sec=sim_t,
                text=f"{inc.id} closed · {outcome}",
                severity=inc.severity.value,
                entity_kind="incident",
                entity_id=inc.id,
                incident_id=inc.id,
            )

        # INCIDENT — first tick an incident appears in the active set.
        for inc in engine.active_incidents.values():
            if inc.id in self._seen_incident_ids:
                continue
            self._seen_incident_ids.add(inc.id)
            self._emit(
                kind="INCIDENT",
                sim_time_sec=float(inc.reported_at_sim_time_sec),
                text=(
                    f"{inc.category.value.replace('_', ' ').upper()} "
                    f"reported · {inc.location_name}"
                ),
                severity=inc.severity.value,
                entity_kind="incident",
                entity_id=inc.id,
                incident_id=inc.id,
            )

        # ADMISSION — ER/ICU occupancy increases vs the previous tick.
        for h in engine.hospitals:
            cur = (h.occupied_er_beds, h.occupied_icu_beds)
            prev = self._prev_hospital_loads.get(h.id)
            self._prev_hospital_loads[h.id] = cur
            if prev is None:
                continue  # baseline load — not an admission event
            if cur[0] > prev[0]:
                n = cur[0] - prev[0]
                self._emit(
                    kind="ADMISSION",
                    sim_time_sec=sim_t,
                    text=(
                        f"Patient admitted · {h.name} · ER bed"
                        + (f" ×{n}" if n > 1 else "")
                    ),
                    severity=None,
                    entity_kind="hospital",
                    entity_id=h.id,
                )
            if cur[1] > prev[1]:
                n = cur[1] - prev[1]
                self._emit(
                    kind="ADMISSION",
                    sim_time_sec=sim_t,
                    text=(
                        f"Patient admitted · {h.name} · ICU bed"
                        + (f" ×{n}" if n > 1 else "")
                    ),
                    severity=None,
                    entity_kind="hospital",
                    entity_id=h.id,
                )

        # FRAME — fixed sim-time sampling cadence.
        needs_sample = (sim_t - self._last_sample_sec) >= self.sample_interval_sec or (
            not self._frames and self.max_frames > 0
        )
        if needs_sample and len(self._frames) < self.max_frames:
            self._frames.append(engine.get_current_state())
            self._last_sample_sec = sim_t

    def finish(self, engine: Any) -> None:
        """Capture the terminal frame so replays end on true final state."""
        if (
            self._frames
            and engine.sim_time_seconds > self._frames[-1]["sim_time_sec"]
            and len(self._frames) < self.max_frames
        ):
            self._frames.append(engine.get_current_state())

    # ------------------------------------------------------------------
    # Artifact assembly.
    # ------------------------------------------------------------------
    def _emit(
        self,
        *,
        kind: str,
        sim_time_sec: float,
        text: str,
        severity: str | None,
        entity_kind: str,
        entity_id: str,
        details: dict[str, Any] | None = None,
        incident_id: str | None = None,
    ) -> None:
        self._seq += 1
        event: dict[str, Any] = {
            "id": f"evt_{self._seq:05d}",
            "kind": kind,
            "sim_time_sec": round(sim_time_sec, 1),
            "text": text,
            "severity": severity,
            "entity_kind": entity_kind,
            "entity_id": entity_id,
        }
        if details:
            # Structured decision evidence (Phase 10E-2) — candidate scoring
            # and override reasons ride along with DISPATCH journal entries.
            event["details"] = details
        if incident_id:
            # Incident linkage (Phase 10F-1) — powers debrief storytelling.
            event["incident_id"] = incident_id
        self._events.append(event)

    def to_recording(
        self,
        *,
        run_id: str,
        strategy: str,
        duration_seconds: float,
    ) -> dict[str, Any]:
        events_sorted = sorted(self._events, key=lambda e: e["sim_time_sec"])
        return {
            "run_id": run_id,
            "strategy": strategy,
            "duration_seconds": duration_seconds,
            "frame_count": len(self._frames),
            "frame_interval_sec": self.sample_interval_sec,
            "event_count": len(events_sorted),
            "events": events_sorted,
            "frames": self._frames,
        }
