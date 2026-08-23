'use client';

import { Suspense, useMemo } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import TwinCanvas from '@/components/twin/TwinCanvas';
import MissionBar from '@/components/command/MissionBar';
import IncidentQueue from '@/components/command/IncidentQueue';
import FleetPanel from '@/components/command/FleetPanel';
import HospitalPanel from '@/components/command/HospitalPanel';
import DecisionLedger from '@/components/command/DecisionLedger';
import EntityInspector from '@/components/command/EntityInspector';
import TimelineShell from '@/components/command/TimelineShell';
import MetricsStrip from '@/components/command/MetricsStrip';
import { useCommandFeed } from '@/hooks/useCommandFeed';

/**
 * Command Center (Phase 10D).
 *
 * Zero-scroll mission control: the live twin is the instrument at center,
 * operational panels flank it, everything reads from real engine state.
 * No decorative motion — glow and color encode state, nothing else.
 */
export default function CommandPage() {
  return (
    <Suspense fallback={<main className="h-screen w-screen bg-void" />}>
      <CommandInner />
    </Suspense>
  );
}

function CommandInner() {
  const searchParams = useSearchParams();
  const runId = useMemo(() => {
    const explicit = searchParams.get('run');
    if (explicit) {
      try {
        window.localStorage.setItem('aureon:lastRun', explicit);
      } catch {}
      return explicit;
    }
    try {
      return window.localStorage.getItem('aureon:lastRun');
    } catch {
      return null;
    }
  }, [searchParams]);

  const feed = useCommandFeed(runId);
  const standby = !feed.liveState && feed.status !== 'ended';

  return (
    <main className="flex h-screen w-screen flex-col overflow-hidden bg-void">
      <MissionBar
        runId={runId}
        status={feed.status}
        progress={feed.progress}
        lastSuccessAt={feed.lastSuccessAt}
      />

      <div className="grid min-h-0 flex-1 grid-cols-[19rem_1fr_20rem] grid-rows-[minmax(0,1fr)_auto] gap-2 p-2">
        {/* Left rail */}
        <IncidentQueueColumn liveState={feed.liveState} />

        {/* Center instrument */}
        <CenterInstrument feed={feed} />

        {/* Right rail */}
        <RightRail liveState={feed.liveState} />

        {/* Timeline spans center+right under the rails */}
        <div className="col-span-2 col-start-2 min-h-0 rounded-lg border border-hairline bg-panel-1/80">
          <TimelineShell progress={feed.progress} />
        </div>
      </div>

      <footer className="h-16 shrink-0 border-t border-hairline bg-panel-1">
        <MetricsStrip progress={feed.progress} result={feed.result} />
      </footer>
    </main>
  );
}

function IncidentQueueColumn({ liveState }: { liveState: ReturnType<typeof useCommandFeed>['liveState'] }) {
  return (
    <div className="flex min-h-0 flex-col gap-2">
      <div className="min-h-0 flex-1">
        <IncidentQueue liveState={liveState} />
      </div>
      <div className="min-h-0 flex-[2]">
        <DecisionLedger />
      </div>
    </div>
  );
}

function CenterInstrument({
  feed,
}: {
  feed: ReturnType<typeof useCommandFeed>;
}) {
  const standby = !feed.liveState && feed.status !== 'ended';
  return (
    <div className="relative min-h-0 overflow-hidden rounded-lg border border-hairline">
      <TwinCanvas />
      {standby && (
        <div className="absolute inset-x-0 top-4 z-10 mx-auto w-fit rounded-md border border-hairline-strong bg-panel-1/90 px-5 py-3 text-center backdrop-blur">
          <p className="hud-stamp text-[var(--color-text-secondary)]">NO ACTIVE RUN</p>
          <Link
            href="/simulation"
            className="mt-2 inline-block rounded-md bg-teal-core px-4 py-1.5 text-xs font-semibold text-black hover:brightness-110 transition-all"
          >
            Launch a Simulation →
          </Link>
        </div>
      )}
      {feed.status === 'ended' && (
        <div className="pointer-events-none absolute inset-x-0 top-4 z-10 mx-auto w-fit">
          <span className="hud-stamp rounded-full border border-violet-intel/30 bg-panel-1/90 px-4 py-1.5 text-violet-intel backdrop-blur">
            RUN COMPLETE — OUTCOMES ARCHIVED
          </span>
        </div>
      )}
    </div>
  );
}

function RightRail({
  liveState,
}: {
  liveState: ReturnType<typeof useCommandFeed>['liveState'];
}) {
  return (
    <div className="flex min-h-0 flex-col gap-2">
      <div className="min-h-0 flex-1">
        <FleetPanel liveState={liveState} />
      </div>
      <div className="min-h-0 flex-1">
        <HospitalPanel liveState={liveState} />
      </div>
      <section className="flex h-44 shrink-0 flex-col rounded-lg border border-hairline bg-panel-1/80 backdrop-blur-sm">
        <header className="shrink-0 border-b border-hairline px-3 py-2">
          <h2 className="hud-label text-[var(--color-text-secondary)]">
            Entity Inspector
          </h2>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto">
          <EntityInspector />
        </div>
      </section>
    </div>
  );
}
