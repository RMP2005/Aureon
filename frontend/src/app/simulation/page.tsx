'use client';

import { useState } from 'react';
import Navbar from '@/components/Navbar';
import { runSimulation, type SimulationRunResult } from '@/lib/api';

export default function SimulationPage() {
  const [strategy, setStrategy] = useState('aureon');
  const [duration, setDuration] = useState(30);
  const [rate, setRate] = useState(12);
  const [seed, setSeed] = useState(42);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SimulationRunResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await runSimulation({
        strategy,
        duration_minutes: duration,
        incident_rate_per_hour: rate,
        seed,
      });
      setResult(res.data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
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
            disabled={loading}
            className="px-6 py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-medium hover:shadow-lg hover:shadow-cyan-500/25 transition-all duration-300 disabled:opacity-50"
          >
            {loading ? 'Running...' : 'Run Simulation'}
          </button>
        </div>

        {error && (
          <div className="glass-panel rounded-2xl p-6 mb-6 border border-red-500/20">
            <p className="text-red-400">{error}</p>
          </div>
        )}

        {result && (
          <div className="glass-panel rounded-2xl p-6">
            <h2 className="text-lg font-semibold mb-4">Results — {result.run_id}</h2>
            <p className="text-sm text-[var(--color-text-secondary)] mb-4">
              Strategy: {result.strategy} | Seed: {result.parameters.seed}
            </p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(result.metrics).slice(0, 8).map(([key, value]) => (
                <div key={key} className="glass-panel rounded-xl p-4 text-center">
                  <p className="text-xl font-semibold">{typeof value === 'number' ? value.toFixed(1) : String(value)}</p>
                  <p className="text-xs text-[var(--color-text-muted)] uppercase">{key.replace(/_/g, ' ')}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </>
  );
}
