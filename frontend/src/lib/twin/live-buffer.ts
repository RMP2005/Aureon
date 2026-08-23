/**
 * Transient live-state buffer for the twin (Phase 10B).
 *
 * Snapshot data flows here from TanStack Query's fetcher; the render loop
 * reads it every frame via plain mutable fields. Deliberately NOT React
 * state — entity motion must never trigger re-renders.
 */
import type { RunLiveState } from '@/lib/api';
import { project } from './projection';

export interface AmbulanceMotion {
  /** Currently rendered position. */
  x: number;
  z: number;
  /** Snapshot target position — eased toward each frame. */
  tx: number;
  tz: number;
  id: string;
  callsign: string;
  capability: string;
  status: string;
  missionsCompleted: number;
}

export interface ActiveIncident {
  id: string;
  x: number;
  z: number;
  severity: string;
  category: string;
  requiredCapability: string;
}

interface LiveBuffer {
  version: number;
  ambulances: Map<string, AmbulanceMotion>;
  incidents: ActiveIncident[];
  simTimeFormatted: string;
  tick: number;
  strategy: string;
  completedIncidents: number;
  pendingQueue: number;
  fleetTotal: number;
  fleetAvailable: number;
}

const buffer: LiveBuffer = {
  version: 0,
  ambulances: new Map(),
  incidents: [],
  simTimeFormatted: '--:--:--',
  tick: 0,
  strategy: '—',
  completedIncidents: 0,
  pendingQueue: 0,
  fleetTotal: 0,
  fleetAvailable: 0,
};

/** Easing rate for dead-reckoned ambulance motion (per second). */
const MOTION_RATE = 3.2;

export function getLiveBuffer(): LiveBuffer {
  return buffer;
}

/**
 * Ingest a fresh engine snapshot. Existing entities ease toward their new
 * targets; new entities spawn at target; vanished entities are removed.
 *
 * REPLAY CONTRACT: this function is the single ingestion point for twin
 * state. Scenario replay (Phase 10D+ Demo Mode) is a snapshot stream fed
 * through this same entry — the render loop neither knows nor cares
 * whether frames originate from a live engine or a recording.
 */
export function ingestLiveState(state: RunLiveState): void {
  const seen = new Set<string>();

  let available = 0;
  for (const a of state.ambulances) {
    seen.add(a.id);
    const [tx, tz] = project(a.longitude, a.latitude);
    const existing = buffer.ambulances.get(a.id);
    if (existing) {
      existing.tx = tx;
      existing.tz = tz;
      existing.status = a.status;
      existing.missionsCompleted = a.missions_completed;
    } else {
      buffer.ambulances.set(a.id, {
        id: a.id,
        callsign: a.callsign,
        capability: a.capability,
        status: a.status,
        missionsCompleted: a.missions_completed,
        x: tx,
        z: tz,
        tx,
        tz,
      });
    }
    if (a.status === 'available' || a.status === 'at_station') available += 1;
  }
  for (const id of buffer.ambulances.keys()) {
    if (!seen.has(id)) buffer.ambulances.delete(id);
  }

  buffer.incidents = state.active_incidents.map((inc) => {
    const [x, z] = project(inc.longitude, inc.latitude);
    return {
      id: inc.id,
      x,
      z,
      severity: inc.severity,
      category: inc.category,
      requiredCapability: inc.required_capability,
    };
  });

  buffer.simTimeFormatted = state.sim_time_formatted;
  buffer.tick = state.tick;
  buffer.strategy = state.strategy;
  buffer.completedIncidents = state.completed_incidents_count;
  buffer.pendingQueue = state.pending_queue_count;
  buffer.fleetTotal = state.ambulances.length;
  buffer.fleetAvailable = available;
  buffer.version += 1;
}

/**
 * Advance rendered positions toward snapshot targets.
 * Frame-rate independent exponential ease.
 */
export function advanceMotions(dt: number): void {
  const k = 1 - Math.exp(-MOTION_RATE * dt);
  for (const m of buffer.ambulances.values()) {
    m.x += (m.tx - m.x) * k;
    m.z += (m.tz - m.z) * k;
  }
}
