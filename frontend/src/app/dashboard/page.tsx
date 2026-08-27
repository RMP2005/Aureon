'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Navbar from '@/components/Navbar';
import {
  getHealth,
  listSimulationResults,
  type HealthData,
  type RunSummary,
} from '@/lib/api';

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getHealth(), listSimulationResults()])
      .then(([healthRes, runsRes]) => {
        setHealth(healthRes.data);
        setRuns(runsRes.data);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const completedRuns = runs.filter((r) => r.status === 'completed');
  const failedRuns = runs.filter((r) => r.status === 'failed');

  return (
    <>
      <Navbar />
      <main className="pt-6 px-6 max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Dashboard</h1>

        {error && (
          <div className="glass-panel rounded-2xl p-6 mb-6 border border-red-500/20">
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}

        {/* Backend Health */}
        <div className="glass-panel rounded-2xl p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Backend Health</h2>
          {loading ? (
            <p className="text-[var(--color-text-secondary)] text-sm">Loading...</p>
          ) : health ? (
            <div className="grid grid-cols-3 gap-4">
              <div className="glass-panel rounded-xl p-4 text-center">
                <p className="text-2xl font-semibold">{health.status}</p>
                <p className="text-xs text-[var(--color-text-muted)] uppercase">Status</p>
              </div>
              <div className="glass-panel rounded-xl p-4 text-center">
                <p className="text-2xl font-semibold">{health.service}</p>
                <p className="text-xs text-[var(--color-text-muted)] uppercase">Service</p>
              </div>
              <div className="glass-panel rounded-xl p-4 text-center">
                <p className="text-2xl font-semibold">{health.version}</p>
                <p className="text-xs text-[var(--color-text-muted)] uppercase">Version</p>
              </div>
            </div>
          ) : (
            <p className="text-red-400 text-sm">Could not reach backend</p>
          )}
        </div>

        {/* Simulation Summary */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          <div className="glass-panel rounded-2xl p-6 text-center">
            <p className="text-3xl font-bold">{runs.length}</p>
            <p className="text-xs text-[var(--color-text-muted)] uppercase mt-1">Total Runs</p>
          </div>
          <div className="glass-panel rounded-2xl p-6 text-center">
            <p className="text-3xl font-bold text-emerald-400">{completedRuns.length}</p>
            <p className="text-xs text-[var(--color-text-muted)] uppercase mt-1">Completed</p>
          </div>
          <div className="glass-panel rounded-2xl p-6 text-center">
            <p className="text-3xl font-bold text-red-400">{failedRuns.length}</p>
            <p className="text-xs text-[var(--color-text-muted)] uppercase mt-1">Failed</p>
          </div>
        </div>

        {/* Recent Runs */}
        <div className="glass-panel rounded-2xl p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Recent Runs</h2>
            <Link
              href="/analytics"
              className="text-sm text-cyan-400 hover:underline"
            >
              View all
            </Link>
          </div>
          {runs.length === 0 ? (
            <p className="text-[var(--color-text-secondary)] text-sm">
              No runs yet.{' '}
              <Link href="/simulation" className="text-cyan-400 hover:underline">
                Run a simulation
              </Link>
              .
            </p>
          ) : (
            <div className="space-y-2">
              {runs.slice(0, 5).map((run) => (
                <div
                  key={run.run_id}
                  className="px-4 py-3 glass-panel rounded-xl flex items-center justify-between"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`h-2 w-2 rounded-full ${
                        run.status === 'completed'
                          ? 'bg-emerald-400'
                          : run.status === 'failed'
                            ? 'bg-red-400'
                            : 'bg-amber-400'
                      }`}
                    />
                  <div>
                    <span className="font-medium text-sm">{run.run_id}</span>
                    <span className="ml-3 text-xs text-[var(--color-text-muted)]">
                      {run.type}
                    </span>
                    {run.strategy && (
                      <span className="ml-2 text-xs text-[var(--color-text-muted)]">
                        {run.strategy}
                      </span>
                    )}
                  </div>
                  </div>
                  <span className="text-xs text-[var(--color-text-muted)]">
                    {run.executed_at
                      ? new Date(run.executed_at).toLocaleString()
                      : '—'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </>
  );
}
