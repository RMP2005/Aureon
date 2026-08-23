'use client';

import { useState } from 'react';
import { useTwinStore } from '@/lib/twin/store';
import { getLiveBuffer } from '@/lib/twin/live-buffer';
import { HOSPITALS } from '@/lib/twin/city-data';
import type { DispatchLogEntry } from '@/lib/api';
import DecisionExplain, { ExplainButton } from './DecisionExplain';
import { EmptyNote, OccupancyBar, StatusChip } from './primitives';

/**
 * Entity Inspector (Phase 10D) — readout for the current scene selection.
 * Every field is a live or persisted engine value. Phase 10F-1 adds the
 * "Explain This Decision" interaction for dispatched incidents when the
 * run's persisted decision evidence is available.
 */
export default function EntityInspector({
  dispatchIndex,
}: {
  /** incident_id → persisted dispatch entry with decision evidence. */
  dispatchIndex?: Map<string, DispatchLogEntry> | null;
}) {
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
    return <IncidentRecord id={selection.id} dispatchIndex={dispatchIndex} />;
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

function IncidentRecord({
  id,
  dispatchIndex,
}: {
  id: string;
  dispatchIndex?: Map<string, DispatchLogEntry> | null;
}) {
  const [explainOpen, setExplainOpen] = useState(false);
  const inc = getLiveBuffer().incidents.find((i) => i.id === id);

  if (!inc) {
    // Completed incidents live on in the persisted dispatch evidence.
    const entry = dispatchIndex?.get(id);
    if (entry) {
      return (
        <div className="space-y-3 p-3">
          <Header
            title={entry.category.replace(/_/g, ' ').toUpperCase()}
            sub={id}
            tone="text-violet-intel"
          />
          <Row label="Status" value={<StatusChip value="closed" />} />
          <Row label="Unit" value={`${entry.callsign} · ${entry.ambulance_id}`} mono />
          <Row label="Scene ETA" value={`${(entry.scene_eta_sec / 60).toFixed(1)} min`} mono />
          <div>
            <ExplainButton
              disabled={!entry.decision}
              open={explainOpen}
              onClick={() => setExplainOpen((o) => !o)}
            />
          </div>
          {explainOpen && entry.decision && (
            <DecisionExplain
              compact
              details={entry.decision}
              context={{
                callsign: entry.callsign,
                incidentId: id,
                rationale: entry.rationale,
              }}
            />
          )}
        </div>
      );
    }
    return <EmptyNote>Incident no longer active.</EmptyNote>;
  }

  const hasEvidence = Boolean(dispatchIndex?.get(id)?.decision);
  return (
    <div className="space-y-3 p-3">
      <Header
        title={inc.category.replace(/_/g, ' ').toUpperCase()}
        sub={inc.id}
        tone="text-crit-red"
      />
      <Row label="Severity" value={<StatusChip value={inc.severity} />} />
      <Row label="Required capability" value={inc.requiredCapability.toUpperCase()} mono />
      {inc.assignedAmbulance && (
        <Row label="Assigned unit" value={inc.assignedAmbulance} mono />
      )}
      <div>
        <ExplainButton
          disabled={!hasEvidence}
          open={hasEvidence && explainOpen}
          onClick={() => setExplainOpen((o) => !o)}
        />
      </div>
      {hasEvidence && explainOpen && dispatchIndex?.get(id)?.decision && (
        <DecisionExplain
          compact
          details={dispatchIndex.get(id)!.decision!}
          context={{
            callsign: dispatchIndex.get(id)?.callsign,
            incidentId: id,
            rationale: dispatchIndex.get(id)?.rationale,
          }}
        />
      )}
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
