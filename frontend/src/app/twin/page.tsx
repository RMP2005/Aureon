'use client';

import { Suspense, useCallback, useState } from 'react';
import Link from 'next/link';
import { resetAllScrollers } from '@/components/brand/HomeLink';
import { useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import TwinCanvas from '@/components/twin/TwinCanvas';
import type { TwinPerfStats } from '@/components/twin/StatsProbe';
import {
  getRunLiveState,
  type RunLiveState,
} from '@/lib/api';
import { ingestLiveState, getLiveBuffer } from '@/lib/twin/live-buffer';
import { useTwinStore } from '@/lib/twin/store';

/**
 * Phase 10B twin host — deliberately bare.
 * Full-bleed scene + telemetry stamps. Command-center chrome arrives in 10D.
 */

function isNotFoundError(e: unknown): boolean {
  return e instanceof Error && e.message.includes('404');
}

function TwinPageInner() {
  const searchParams = useSearchParams();
  const runId = searchParams.get('run');
  const [perf, setPerf] = useState<TwinPerfStats | null>(null);
  const [liveEnded, setLiveEnded] = useState(false);
  const selection = useTwinStore((s) => s.selection);

  const onStats = useCallback((s: TwinPerfStats) => setPerf(s), []);

  useQuery({
    queryKey: ['twin-live', runId],
    enabled: runId !== null && !liveEnded,
    queryFn: async (): Promise<RunLiveState | null> => {
      try {
        const res = await getRunLiveState(runId as string);
        ingestLiveState(res.data);
        return res.data;
      } catch (e) {
        if (isNotFoundError(e)) {
          setLiveEnded(true);
          return null;
        }
        throw e;
      }
    },
    refetchInterval: 1_000,
    retry: false,
    staleTime: 0,
  });

  const buffer = getLiveBuffer();
  const selectedAmbulance =
    selection?.kind === 'ambulance'
      ? buffer.ambulances.get(selection.id)
      : undefined;

  return (
    <main className="relative h-screen w-screen overflow-hidden bg-void">
      {/* Scene */}
      <div className="absolute inset-0">
        <TwinCanvas onStats={onStats} />
      </div>

      {/* HUD — top-left identity + live clock */}
      <div className="pointer-events-none absolute left-5 top-5 select-none">
        <p className="font-display text-lg font-semibold tracking-tight">
          Aureon <span className="text-teal-core">/</span> Bengaluru Twin
        </p>
        <p className="hud-stamp mt-1 text-[var(--color-text-muted)]">
          {runId
            ? `RUN ${runId.slice(0, 8)} · ${buffer.strategy.toUpperCase()} · T+${buffer.simTimeFormatted}`
            : 'STATIC CITY SKELETON · NO LIVE RUN'}
        </p>
        {runId && (
          <p className="hud-stamp mt-0.5 text-[var(--color-text-muted)]">
            TICK {buffer.tick} · FLEET {buffer.fleetAvailable}/{buffer.fleetTotal} AVAIL · ACTIVE{' '}
            {buffer.incidents.length} · QUEUE {buffer.pendingQueue}
          </p>
        )}
      </div>

      {/* HUD — bottom-left perf baseline */}
      <div className="pointer-events-none absolute bottom-5 left-5 select-none">
        <p className="hud-stamp text-[var(--color-text-muted)]">
          {perf
            ? `${perf.fps} FPS · ${perf.drawCalls} CALLS · ${(perf.triangles / 1000).toFixed(0)}K TRIS`
            : 'SAMPLING…'}
        </p>
      </div>

      {/* HUD — bottom-right selection readout */}
      <div className="pointer-events-none absolute bottom-5 right-5 max-w-xs select-none text-right">
        {selectedAmbulance ? (
          <>
            <p className="hud-label text-teal-core">{selectedAmbulance.callsign}</p>
            <p className="hud-stamp mt-0.5 text-[var(--color-text-secondary)]">
              {selectedAmbulance.status.replace(/_/g, ' ').toUpperCase()} · CAP{' '}
              {selectedAmbulance.capability.slice(0, 3).toUpperCase()} · MISSIONS{' '}
              {selectedAmbulance.missionsCompleted}
            </p>
          </>
        ) : selection?.kind === 'hospital' ? (
          <p className="hud-label text-titanium">HOSPITAL {selection.id}</p>
        ) : null}
      </div>

      {liveEnded && (
        <div className="pointer-events-none absolute inset-x-0 top-20 flex justify-center">
          <p className="hud-stamp rounded-full border border-hairline bg-panel-1 px-4 py-1.5 text-[var(--color-text-secondary)]">
            RUN ENDED — SNAPSHOT ARCHIVED
          </p>
        </div>
      )}

      {/* Way back — temporary scaffolding until command center (10D) */}
      <Link
        href="/"
        onClick={resetAllScrollers}
        className="absolute right-5 top-5 hud-stamp text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
      >
        ← EXIT TWIN
      </Link>
    </main>
  );
}

export default function TwinPage() {
  return (
    <Suspense fallback={<main className="h-screen w-screen bg-void" />}>
      <TwinPageInner />
    </Suspense>
  );
}
