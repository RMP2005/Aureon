/**
 * Replay controller (Phase 10E-1).
 *
 * Feeds recorded engine snapshots through THE SAME ingestion entry as live
 * telemetry (`ingestLiveState`) — the render loop cannot tell a replay from
 * a live run, per the REPLAY CONTRACT in live-buffer.ts. No second rendering
 * pipeline exists anywhere.
 *
 * The event journal comes verbatim from the backend's RunRecorder (observed
 * engine facts, never synthesized). Ledger entries are revealed progressively
 * as the playhead crosses each event's sim-time position.
 */
import { create } from 'zustand';
import {
  getRunReplay,
  type ReplayEvent,
  type RunLiveState,
  type RunReplayRecording,
} from '@/lib/api';
import { ingestLiveState } from './live-buffer';
import { useLedgerStore } from '@/lib/command/ledger';
import { useTwinStore } from './store';

export type ReplayStatus = 'idle' | 'loading' | 'ready' | 'playing';

interface ReplayStore {
  status: ReplayStatus;
  recording: RunReplayRecording | null;
  /** React mirror of the most recently ingested frame — drives panels. */
  currentFrame: RunLiveState | null;
  playheadSec: number;
  speed: number;
  activeEventId: string | null;
  error: string | null;

  loadRecording: (runId: string) => Promise<void>;
  play: () => void;
  pause: () => void;
  toggle: () => void;
  seek: (sec: number) => void;
  cycleSpeed: () => void;
  seekToEvent: (event: ReplayEvent) => void;
  stop: () => void;
}

export const SPEEDS = [1, 2, 4, 8] as const;

// Module-level playback machinery — deliberately outside React state.
let rafHandle: number | null = null;
let lastTickAt = 0;
let frameIndex = 0;
let revealedIds = new Set<string>();
let highestRevealedSec = 0;

export const useReplayStore = create<ReplayStore>((set, get) => {
  const durationOf = () => get().recording?.duration_seconds ?? 0;

  const ingestFrameAt = (t: number) => {
    const rec = get().recording;
    if (!rec || rec.frames.length === 0) return;
    const idx = findFrameIndex(rec.frames, t);
    if (idx !== frameIndex || get().currentFrame !== rec.frames[idx]) {
      frameIndex = idx;
      const frame = rec.frames[idx];
      ingestLiveState(frame);
      set({ currentFrame: frame });
    }
  };

  const revealEventsUpTo = (t: number) => {
    const rec = get().recording;
    if (!rec) return;
    if (t < highestRevealedSec - 0.5) {
      // Backward seek — rebuild the ledger up to the new position.
      revealedIds = new Set();
      highestRevealedSec = 0;
      useLedgerStore.getState().clear();
    }
    const due = rec.events.filter(
      (e) => e.sim_time_sec <= t && !revealedIds.has(e.id),
    );
    if (due.length === 0) return;
    due.sort((a, b) => b.sim_time_sec - a.sim_time_sec); // newest first
    useLedgerStore.getState().append(due.map(toLedgerEvent));
    for (const e of due) revealedIds.add(e.id);
    highestRevealedSec = Math.max(highestRevealedSec, t);
  };

  const tick = (now: number) => {
    const st = get();
    if (st.status !== 'playing') return;
    const dt = Math.min((now - lastTickAt) / 1000, 0.25);
    lastTickAt = now;
    const next = st.playheadSec + dt * st.speed;
    const end = durationOf();

    if (next >= end) {
      apply(next >= end ? end : next);
      set({ status: 'ready' });
      rafHandle = null;
      return;
    }
    apply(next);
    rafHandle = requestAnimationFrame(tick);
  };

  const apply = (t: number) => {
    set({ playheadSec: t });
    ingestFrameAt(t);
    revealEventsUpTo(t);
  };

  const startLoop = () => {
    if (rafHandle !== null) cancelAnimationFrame(rafHandle);
    lastTickAt = performance.now();
    rafHandle = requestAnimationFrame(tick);
  };

  return {
    status: 'idle',
    recording: null,
    currentFrame: null,
    playheadSec: 0,
    speed: 2,
    activeEventId: null,
    error: null,

    loadRecording: async (runId) => {
      cancelLoop();
      set({ status: 'loading', error: null, recording: null, currentFrame: null });
      try {
        const res = await getRunReplay(runId);
        const rec = res.data;
        if (!rec.frames.length) {
          set({ status: 'idle', error: 'Recording contains no frames.' });
          return;
        }
        revealedIds = new Set();
        highestRevealedSec = 0;
        frameIndex = 0;
        set({
          recording: rec,
          status: 'ready',
          playheadSec: 0,
          activeEventId: null,
        });
        // Present the opening state immediately through the live pipeline.
        ingestLiveState(rec.frames[0]);
        set({ currentFrame: rec.frames[0] });
      } catch (e) {
        set({
          status: 'idle',
          error:
            e instanceof Error && e.message.includes('404')
              ? 'No replay recording exists for this run.'
              : 'Failed to load replay recording.',
        });
      }
    },

    play: () => {
      const st = get();
      if (!st.recording || st.status === 'playing') return;
      // Replay from the top once the end was reached.
      if (st.playheadSec >= durationOf() - 0.01) {
        apply(0);
      }
      set({ status: 'playing' });
      startLoop();
    },

    pause: () => {
      if (get().status !== 'playing') return;
      cancelLoop();
      set({ status: 'ready' });
    },

    toggle: () => {
      if (get().status === 'playing') get().pause();
      else get().play();
    },

    seek: (sec) => {
      const rec = get().recording;
      if (!rec) return;
      const t = clamp(sec, 0, rec.duration_seconds);
      apply(t);
    },

    cycleSpeed: () => {
      const cur = get().speed;
      const idx = SPEEDS.indexOf(cur as (typeof SPEEDS)[number]);
      set({ speed: SPEEDS[(idx + 1) % SPEEDS.length] });
    },

    seekToEvent: (event) => {
      const st = get();
      if (!st.recording) return;
      apply(clamp(event.sim_time_sec, 0, st.recording.duration_seconds));
      set({ activeEventId: event.id });
      if (event.entity_kind && event.entity_id) {
        useTwinStore.getState().focus({
          kind: event.entity_kind,
          id: event.entity_id,
        });
      }
      useLedgerStore.getState().setHighlight(event.id);
    },

    stop: () => {
      cancelLoop();
      set({ status: 'idle', currentFrame: null, activeEventId: null });
    },
  };
});

function cancelLoop() {
  if (rafHandle !== null) {
    cancelAnimationFrame(rafHandle);
    rafHandle = null;
  }
}

/** Last frame whose sim-time is at or before `t` (binary search). */
function findFrameIndex(frames: RunLiveState[], t: number): number {
  let lo = 0;
  let hi = frames.length - 1;
  let ans = 0;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (frames[mid].sim_time_sec <= t) {
      ans = mid;
      lo = mid + 1;
    } else {
      hi = mid - 1;
    }
  }
  return ans;
}

function toLedgerEvent(e: ReplayEvent): Parameters<
  ReturnType<typeof useLedgerStore.getState>['append']
>[0][number] {
  return {
    id: e.id,
    kind: e.kind === 'ADMISSION' ? 'LOG' : e.kind,
    severity: e.severity ?? undefined,
    text: e.text,
    simSec: e.sim_time_sec,
    source: 'REPLAY',
  };
}

function clamp(v: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, v));
}
