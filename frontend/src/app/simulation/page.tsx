'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import Navbar from '@/components/Navbar';
import {
  runSimulation,
  getRunStatus,
  getRunById,
  type SimulationRunResult,
  type RunProgress,
} from '@/lib/api';

export default function SimulationPage() {
  const [strategy, setStrategy] = useState('aureon');
  const [duration, setDuration] = useState(30);
  const [rate, setRate] = useState(12);
  const [seed, setSeed] = useState(42);
  const [progress, setProgress] = useState<RunProgress | null>(null);
  const [result, setResult] = useState<SimulationRunResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clearPolling = useCallback(() => {
    if (timerRef.current !== null) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => clearPolling();
  }, [clearPolling]);

  const handleRun = async () => {
    clearPolling();
    setError(null);
    setResult(null);
    setProgress({ run_id: '', status: 'queued', progress_percent: 0, elapsed_seconds: 0, duration_seconds: 0, completed_incidents: 0, reported_incidents: 0, active_ambulances: 0, available_ambulances: 0, error: null });

    try {
      const res = await runSimulation({
        strategy,
        duration_minutes: duration,
        incident_rate_per_hour: rate,
        seed,
      });
      const runId = res.data.run_id;
      setProgress((prev) => prev ? { ...prev, run_id: runId, status: 'queued' } : null);

      timerRef.current = setInterval(async () => {
        try {
          const statusRes = await getRunStatus(runId);
          const p = statusRes.data;
          setProgress(p);

          if (p.status === 'completed') {
            clearPolling();
            const resultRes = await getRunById(runId);
            setResult(resultRes.data);
            setProgress(null);
          } else if (p.status === 'failed') {
            clearPolling();
            setError(p.error || 'Simulation failed');
            setProgress(null);
          }
        } catch {
          clearPolling();
          setError('Failed to fetch simulation status');
          setProgress(null);
        }
      }, 1000);
    } catch (e: unknown) {
      clearPolling();
      setError(e instanceof Error ? e.message : 'Unknown error');
      setProgress(null);
    }
  };

  const isRunning = progress !== null && (progress.status === 'queued' || progress.status === 'running');
  const metricEntries = result ? Object.entries(result.metrics) : [];

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <>
      <Navbar />
      <main className="pt-28 px-6 max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Simulation</h1>

        <div className="glass-panel rounded-2xl p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Run Simulation</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div>
              <label className="block text-xs text-[var(--color-text-muted)] mb-1 uppercase">Strategy</label>
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
              <label className="block text-xs text-[var(--color-text-muted)] mb-1 uppercase">Duration (min)</label>
              <input
                type="number"
                value={duration}
                onChange={(e) => setDuration(Number(e.target.value))}
                min={5}
                max={120}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-[var(--color-text-muted)] mb-1 uppercase">Incidents/hr</label>
              <input
                type="number"
                value={rate}
                onChange={(e) => setRate(Number(e.target.value))}
                min={1}
                max={30}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-[var(--color-text-muted)] mb-1 uppercase">Seed</label>
              <input
                type="number"
                value={seed}
                onChange={(e) => setSeed(Number(e.target.value))}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm"
              />
            </div>
          </div>
          <button
            onClick={handleRun}
            disabled={isRunning}
            className="px-6 py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-medium hover:shadow-lg hover:shadow-cyan-500/25 transition-all duration-300 disabled:opacity-50"
          >
            {isRunning ? 'Running...' : 'Run Simulation'}
          </button>
        </div>

        {progress && isRunning && (
          <div className="glass-panel rounded-2xl p-6 mb-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
              <h2 className="text-lg font-semibold">
                {progress.status === 'queued' ? 'Queued' : 'Running'} — {progress.run_id}
              </h2>
            </div>

            <div className="mb-4">
              <div className="flex justify-between text-sm text-[var(--color-text-secondary)] mb-1">
                <span>Progress</span>
                <span>{progress.progress_percent.toFixed(1)}%</span>
              </div>
              <div className="w-full bg-white/5 rounded-full h-2">
                <div
                  className="bg-gradient-to-r from-cyan-500 to-blue-600 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${progress.progress_percent}%` }}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div className="glass-panel rounded-xl p-3 text-center">
                <p className="text-lg font-semibold">{formatTime(progress.elapsed_seconds)} / {formatTime(progress.duration_seconds)}</p>
                <p className="text-xs text-[var(--color-text-muted)] uppercase">Elapsed</p>
              </div>
              <div className="glass-panel rounded-xl p-3 text-center">
                <p className="text-lg font-semibold">{progress.completed_incidents}</p>
                <p className="text-xs text-[var(--color-text-muted)] uppercase">Completed</p>
              </div>
              <div className="glass-panel rounded-xl p-3 text-center">
                <p className="text-lg font-semibold">{progress.reported_incidents}</p>
                <p className="text-xs text-[var(--color-text-muted)] uppercase">Reported</p>
              </div>
              <div className="glass-panel rounded-xl p-3 text-center">
                <p className="text-lg font-semibold">{progress.available_ambulances} / {progress.available_ambulances + progress.active_ambulances}</p>
                <p className="text-xs text-[var(--color-text-muted)] uppercase">Fleet Available</p>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="glass-panel rounded-2xl p-6 mb-6 border border-red-500/20">
            <div className="flex items-center gap-2 mb-2">
              <div className="h-2 w-2 rounded-full bg-red-400" />
              <span className="text-sm font-medium text-red-400">Simulation Failed</span>
            </div>
            <p className="text-sm text-[var(--color-text-secondary)]">{error}</p>
          </div>
        )}

        {result && (
          <div className="glass-panel rounded-2xl p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="h-2 w-2 rounded-full bg-emerald-400" />
              <h2 className="text-lg font-semibold">Results — {result.run_id}</h2>
            </div>
            <div className="flex flex-wrap gap-3 mb-4 text-sm text-[var(--color-text-secondary)]">
              <span>Strategy: <strong>{result.strategy}</strong></span>
              <span>Duration: <strong>{result.parameters.duration_minutes}</strong> min</span>
              <span>Rate: <strong>{result.parameters.incident_rate_per_hour}</strong>/hr</span>
              <span>Seed: <strong>{result.parameters.seed}</strong></span>
              {result.executed_at && (
                <span>Run at: <strong>{new Date(result.executed_at).toLocaleString()}</strong></span>
              )}
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {metricEntries.map(([key, value]) => (
                <div key={key} className="glass-panel rounded-xl p-4 text-center">
                  <p className="text-xl font-semibold">
                    {typeof value === 'number' ? value.toFixed(1) : String(value)}
                  </p>
                  <p className="text-xs text-[var(--color-text-muted)] uppercase">
                    {key.replace(/_/g, ' ')}
                  </p>
                </div>
              ))}
            </div>
            {metricEntries.length === 0 && (
              <p className="text-sm text-[var(--color-text-muted)]">No metrics returned.</p>
            )}
          </div>
        )}
      </main>
    </>
  );
}
