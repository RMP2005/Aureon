'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Navbar from '@/components/Navbar';
import { listSimulationResults, type RunSummary } from '@/lib/api';

export default function AnalyticsPage() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listSimulationResults()
      .then((res) => setRuns(res.data))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const completedRuns = runs.filter((r) => r.status === 'completed');
  const failedRuns = runs.filter((r) => r.status === 'failed');

  return (
    <>
      <Navbar />
      <main className="pt-6 px-6 max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Analytics</h1>

        {/* Summary cards */}
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

        {/* Run list */}
        <div className="glass-panel rounded-2xl p-6">
          <h2 className="text-lg font-semibold mb-4">All Simulation Runs</h2>

          {error && (
            <div className="glass-panel rounded-xl p-4 mb-4 border border-red-500/20">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}

          {loading ? (
            <p className="text-[var(--color-text-secondary)] text-sm">Loading runs...</p>
          ) : runs.length === 0 ? (
            <p className="text-[var(--color-text-secondary)] text-sm">
              No simulation runs yet.{' '}
              <Link href="/simulation" className="text-cyan-400 hover:underline">
                Run a simulation
              </Link>
              .
            </p>
          ) : (
            <div className="space-y-2">
              {runs.map((run) => (
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
                      <span className="ml-3 text-xs text-[var(--color-text-muted)] capitalize">
                        {run.type}
                      </span>
                      {run.strategy && (
                        <span className="ml-2 text-xs text-[var(--color-text-muted)]">
                          {run.strategy}
                        </span>
                      )}
                      <span
                        className={`ml-2 text-xs capitalize ${
                          run.status === 'completed'
                            ? 'text-emerald-400'
                            : run.status === 'failed'
                              ? 'text-red-400'
                              : 'text-amber-400'
                        }`}
                      >
                        {run.status}
                      </span>
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
