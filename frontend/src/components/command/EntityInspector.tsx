'use client';

import { useTwinStore } from '@/lib/twin/store';
import { getLiveBuffer } from '@/lib/twin/live-buffer';
import { HOSPITALS } from '@/lib/twin/city-data';
import { EmptyNote, OccupancyBar, StatusChip } from './primitives';

/**
 * Entity Inspector (Phase 10D) — readout for the current scene selection.
 * Every field is a live or persisted engine value.
 */
export default function EntityInspector() {
  const selection = useTwinStore((s) => s.selection);

  if (!selection) {
    return (
      <EmptyNote>
        Select a unit, facility, or incident — in the scene or from a panel —
        to inspect its live record.
      </EmptyNote>
    );
  }

  const buffer = getLiveBuffer();

  if (selection.kind === 'ambulance') {
    const a = buffer.ambulances.get(selection.id);
    if (!a) return <EmptyNote>Unit off the active roster.</EmptyNote>;
    return (
      <div className="space-y-3 p-3">
        <Header title={a.callsign} sub={a.id} tone="text-teal-core" />
        <Row label="Status" value={<StatusChip value={a.status} />} />
        <Row label="Capability" value={a.capability.toUpperCase()} mono />
        <Row label="Missions" value={String(a.missionsCompleted)} mono />
      </div>
    );
  }

  if (selection.kind === 'incident') {
    const inc = buffer.incidents.find((i) => i.id === selection.id);
    if (!inc) return <EmptyNote>Incident no longer active.</EmptyNote>;
    return (
      <div className="space-y-3 p-3">
        <Header
          title={inc.category.replace(/_/g, ' ').toUpperCase()}
          sub={inc.id}
          tone="text-crit-red"
        />
        <Row label="Severity" value={<StatusChip value={inc.severity} />} />
        <Row label="Required capability" value={inc.requiredCapability.toUpperCase()} mono />
      </div>
    );
  }

  const h = HOSPITALS.find((x) => x.id === selection.id);
  if (!h) return <EmptyNote>Unknown facility.</EmptyNote>;
  return (
    <div className="space-y-3 p-3">
      <Header title={h.name} sub={h.id} tone="text-titanium" />
      <p className="hud-stamp !text-[9px] text-[var(--color-text-muted)]">
        OCCUPANCY TELEMETRY FLOWS WITH THE LIVE RUN
      </p>
    </div>
  );
}

function Header({ title, sub, tone }: { title: string; sub: string; tone: string }) {
  return (
    <div className="border-b border-hairline pb-2">
      <p className={`font-display text-sm font-semibold tracking-wide ${tone}`}>
        {title}
      </p>
      <p className="tnum mt-0.5 font-mono text-[10px] text-[var(--color-text-muted)]">
        {sub}
      </p>
    </div>
  );
}

function Row({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-[11px] text-[var(--color-text-secondary)]">{label}</span>
      {typeof value === 'string' ? (
        <span className={`${mono ? 'tnum font-mono' : ''} text-xs`}>{value}</span>
      ) : (
        value
      )}
    </div>
  );
}
