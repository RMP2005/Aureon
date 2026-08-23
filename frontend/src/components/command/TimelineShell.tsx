'use client';

import { useMemo, useRef } from 'react';
import type { RunProgress } from '@/lib/api';
import { useLedgerStore } from '@/lib/command/ledger';
import { SPEEDS, useReplayStore } from '@/lib/twin/replay';

/**
 * Timeline shell (Phase 10D) / replay scrubber (Phase 10E-1).
 *
 * LIVE mode: run progress on a fixed scale with observed ledger markers.
 * REPLAY mode: functional transport — drag/click to seek, play/pause,
 * speed cycling, and clickable evidence markers (incident / dispatch /
 * admission). Clicking a marker seeks, focuses the camera on the entity,
 * selects it in the scene, and flashes its Decision-Ledger entry.
 */
export default function TimelineShell({
  mode,
  progress,
}: {
  mode: 'live' | 'replay';
  progress?: RunProgress | null;
}) {
  if (mode === 'replay') return <ReplayScrubber />;
  return <LiveTimeline progress={progress ?? null} />;
}

/* ------------------------------------------------------------------ */
/* LIVE                                                                */
/* ------------------------------------------------------------------ */

function LiveTimeline({ progress }: { progress: RunProgress | null }) {
  const events = useLedgerStore((s) => s.events);
  const total = progress?.duration_seconds ?? 0;

  const markers = useMemo(
    () =>
      events
        .filter((e) => total > 0 && e.simSec <= total)
        .slice(0, 60)
        .map((e) => ({ ...e, pct: (e.simSec / total) * 100 })),
    [events, total],
  );

  const fillPct = progress?.progress_percent ?? 0;

  return (
    <div className="flex h-full items-center gap-4 px-5">
      <span className="tnum shrink-0 font-mono text-[10px] text-[var(--color-text-muted)]">
        T+{format(progress?.elapsed_seconds ?? 0)}
      </span>
      <div className="relative h-6 flex-1">
        <div className="absolute inset-x-0 top-1/2 h-[3px] -translate-y-1/2 rounded-full bg-white/8" />
        <div
          className="absolute left-0 top-1/2 h-[3px] -translate-y-1/2 rounded-full bg-teal-core transition-all duration-500"
          style={{ width: `${fillPct}%` }}
        />
        {markers.map((m) => (
          <span
            key={m.id}
            title={m.text}
            className={`absolute top-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rotate-45 ${
              MARKER_TONE[m.kind] ?? 'bg-white/40'
            }`}
            style={{ left: `${m.pct}%` }}
          />
        ))}
      </div>
      <span className="tnum shrink-0 font-mono text-[10px] text-[var(--color-text-muted)]">
        {format(total)}
      </span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* REPLAY SCRUBBER                                                     */
/* ------------------------------------------------------------------ */

const MARKER_TONE: Record<string, string> = {
  INCIDENT: 'bg-crit-red',
  DISPATCH: 'bg-teal-core',
  RESOLVED: 'bg-teal-core',
  ADMISSION: 'bg-white/70',
};

function ReplayScrubber() {
  const recording = useReplayStore((s) => s.recording);
  const status = useReplayStore((s) => s.status);
  const playheadSec = useReplayStore((s) => s.playheadSec);
  const speed = useReplayStore((s) => s.speed);
  const activeEventId = useReplayStore((s) => s.activeEventId);
  const toggle = useReplayStore((s) => s.toggle);
  const cycleSpeed = useReplayStore((s) => s.cycleSpeed);
  const seekToEvent = useReplayStore((s) => s.seekToEvent);

  const trackRef = useRef<HTMLDivElement | null>(null);
  const draggingRef = useRef(false);

  const duration = recording?.duration_seconds ?? 0;
  const pct = duration > 0 ? (playheadSec / duration) * 100 : 0;

  // Downsample dense journals so markers stay legible at any zoom.
  const markers = useMemo(() => pickSpread(recording?.events ?? [], 80), [recording]);

  const seekFromPointer = (clientX: number) => {
    const el = trackRef.current;
    if (!el || duration <= 0) return;
    const rect = el.getBoundingClientRect();
    const frac = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
    useReplayStore.getState().seek(frac * duration);
  };

  return (
    <div className="flex h-full items-center gap-4 px-4">
      {/* Transport */}
      <button
        onClick={toggle}
        disabled={status === 'loading'}
        aria-label={status === 'playing' ? 'Pause replay' : 'Play replay'}
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-teal-core/40 text-teal-core transition-colors hover:bg-teal-core/10 disabled:opacity-40"
      >
        {status === 'playing' ? <PauseIcon /> : <PlayIcon />}
      </button>
      <button
        onClick={cycleSpeed}
        className="tnum hud-stamp shrink-0 rounded-md border border-hairline-strong px-2 py-1 !text-[10px] text-[var(--color-text-secondary)] hover:border-white/20 hover:text-[var(--color-text-primary)] transition-colors"
        aria-label="Cycle playback speed"
      >
        {speed}×
      </button>

      <span className="tnum shrink-0 font-mono text-[10px] text-[var(--color-text-muted)]">
        T+{format(playheadSec)}
      </span>

      {/* Track */}
      <div
        ref={trackRef}
        role="slider"
        aria-label="Replay timeline"
        aria-valuemin={0}
        aria-valuemax={Math.round(duration)}
        aria-valuenow={Math.round(playheadSec)}
        tabIndex={0}
        className="relative h-8 min-w-0 flex-1 cursor-pointer select-none"
        onPointerDown={(e) => {
          draggingRef.current = true;
          e.currentTarget.setPointerCapture(e.pointerId);
          seekFromPointer(e.clientX);
        }}
        onPointerMove={(e) => {
          if (draggingRef.current) seekFromPointer(e.clientX);
        }}
        onPointerUp={() => {
          draggingRef.current = false;
        }}
      >
        <div className="absolute inset-x-0 top-1/2 h-[3px] -translate-y-1/2 rounded-full bg-white/8" />
        <div
          className="absolute left-0 top-1/2 h-[3px] -translate-y-1/2 rounded-full bg-teal-core"
          style={{ width: `${pct}%` }}
        />
        {/* Playhead */}
        <div
          className="pointer-events-none absolute top-1/2 h-3.5 w-[2px] -translate-x-1/2 -translate-y-1/2 bg-white/90"
          style={{ left: `${pct}%` }}
        />
        {/* Evidence markers */}
        {markers.map((e) => {
          const active = e.id === activeEventId;
          return (
            <button
              key={e.id}
              title={`${markerKindLabel(e.kind)} · T+${format(e.sim_time_sec)}\n${e.text}`}
              aria-label={e.text}
              onPointerDown={(pe) => pe.stopPropagation()}
              onClick={(me) => {
                me.stopPropagation();
                seekToEvent(e);
              }}
              className={`absolute top-1/2 h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rotate-45 transition-transform hover:scale-150 ${
                MARKER_TONE[e.kind] ?? 'bg-white/60'
              } ${active ? 'ring-2 ring-white/70 ring-offset-1 ring-offset-transparent' : ''}`}
              style={{ left: `${(e.sim_time_sec / duration) * 100}%` }}
            />
          );
        })}
      </div>

      <span className="tnum shrink-0 font-mono text-[10px] text-[var(--color-text-muted)]">
        {format(duration)}
      </span>
      <span className="hidden lg:block hud-stamp shrink-0 !text-[9px] text-[var(--color-text-muted)]">
        {SPEEDS.length}× SPEEDS · CLICK MARKERS FOR EVIDENCE
      </span>
    </div>
  );
}

/** Evenly sample up to `max` events, preserving chronological coverage. */
function pickSpread<T extends { sim_time_sec: number }>(events: T[], max: number): T[] {
  if (events.length <= max) return events;
  const step = events.length / max;
  const out: T[] = [];
  for (let i = 0; i < max; i++) out.push(events[Math.floor(i * step)]);
  return out;
}

function markerKindLabel(kind: string): string {
  switch (kind) {
    case 'INCIDENT':
      return 'INCIDENT REPORTED';
    case 'DISPATCH':
      return 'UNIT DISPATCHED';
    case 'ADMISSION':
      return 'HOSPITAL ADMISSION';
    default:
      return kind;
  }
}

function PlayIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor" aria-hidden>
      <path d="M2.5 1.5v9l8-4.5-8-4.5z" />
    </svg>
  );
}

function PauseIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor" aria-hidden>
      <path d="M2.5 1.5h2.6v9H2.5zM6.9 1.5h2.6v9H6.9z" />
    </svg>
  );
}

function format(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}
