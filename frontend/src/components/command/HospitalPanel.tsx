'use client';

import type { RunLiveState } from '@/lib/api';
import { useTwinStore } from '@/lib/twin/store';
import { EmptyNote, OccupancyBar, PanelFrame } from './primitives';

/**
 * Hospital panel (Phase 10D) — ER + ICU load per facility.
 * Bars color strictly by occupancy thresholds (state, not decoration).
 */
export default function HospitalPanel({
  liveState,
}: {
  liveState: RunLiveState | null;
}) {
  const selection = useTwinStore((s) => s.selection);
  const select = useTwinStore((s) => s.select);

  return (
    <PanelFrame title="Hospitals">
      {!liveState || liveState.hospitals.length === 0 ? (
        <EmptyNote>No facility telemetry — no live run.</EmptyNote>
      ) : (
        <ul className="divide-y divide-[color:var(--color-hairline)]">
          {liveState.hospitals.map((h) => {
            const [erUsed, erTotal] = parseOccupancy(h.er_occupancy);
            const [icuUsed, icuTotal] = parseOccupancy(h.icu_occupancy);
            const selected =
              selection?.kind === 'hospital' && selection.id === h.id;
            return (
              <li key={h.id}>
                <button
                  onClick={() => select({ kind: 'hospital', id: h.id })}
                  className={`w-full px-3 py-2.5 text-left transition-colors hover:bg-white/[0.03] ${
                    selected ? 'bg-titanium/5 border-l-2 border-l-titanium' : ''
                  }`}
                >
                  <p className="truncate text-xs font-medium">{h.name}</p>
                  <div className="mt-1.5 space-y-1">
                    <LoadRow label="ER" used={erUsed} total={erTotal} />
                    <LoadRow label="ICU" used={icuUsed} total={icuTotal} />
                  </div>
                  {h.specialties.length > 0 && (
                    <p className="mt-1 truncate hud-stamp !text-[9px] text-[var(--color-text-muted)]">
                      {h.specialties.join(' · ').toUpperCase()}
                    </p>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </PanelFrame>
  );
}

function LoadRow({ label, used, total }: { label: string; used: number; total: number }) {
  return (
    <div className="flex items-center gap-2">
      <span className="hud-stamp w-6 shrink-0 !text-[9px] text-[var(--color-text-muted)]">
        {label}
      </span>
      <OccupancyBar used={used} total={total} />
    </div>
  );
}

function parseOccupancy(s: string): [number, number] {
  const [a, b] = s.split('/').map((n) => parseInt(n, 10));
  return [Number.isFinite(a) ? a : 0, Number.isFinite(b) ? b : 0];
}
