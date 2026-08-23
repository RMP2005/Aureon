'use client';

import type { RunLiveState } from '@/lib/api';
import { useTwinStore } from '@/lib/twin/store';
import { EmptyNote, PanelFrame, StatusChip } from './primitives';

const SEVERITY_ORDER: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

/**
 * Incident queue (Phase 10D) — live active incidents, worst first.
 * Rows select the incident in the scene (ring + camera focus).
 */
export default function IncidentQueue({
  liveState,
}: {
  liveState: RunLiveState | null;
}) {
  const incidents = [...(liveState?.active_incidents ?? [])].sort(
    (a, b) =>
      (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9),
  );
  const callsignById = new Map(
    (liveState?.ambulances ?? []).map((a) => [a.id, a.callsign]),
  );
  const selection = useTwinStore((s) => s.selection);
  const select = useTwinStore((s) => s.select);

  return (
    <PanelFrame
      title="Incident Queue"
      right={
        <span className="tnum font-mono text-[10px] text-[var(--color-text-muted)]">
          {incidents.length} ACTIVE
        </span>
      }
    >
      {incidents.length === 0 ? (
        <EmptyNote>No active incidents.</EmptyNote>
      ) : (
        <ul className="divide-y divide-[color:var(--color-hairline)]">
          {incidents.map((inc) => {
            const selected =
              selection?.kind === 'incident' && selection.id === inc.id;
            return (
              <li key={inc.id}>
                <button
                  onClick={() => select({ kind: 'incident', id: inc.id })}
                  className={`w-full px-3 py-2.5 text-left transition-colors hover:bg-white/[0.03] ${
                    selected ? 'bg-crit-red/5 border-l-2 border-l-crit-red' : ''
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <StatusChip value={inc.severity} />
                    <span className="truncate text-xs font-medium">
                      {inc.category.replace(/_/g, ' ')}
                    </span>
                    <span className="ml-auto shrink-0 font-mono text-[10px] text-[var(--color-text-muted)]">
                      {inc.required_capability.toUpperCase()}
                    </span>
                  </div>
                  <div className="mt-1 flex items-baseline justify-between gap-2">
                    <span className="truncate text-[11px] text-[var(--color-text-secondary)]">
                      {inc.location_name}
                    </span>
                    <span className="shrink-0 text-[10px] text-[var(--color-text-muted)]">
                      {inc.assigned_ambulance
                        ? `→ ${callsignById.get(inc.assigned_ambulance) ?? inc.assigned_ambulance}`
                        : 'UNASSIGNED'}
                    </span>
                  </div>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </PanelFrame>
  );
}
