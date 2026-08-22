'use client';

import { useEffect, useState } from 'react';
import Navbar from '@/components/Navbar';
import { getHealth, type HealthData } from '@/lib/api';

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getHealth()
      .then((res) => setHealth(res.data))
      .catch((e) => setError(e.message));
  }, []);

  return (
    <>
      <Navbar />
      <main className="pt-28 px-6 max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Dashboard</h1>

        <div className="glass-panel rounded-2xl p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Backend Health</h2>
          {error && <p className="text-red-400 text-sm">{error}</p>}
          {health ? (
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
            <p className="text-[var(--color-text-secondary)]">Loading...</p>
          )}
        </div>
      </main>
    </>
  );
}
