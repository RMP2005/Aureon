'use client';

import { useMemo } from 'react';
import type { RunProgress } from '@/lib/api';
import { useLedgerStore } from '@/lib/command/ledger';

/**
 * Timeline shell (Phase 10D).
 * Run progress on a fixed scale with ledger event markers at their sim-time
 * positions. The shell is playback-ready: when scenario replay lands, this
 * becomes its scrubber.
 */
export default function TimelineShell({
  progress,
}: {
  progress: RunProgress | null;
}) {
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
        {/* Track */}
        <div className="absolute inset-x-0 top-1/2 h-[3px] -translate-y-1/2 rounded-full bg-white/8" />
        {/* Progress fill */}
        <div
          className="absolute left-0 top-1/2 h-[3px] -translate-y-1/2 rounded-full bg-teal-core transition-all duration-500"
          style={{ width: `${fillPct}%` }}
        />
        {/* Ledger markers */}
        {markers.map((m) => (
          <span
            key={m.id}
            title={m.text}
            className={`absolute top-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rotate-45 ${
              m.kind === 'INCIDENT'
                ? 'bg-crit-red'
                : m.kind === 'DISPATCH'
                  ? 'bg-teal-core'
                  : 'bg-violet-intel'
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

function format(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}
