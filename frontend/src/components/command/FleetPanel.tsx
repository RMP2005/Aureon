'use client';

import { useMemo, useState } from 'react';
import type { RunLiveState } from '@/lib/api';
import { useTwinStore } from '@/lib/twin/store';
import { EmptyNote, PanelFrame, StatusChip } from './primitives';

const FLEET_ORDER = [
  'dispatched_to_scene',
  'on_scene_triage',
  'transporting_hospital',
  'at_hospital_handover',
  'returning_to_base',
  'idle_at_base',
];

/**
 * Fleet panel (Phase 10D) — every unit, grouped by operational state.
 * Busy units float to the top; selection drives scene focus + inspector.
 */
export default function FleetPanel({ liveState }: { liveState: RunLiveState | null }) {
  const [busyOnly, setBusyOnly] = useState(false);
  const ambulances = useMemo(() => {
    const list = [...(liveState?.ambulances ?? [])];
    list.sort(
      (a, b) =>
        (FLEET_ORDER.indexOf(a.status) ?? 99) -
          (FLEET_ORDER.indexOf(b.status) ?? 99) ||
        a.callsign.localeCompare(b.callsign),
    );
    return busyOnly
      ? list.filter((a) => a.status !== 'idle_at_base' && a.status !== 'returning_to_base')
      : list;
  }, [liveState, busyOnly]);

  const selection = useTwinStore((s) => s.selection);
  const select = useTwinStore((s) => s.select);

  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const a of liveState?.ambulances ?? []) c[a.status] = (c[a.status] ?? 0) + 1;
    return c;
  }, [liveState]);

  return (
    <PanelFrame
      title="Fleet"
      right={
        <button
          onClick={() => setBusyOnly((v) => !v)}
          className={`hud-stamp !text-[9px] rounded-sm border px-1.5 py-0.5 transition-colors ${
            busyOnly
              ? 'border-teal-core/40 text-teal-core'
              : 'border-hairline-strong text-[var(--color-text-muted)]'
          }`}
        >
          BUSY ONLY
        </button>
      }
    >
      {ambulances.length === 0 ? (
        <EmptyNote>Fleet offline — no live run.</EmptyNote>
      ) : (
        <ul className="divide-y divide-[color:var(--color-hairline)]">
          {ambulances.map((amb) => {
            const selected =
              selection?.kind === 'ambulance' && selection.id === amb.id;
            return (
              <li key={amb.id}>
                <button
                  onClick={() => select({ kind: 'ambulance', id: amb.id })}
                  className={`flex w-full items-center gap-2 px-3 py-2 text-left transition-colors hover:bg-white/[0.03] ${
                    selected ? 'bg-teal-core/5 border-l-2 border-l-teal-core' : ''
                  }`}
                >
                  <span className="tnum w-16 shrink-0 font-mono text-xs">
                    {amb.callsign}
                  </span>
                  <StatusChip value={amb.status} />
                  <span className="ml-auto flex shrink-0 items-center gap-2 text-[10px] text-[var(--color-text-muted)]">
                    <span>{amb.capability.toUpperCase()}</span>
                    <span className="tnum">M{amb.missions_completed}</span>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
      {Object.keys(counts).length > 0 && (
        <div className="sticky bottom-0 flex flex-wrap gap-x-3 gap-y-1 border-t border-hairline bg-panel-1 px-3 py-2">
          {FLEET_ORDER.filter((s) => counts[s]).map((s) => (
            <span key={s} className="hud-stamp !text-[9px] text-[var(--color-text-muted)]">
              {counts[s]}× {s.replace(/_/g, ' ').split(' ').pop()}
            </span>
          ))}
        </div>
      )}
    </PanelFrame>
  );
}
