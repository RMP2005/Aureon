'use client';

import { Suspense, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useSearchParams } from 'next/navigation';
import TwinCanvas from '@/components/twin/TwinCanvas';
import MissionBar from '@/components/command/MissionBar';
import IncidentQueue from '@/components/command/IncidentQueue';
import FleetPanel from '@/components/command/FleetPanel';
import HospitalPanel from '@/components/command/HospitalPanel';
import DecisionLedger from '@/components/command/DecisionLedger';
import EntityInspector from '@/components/command/EntityInspector';
import MissionDebrief from '@/components/command/MissionDebrief';
import TimelineShell from '@/components/command/TimelineShell';
import MetricsStrip from '@/components/command/MetricsStrip';
import { useCommandFeed } from '@/hooks/useCommandFeed';
import { useReplayStore } from '@/lib/twin/replay';
import { useSessionStore } from '@/lib/twin/store';
import { requestIntroSweep } from '@/lib/twin/intro';
import BootOverlay from '@/components/command/BootOverlay';
import Hl from '@/components/brand/Hl';
import { launchDemo } from '@/lib/api';

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

  // Landing handoff (Phase 10F-1): arriving with ?intro=1 arms the camera
  // sweep before the twin mounts, so the descent reads as one gesture.
  const [introArrival, setIntroArrival] = useState(false);
  useEffect(() => {
    if (searchParams.get('intro') === '1') {
      requestIntroSweep();
      setIntroArrival(true);
    }
  }, [searchParams]);

  const feed = useCommandFeed(runId);

  const replayStatus = useReplayStore((s) => s.status);
  const replayFrame = useReplayStore((s) => s.currentFrame);
  const replayRecording = useReplayStore((s) => s.recording);
  const playheadSec = useReplayStore((s) => s.playheadSec);
  const loadRecording = useReplayStore((s) => s.loadRecording);
  const stopReplay = useReplayStore((s) => s.stop);
  const inReplay = replayStatus === 'ready' || replayStatus === 'playing';

  // Switching runs always tears down any active replay session.
  useEffect(() => {
    stopReplay();
  }, [runId, stopReplay]);

  // Panels read the replay frame while scrubbing — identical RunLiveState
  // shape as live telemetry, so no panel knows which source it renders.
  const panelState = inReplay ? replayFrame : feed.liveState;

  // Persisted decision evidence, indexed by incident (Phase 10F-1) — powers
  // "Explain This Decision" for completed incidents after run completion.
  const dispatchIndex = useMemo(() => {
    const log = feed.result?.dispatch_log_sample ?? [];
    if (log.length === 0) return null;
    return new Map(log.map((e) => [e.incident_id, e]));
  }, [feed.result]);

  return (
    <main className="flex h-screen w-screen flex-col overflow-hidden bg-void">
      <MissionBar
        runId={runId}
        status={feed.status}
        progress={feed.progress}
        lastSuccessAt={feed.lastSuccessAt}
        scenarioName={feed.result?.scenario?.name ?? null}
        replay={
          inReplay
            ? {
                playheadSec,
                durationSec: replayRecording?.duration_seconds ?? 0,
                playing: replayStatus === 'playing',
              }
            : null
        }
      />

      <div className="grid min-h-0 flex-1 grid-cols-[19rem_1fr_20rem] grid-rows-[minmax(0,1fr)_auto] gap-2 p-2">
        {/* Left rail — debrief chapters take over during replay */}
        <IncidentQueueColumn
          liveState={panelState}
          inReplay={inReplay}
          replayRecording={replayRecording}
        />

        {/* Center instrument */}
        <CenterInstrument
          feed={feed}
          inReplay={inReplay}
          replayStatus={replayStatus}
          onLoadReplay={() => runId && loadRecording(runId)}
          onExitReplay={stopReplay}
          showBoot={introArrival}
        />

        {/* Right rail */}
        <RightRail liveState={panelState} dispatchIndex={dispatchIndex} />

        {/* Timeline spans center+right under the rails */}
        <div className="col-span-2 col-start-2 min-h-0 rounded-lg border border-hairline bg-panel-1/80">
          <TimelineShell
            mode={inReplay ? 'replay' : 'live'}
            progress={feed.progress}
          />
        </div>
      </div>

      <footer className="h-16 shrink-0 border-t border-hairline bg-panel-1">
        <MetricsStrip
          progress={feed.progress}
          result={feed.result}
          liveModeStats={panelState?.mode_stats ?? null}
        />
      </footer>
    </main>
  );
}

function IncidentQueueColumn({
  liveState,
  inReplay,
  replayRecording,
}: {
  liveState: ReturnType<typeof useCommandFeed>['liveState'];
  inReplay: boolean;
  replayRecording: ReturnType<typeof useReplayStore.getState>['recording'];
}) {
  return (
    <div className="flex min-h-0 flex-col gap-2">
      <div className="min-h-0 flex-1">
        {inReplay ? (
          <MissionDebrief recording={replayRecording} />
        ) : (
          <IncidentQueue liveState={liveState} />
        )}
      </div>
      <div className="min-h-0 flex-[2]">
        <DecisionLedger />
      </div>
    </div>
  );
}

function CenterInstrument({
  feed,
  inReplay,
  replayStatus,
  onLoadReplay,
  onExitReplay,
  showBoot,
}: {
  feed: ReturnType<typeof useCommandFeed>;
  inReplay: boolean;
  replayStatus: ReturnType<typeof useReplayStore.getState>['status'];
  onLoadReplay: () => void;
  onExitReplay: () => void;
  showBoot: boolean;
}) {
  const replayError = useReplayStore((s) => s.error);
  const router = useRouter();
  const [demoLaunching, setDemoLaunching] = useState(false);
  const standby = !feed.liveState && !inReplay && feed.status !== 'ended';

  // One-click showcase from standby (Phase 10F-1): flagship demo, no config.
  const startShowcase = async () => {
    setDemoLaunching(true);
    try {
      const res = await launchDemo(null); // server resolves its flagship
      useSessionStore
        .getState()
        .setDemo({ ...res.data.demo, runId: res.data.run_id });
      router.replace(`/command?run=${res.data.run_id}`);
    } catch {
      setDemoLaunching(false);
    }
  };

  return (
    <div className="relative min-h-0 overflow-hidden rounded-lg border border-hairline">
      <TwinCanvas />

      {/* Landing → operations boot (Phase 11-refinement, ≤2s entry) */}
      {showBoot && <BootOverlay />}

      {/* Replay session controls */}
      {inReplay && (
        <div className="absolute left-3 top-3 z-10">
          <button
            onClick={onExitReplay}
            className="hud-stamp rounded-md border border-violet-intel/40 bg-panel-1/90 px-3 py-1.5 text-violet-intel backdrop-blur transition-colors hover:bg-violet-intel/10"
          >
            EXIT REPLAY ✕
          </button>
        </div>
      )}

      {standby && (
        <div className="absolute inset-x-0 top-4 z-10 mx-auto w-fit max-w-xl rounded-md border border-hairline-strong bg-panel-1/90 px-5 py-3 text-center backdrop-blur">
          <p className="hud-stamp text-[var(--color-text-secondary)]">NO ACTIVE RUN</p>
          <p className="mt-1.5 text-xs leading-relaxed text-[var(--color-text-muted)]">
            Launch a curated showcase — a city{' '}
            <Hl kind="crit">crisis</Hl> unfolds live while Aureon{' '}
            <Hl kind="reason">decides</Hl> autonomously. Every decision is
            logged with explainable <Hl kind="evidence">evidence</Hl>.
          </p>
          <div className="mt-2 flex items-center justify-center gap-2">
            <button
              onClick={startShowcase}
              disabled={demoLaunching}
              className="inline-block rounded-md bg-teal-core px-4 py-1.5 text-xs font-semibold text-black hover:brightness-110 transition-all disabled:opacity-50"
            >
              {demoLaunching ? 'LAUNCHING DEMO…' : '▶ START SHOWCASE DEMO'}
            </button>
            <Link
              href="/simulation"
              className="inline-block rounded-md border border-hairline-strong px-4 py-1.5 text-xs font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:border-white/20 transition-colors"
            >
              Configure a Run →
            </Link>
          </div>
        </div>
      )}

      {feed.status === 'ended' && !inReplay && (
        <div className="absolute inset-x-0 top-4 z-10 mx-auto w-fit rounded-md border border-hairline-strong bg-panel-1/90 px-5 py-3 text-center backdrop-blur">
          <p className="hud-stamp text-[var(--color-text-secondary)]">RUN COMPLETE — OUTCOMES ARCHIVED</p>
          <button
            onClick={onLoadReplay}
            disabled={replayStatus === 'loading'}
            className="mt-2 inline-block rounded-md bg-teal-core px-4 py-1.5 text-xs font-semibold text-black transition-all hover:brightness-110 disabled:opacity-50"
          >
            {replayStatus === 'loading' ? 'LOADING RECORDING…' : '▶ EVIDENCE REPLAY'}
          </button>
          {replayError && (
            <p className="mt-1.5 hud-stamp !text-[9px] text-crit-red">{replayError}</p>
          )}
        </div>
      )}
    </div>
  );
}

function RightRail({
  liveState,
  dispatchIndex,
}: {
  liveState: ReturnType<typeof useCommandFeed>['liveState'];
  dispatchIndex: Map<string, import('@/lib/api').DispatchLogEntry> | null;
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
          <EntityInspector dispatchIndex={dispatchIndex} />
        </div>
      </section>
    </div>
  );
}
