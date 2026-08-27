'use client';

import Navbar from '@/components/Navbar';

const models = [
  { id: 'hybrid-dispatch', name: 'Hybrid Dispatch Strategy', status: 'active', type: 'Dispatch' },
  { id: 'adaptive-policy', name: 'Adaptive Policy Engine', status: 'available', type: 'Dispatch' },
  { id: 'demand-forecast', name: 'Demand Forecast (XGBoost)', status: 'not_served', type: 'ML' },
  { id: 'event-classifier', name: 'Event Classifier', status: 'not_loaded', type: 'ML' },
];

const statusColors: Record<string, string> = {
  active: 'bg-emerald-400',
  available: 'bg-cyan-400',
  not_served: 'bg-amber-400',
  not_loaded: 'bg-red-400',
};

const statusLabels: Record<string, string> = {
  active: 'Active',
  available: 'Available',
  not_served: 'Not Served',
  not_loaded: 'Not Loaded',
};

export default function ModelsPage() {
  return (
    <>
      <Navbar />
      <main className="pt-6 px-6 max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-8">Models</h1>

        <div className="glass-panel rounded-2xl p-6">
          <h2 className="text-lg font-semibold mb-4">Available Models</h2>
          <p className="text-sm text-[var(--color-text-secondary)] mb-6">
            Dispatch strategies are served through the simulation API. ML models exist in the
            simulation engine but are not yet exposed as standalone inference endpoints.
          </p>
          <div className="space-y-2">
            {models.map((model) => (
              <div
                key={model.id}
                className="px-4 py-3 glass-panel rounded-xl flex items-center justify-between"
              >
                <div>
                  <span className="font-medium text-sm">{model.name}</span>
                  <span className="ml-3 text-xs text-[var(--color-text-muted)]">{model.type}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className={`h-2 w-2 rounded-full ${statusColors[model.status]}`} />
                  <span className="text-xs text-[var(--color-text-secondary)]">{statusLabels[model.status]}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </>
  );
}
