'use client';

import { useCallback, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import Navbar from '@/components/Navbar';
import MetricsPanel from '@/components/MetricsPanel';
import {
  runSimulation,
  getRunById,
  listScenarios,
  listDemos,
  launchDemo,
  type ScenarioInfo,
  type SimulationRunResult,
} from '@/lib/api';
import { useRunPolling } from '@/hooks/useRunPolling';

const formatTime = (seconds: number) => {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
};

export default function SimulationPage() {
  const router = useRouter();
  const [strategy, setStrategy] = useState('aureon');
  const [duration, setDuration] = useState(30);
  const [rate, setRate] = useState(12);
  const [seed, setSeed] = useState(42);
  const [scenario, setScenario] = useState('normal_operations');
  const [result, setResult] = useState<SimulationRunResult | null>(null);
  const [launchError, setLaunchError] = useState<string | null>(null);
  const [demoKey, setDemoKey] = useState<string | null>(null);

  const [runId, setRunId] = useState<string | null>(null);

  // Scenario Library registry — server-owned; the UI never hardcodes presets.
  const scenariosQuery = useQuery({
    queryKey: ['scenarios'],
    queryFn: listScenarios,
    staleTime: 5 * 60_000,
  });
  const scenarios: ScenarioInfo[] = scenariosQuery.data?.data ?? [];

  // Demo Library — curated deterministic showcase runs (Phase 10F-1).
  const demosQuery = useQuery({
    queryKey: ['demos'],
    queryFn: listDemos,
    staleTime: 5 * 60_000,
  });
  const demos = demosQuery.data?.data ?? [];

  const launchCuratedDemo = useCallback(
    async (key: string) => {
      setLaunchError(null);
      setDemoKey(key);
      try {
        const res = await launchDemo(key);
        // Hand the run to the Command Center with camera continuity.
        router.push(`/command?run=${res.data.run_id}&intro=1`);
      } catch (e: unknown) {
        setDemoKey(null);
        setLaunchError(e instanceof Error ? e.message : 'Demo launch failed');
      }
    },
    [router],
  );

  const handleCompleted = useCallback((id: string) => {
    getRunById(id)
      .then((res) => setResult(res.data))
      .catch(() => setResult(null));
  }, []);

  const { progress, error: pollError, isPolling, startPolling } =
    useRunPolling(handleCompleted);

  const isRunning =
    progress !== null &&
    (progress.status === 'queued' || progress.status === 'running');

  // Derived — no render-phase state writes.
  const failureReason =
    progress?.status === 'failed'
      ? progress.error || 'Simulation failed'
      : null;

  const handleRun = async () => {
    setLaunchError(null);
    setResult(null);
    setRunId(null);
    try {
      const res = await runSimulation({
        strategy,
        duration_minutes: duration,
        incident_rate_per_hour: rate,
        seed,
        scenario,
        // Stretch the run over wall time so the live twin has a window.
        wall_clock_factor: 60,
      });
      setRunId(res.data.run_id);
      try {
        window.localStorage.setItem('aureon:lastRun', res.data.run_id);
      } catch {}
      startPolling(res.data.run_id);
    } catch (e: unknown) {
      setLaunchError(e instanceof Error ? e.message : 'Unknown error');
    }
  };

  return (
    <>
      <Navbar />
      <main className="pt-28 px-6 max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Simulation</h1>

        {/* Demo Mode — one-click curated showcase runs */}
        {demos.length > 0 && (
          <div className="glass-panel rounded-2xl p-6 mb-6 border-teal-core/20">
            <div className="flex items-baseline justify-between gap-3 mb-1">
              <h2 className="text-lg font-semibold">Demo Mode</h2>
              <span className="hud-stamp !text-[9px] text-[var(--color-text-muted)]">
                DETERMINISTIC · REAL ENGINE · AUTO-PACED
              </span>
            </div>
            <p className="text-sm text-[var(--color-text-secondary)] mb-4">
              Fully scripted live missions — fixed seeds over the real
              simulation engine, paced for viewing. One click, no
              configuration.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {demos.map((d) => (
                <button
                  key={d.key}
                  onClick={() => launchCuratedDemo(d.key)}
                  disabled={demoKey !== null}
                  className={`rounded-xl border p-3.5 text-left transition-all duration-200 disabled:opacity-50 ${
                    demoKey === d.key
                      ? 'border-teal-core bg-teal-core/10'
                      : 'border-white/10 bg-white/5 hover:border-teal-core/50 hover:bg-teal-core/5'
                  }`}
                >
                  <p className="hud-stamp !text-[8px] text-[var(--color-text-secondary)] mb-1.5">
                    {d.run.scenario.replace(/_/g, ' ').toUpperCase()}
                  </p>
                  <p className="text-sm font-semibold mb-1">{d.name}</p>
                  <p className="text-[11px] text-[var(--color-text-secondary)] leading-snug mb-2">
                    {d.logline}
                  </p>
                  <p className="hud-stamp !text-[8px] text-[var(--color-text-muted)]">
                    {d.run.duration_minutes} MIN @ {d.run.wall_clock_factor}× ·{' '}
                    {d.run.strategy.toUpperCase()}
                  </p>
                </button>
              ))}
            </div>
            {demoKey && (
              <p className="mt-3 hud-stamp !text-[9px] text-teal-core">
                LAUNCHING {demoKey.toUpperCase().replace(/_/g, ' ')} — ENTERING COMMAND CENTER…
              </p>
            )}
          </div>
        )}

        {/* Launcher */}
        <div className="glass-panel rounded-2xl p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Run Simulation</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div>
              <label className="hud-label block text-[var(--color-text-muted)] mb-1">Strategy</label>
              <select
                value={strategy}
                onChange={(e) => setStrategy(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm"
              >
                <option value="aureon">Aureon (Hybrid)</option>
                <option value="baseline">Baseline (Nearest)</option>
                <option value="adaptive">Adaptive</option>
              </select>
            </div>
            <div>
              <label className="hud-label block text-[var(--color-text-muted)] mb-1">Duration (min)</label>
              <input
                type="number"
                value={duration}
                onChange={(e) => setDuration(Number(e.target.value))}
                min={5}
                max={120}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm font-mono tabular"
              />
            </div>
            <div>
              <label className="hud-label block text-[var(--color-text-muted)] mb-1">Incidents/hr</label>
              <input
                type="number"
                value={rate}
                onChange={(e) => setRate(Number(e.target.value))}
                min={1}
                max={30}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm font-mono tabular"
              />
            </div>
            <div>
              <label className="hud-label block text-[var(--color-text-muted)] mb-1">Seed</label>
              <input
                type="number"
                value={seed}
                onChange={(e) => setSeed(Number(e.target.value))}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm font-mono tabular"
              />
            </div>
          </div>

          {/* Scenario Library — world-state presets, server-owned registry */}
          <div className="mb-4">
            <label className="hud-label block text-[var(--color-text-muted)] mb-2">
              Scenario
            </label>
            {scenariosQuery.isLoading ? (
              <p className="hud-stamp text-[var(--color-text-muted)]">
                LOADING SCENARIOS…
              </p>
            ) : scenarios.length === 0 ? (
              <p className="hud-stamp text-[var(--color-text-muted)]">
                SCENARIO REGISTRY UNAVAILABLE — DEFAULTS APPLY
              </p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {scenarios.map((s) => {
                  const selected = scenario === s.key;
                  return (
                    <button
                      key={s.key}
                      onClick={() => setScenario(s.key)}
                      className={`rounded-xl border p-3 text-left transition-all duration-200 ${
                        selected
                          ? 'border-teal-core bg-teal-core/10'
                          : 'border-white/10 bg-white/5 hover:border-white/25'
                      }`}
                    >
                      <div className="flex items-baseline justify-between gap-2 mb-1">
                        <span className={`text-sm font-semibold ${selected ? 'text-teal-core' : ''}`}>
                          {s.name}
                        </span>
                        {selected && (
                          <span className="hud-stamp !text-[8px] text-teal-core">ACTIVE</span>
                        )}
                      </div>
                      <p className="text-xs text-[var(--color-text-secondary)] leading-snug mb-1.5">
                        {s.tagline}
                      </p>
                      <p className="text-[11px] text-[var(--color-text-muted)] leading-snug mb-2 line-clamp-3">
                        {s.description}
                      </p>
                      <span className="hud-stamp !text-[8px] rounded-sm border border-hairline-strong px-1.5 py-0.5 text-[var(--color-text-muted)]">
                        STRESS · {s.stress_vector.toUpperCase()}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <button
            onClick={handleRun}
            disabled={isRunning}
            className="px-6 py-2 rounded-lg bg-teal-core text-black font-semibold hover:brightness-110 hover:shadow-[0_0_20px_rgba(22,242,212,0.25)] transition-all duration-300 disabled:opacity-50"
          >
            {isRunning ? 'Running…' : 'Run Simulation'}
          </button>
          {launchError && (
            <p className="mt-3 text-sm text-crit-red">{launchError}</p>
          )}
          {isRunning && runId && (
            <>
              <Link
                href={`/twin?run=${runId}`}
                className="ml-4 inline-block px-5 py-2 rounded-lg border border-teal-core/40 text-sm font-medium text-teal-core hover:bg-teal-core/10 transition-colors"
              >
                Open Live Twin →
              </Link>
              <Link
                href={`/command?run=${runId}`}
                className="ml-2 inline-block px-5 py-2 rounded-lg border border-hairline-strong text-sm font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:border-white/20 transition-colors"
              >
                Command Center →
              </Link>
            </>
          )}
        </div>

        {/* Live progress */}
        {progress && isRunning && (
          <div className="glass-panel rounded-2xl p-6 mb-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="h-2 w-2 rounded-full bg-amber-warn animate-pulse" />
              <h2 className="text-lg font-semibold font-mono text-sm tracking-tight">
                {progress.status.toUpperCase()} — {progress.run_id}
              </h2>
            </div>

            <div className="mb-4">
              <div className="flex justify-between text-sm text-[var(--color-text-secondary)] mb-1">
                <span>Progress</span>
                <span className="font-mono tabular">{progress.progress_percent.toFixed(1)}%</span>
              </div>
              <div className="w-full bg-white/5 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-teal-core h-2 rounded-full transition-all duration-500"
                  style={{ width: `${progress.progress_percent}%` }}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <ProgressStat
                value={`${formatTime(progress.elapsed_seconds)} / ${formatTime(progress.duration_seconds)}`}
                label="Elapsed"
              />
              <ProgressStat value={String(progress.completed_incidents)} label="Completed" />
              <ProgressStat value={String(progress.reported_incidents)} label="Reported" />
              <ProgressStat
                value={`${progress.available_ambulances} / ${progress.available_ambulances + progress.active_ambulances}`}
                label="Fleet Available"
              />
            </div>
          </div>
        )}

        {(pollError || failureReason) && (
          <div className="glass-panel rounded-2xl p-6 mb-6 border border-crit-red/20">
            <div className="flex items-center gap-2 mb-2">
              <div className="h-2 w-2 rounded-full bg-crit-red" />
              <span className="text-sm font-medium text-crit-red">Simulation Failed</span>
            </div>
            <p className="text-sm text-[var(--color-text-secondary)]">{pollError ?? failureReason}</p>
          </div>
        )}

        {/* Results — typed nested metrics */}
        {result && (
          <>
            <MetricsPanel result={result} />
            <p className="hud-stamp text-[var(--color-text-muted)] -mt-3 mb-8">
              RUN AT {new Date(result.executed_at).toLocaleString()}
            </p>
          </>
        )}
      </main>
    </>
  );
}

function ProgressStat({ value, label }: { value: string; label: string }) {
  return (
    <div className="glass-panel rounded-xl p-3 text-center">
      <p className="font-mono tabular text-lg font-semibold">{value}</p>
      <p className="hud-label text-[var(--color-text-muted)] mt-0.5">{label}</p>
    </div>
  );
}
