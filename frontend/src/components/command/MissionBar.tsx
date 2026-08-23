'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import type { FeedStatus } from '@/hooks/useCommandFeed';
import type { RunProgress } from '@/lib/api';

/**
 * Top mission bar (Phase 10D) — run identity, sim clock, feed health.
 * STALE/LOST reflect real poll age, not assumptions.
 */
export default function MissionBar({
  runId,
  status,
  progress,
  lastSuccessAt,
}: {
  runId: string | null;
  status: FeedStatus;
  progress: RunProgress | null;
  lastSuccessAt: number;
}) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1_000);
    return () => clearInterval(t);
  }, []);

  const age = status === 'live' ? now - lastSuccessAt : Infinity;
  const feedTone =
    status === 'standby'
      ? { label: 'STANDBY', cls: 'text-[var(--color-text-muted)]' }
      : status === 'ended'
        ? { label: 'RUN ENDED', cls: 'text-violet-intel' }
        : age > 6_000
          ? { label: 'FEED LOST', cls: 'text-crit-red' }
          : age > 2_500
            ? { label: 'STALE', cls: 'text-amber-warn' }
            : { label: 'LIVE', cls: 'text-teal-core animate-pulse' };

  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-4 border-b border-hairline bg-panel-1 px-5">
      <div className="flex items-baseline gap-3 min-w-0">
        <span className="font-display text-base font-semibold tracking-tight">
          Aureon <span className="text-teal-core">·</span>{' '}
          <span className="hud-label align-middle text-[var(--color-text-secondary)]">
            Command
          </span>
        </span>
        <span className="tnum truncate font-mono text-xs text-[var(--color-text-muted)]">
          {runId ?? 'NO ACTIVE RUN'}
        </span>
      </div>

      <div className="flex items-center gap-5">
        {progress && (
          <>
            <ClockStat label="SIM TIME" value={simClock(progress.elapsed_seconds)} />
            <ClockStat
              label="PROGRESS"
              value={`${progress.progress_percent.toFixed(0)}%`}
            />
            <ClockStat
              label="FLEET"
              value={`${progress.available_ambulances}/${progress.available_ambulances + progress.active_ambulances}`}
            />
          </>
        )}
        <span className={`hud-stamp flex items-center gap-2 ${feedTone.cls}`}>
          <span className={`h-1.5 w-1.5 rounded-full bg-current ${feedTone.label === 'LIVE' ? 'animate-pulse' : ''}`} />
          {feedTone.label}
        </span>
        <Link
          href="/simulation"
          className="hud-stamp rounded-md border border-hairline-strong px-3 py-1.5 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:border-white/20 transition-colors"
        >
          LAUNCH RUN →
        </Link>
      </div>
    </header>
  );
}

function ClockStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="hidden sm:block text-right leading-tight">
      <p className="hud-stamp !text-[9px] text-[var(--color-text-muted)]">{label}</p>
      <p className="tnum font-mono text-sm">{value}</p>
    </div>
  );
}

function simClock(sec: number): string {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}
