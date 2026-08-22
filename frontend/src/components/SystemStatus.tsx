'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { getHealth, type HealthData } from '@/lib/api';

const statusColors: Record<string, string> = {
  online: 'bg-emerald-400',
  healthy: 'bg-emerald-400',
  standby: 'bg-amber-400',
  offline: 'bg-red-400',
  error: 'bg-red-400',
};

const subsystems = [
  { name: 'Simulation Engine', version: 'v0.1.0', checkHealth: true },
  { name: 'ML Pipeline', version: 'v0.1.0', checkHealth: false },
  { name: 'Event Classifier', version: 'v0.1.0', checkHealth: false },
  { name: 'Prediction Engine', version: 'v0.1.0', checkHealth: false },
  { name: 'Optimizer', version: 'v0.1.0', checkHealth: false },
  { name: 'Data Pipeline', version: 'v0.1.0', checkHealth: false },
];

export default function SystemStatus() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    getHealth()
      .then((res) => setHealth(res.data))
      .catch(() => setError(true));
  }, []);

  const getStatus = (checkHealth: boolean): string => {
    if (checkHealth && health) return health.status;
    if (checkHealth && error) return 'offline';
    return 'standby';
  };

  return (
    <section className="relative px-6 py-24">
      <div className="max-w-4xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-100px' }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12"
        >
          <h2 className="text-3xl md:text-4xl font-bold mb-4">System Status</h2>
          <p className="text-[var(--color-text-secondary)]">
            Real-time monitoring of all Aureon subsystems.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-50px' }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="glass-panel rounded-2xl overflow-hidden"
        >
          <div className="px-6 py-4 border-b border-white/5 flex items-center justify-between">
            <span className="text-sm font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Subsystem</span>
            <span className="text-sm font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">Status</span>
          </div>
          {subsystems.map((system, index) => {
            const status = getStatus(system.checkHealth);
            return (
              <motion.div
                key={system.name}
                initial={{ opacity: 0, x: -10 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.3, delay: 0.1 * index }}
                className="px-6 py-4 flex items-center justify-between border-b border-white/5 last:border-b-0 hover:bg-white/[0.02] transition-colors"
              >
                <div className="flex items-center gap-4">
                  <span className="text-sm font-medium">{system.name}</span>
                  <span className="text-xs text-[var(--color-text-muted)]">{system.version}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className={`h-2 w-2 rounded-full ${statusColors[status] ?? 'bg-amber-400'}`} />
                  <span className="text-xs text-[var(--color-text-secondary)] capitalize">{status}</span>
                </div>
              </motion.div>
            );
          })}
        </motion.div>
      </div>
    </section>
  );
}
