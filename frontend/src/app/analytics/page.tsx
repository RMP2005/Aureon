'use client';

import { useEffect, useState } from 'react';
import Navbar from '@/components/Navbar';
import { listSimulationResults, type SimulationRunResult } from '@/lib/api';

export default function AnalyticsPage() {
  const [runs, setRuns] = useState<Array<{ run_id: string; type: string; executed_at: string }>>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listSimulationResults()
      .then((res) => setRuns(res.data))
      .catch((e) => setError(e.message));
  }, []);

  return (
    <>
      <Navbar />
      <main className="pt-28 px-6 max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Analytics</h1>

        <div className="glass-panel rounded-2xl p-6">
          <h2 className="text-lg font-semibold mb-4">Recent Simulation Runs</h2>
          {error && <p className="text-red-400 text-sm mb-4">{error}</p>}
          {runs.length === 0 ? (
            <p className="text-[var(--color-text-secondary)]">
              No simulation runs yet. Run a simulation from the{' '}
              <a href="/simulation" className="text-cyan-400 hover:underline">Simulation page</a>.
            </p>
          ) : (
            <div className="space-y-2">
              {runs.map((run) => (
                <div
                  key={run.run_id}
                  className="px-4 py-3 glass-panel rounded-xl flex items-center justify-between"
                >
                  <div>
                    <span className="font-medium text-sm">{run.run_id}</span>
                    <span className="ml-3 text-xs text-[var(--color-text-muted)] capitalize">{run.type}</span>
                  </div>
                  <span className="text-xs text-[var(--color-text-muted)]">
                    {run.executed_at ? new Date(run.executed_at).toLocaleString() : '—'}
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
