'use client';

import { useState } from 'react';
import SystemDiagram from './SystemDiagram';
import ConceptBlock from './ConceptBlock';
import { CITY } from '@/lib/twin/projection';

/**
 * InteractiveSystemMap (Phase 11F).
 *
 * The single-page architecture overview. Clicking a stage explains it in
 * place; the City Layer detail carries real dataset counts so the map
 * describes the actual model, not an abstraction.
 */

type NodeGlyph = 'grid' | 'infra' | 'alert' | 'intel' | 'chart';

const STAGES: {
  label: string;
  sub: string;
  glyph: NodeGlyph;
  kind: 'system' | 'intelligence' | 'evidence' | 'critical';
  body: string;
}[] = [
  {
    label: 'ROAD NETWORK',
    sub: 'Bengaluru as a navigable graph',
    glyph: 'grid',
    kind: 'system',
    body: 'The arterial network is resolved into a routable graph. Every unit travels real shortest paths — distances and ETAs are measured, not guessed.',
  },
  {
    label: 'INFRASTRUCTURE',
    sub: 'Hospitals & response bases',
    glyph: 'infra',
    kind: 'evidence',
    body: 'Hospitals are modeled with capacity and capability; ambulance bases hold the fleet between calls. Blue markers on the twin are clinical infrastructure.',
  },
  {
    label: 'EMERGENCY EVENTS',
    sub: 'Incidents appear dynamically',
    glyph: 'alert',
    kind: 'critical',
    body: 'A seeded stochastic process reports incidents across the city — each with location, severity, and required capability. No two runs unfold identically unless seeded identically.',
  },
  {
    label: 'AI DECISION ENGINE',
    sub: 'Dispatch chosen — and explained',
    glyph: 'intel',
    kind: 'intelligence',
    body: 'For every incident the engine weighs coverage, ETA, and capability, then commits a unit. The decision is published with its rationale and rejected alternatives.',
  },
  {
    label: 'OUTCOME ANALYSIS',
    sub: 'Replay · debrief · compare',
    glyph: 'chart',
    kind: 'evidence',
    body: 'Runs are frame-recorded. Debriefs reconstruct each mission from recorded facts, response times are measured, and Aureon is benchmarked against baseline strategies.',
  },
];

function Glyph({ name }: { name: NodeGlyph }) {
  const s = 'h-3.5 w-3.5';
  switch (name) {
    case 'grid':
      return (
        <svg viewBox="0 0 16 16" className={s} aria-hidden fill="none" stroke="currentColor" strokeWidth="1.4">
          <path d="M2 5h12M2 11h12M5 2v12M11 2v12" />
        </svg>
      );
    case 'infra':
      return (
        <svg viewBox="0 0 16 16" className={s} aria-hidden fill="none" stroke="currentColor" strokeWidth="1.4">
          <path d="M8 2v6M4.5 14V8h7v6M2 14h12" />
        </svg>
      );
    case 'alert':
      return (
        <svg viewBox="0 0 16 16" className={s} aria-hidden fill="none" stroke="currentColor" strokeWidth="1.4">
          <circle cx="8" cy="9" r="4.5" />
          <path d="M8 2v2M1.5 9H3M13 9h1.5" />
        </svg>
      );
    case 'intel':
      return (
        <svg viewBox="0 0 16 16" className={s} aria-hidden fill="none" stroke="currentColor" strokeWidth="1.4">
          <rect x="3" y="3" width="10" height="10" />
          <path d="M3 6.5h10M6.5 6.5V13" />
        </svg>
      );
    case 'chart':
      return (
        <svg viewBox="0 0 16 16" className={s} aria-hidden fill="none" stroke="currentColor" strokeWidth="1.4">
          <path d="M2 13.5h12M4 11l3-4 2.5 2L13 4" />
        </svg>
      );
  }
}

export default function InteractiveSystemMap() {
  const [active, setActive] = useState(0);
  const stage = STAGES[active];
  const segments = CITY.segments.length.toLocaleString('en-US');

  const detail =
    active === 0
      ? `The city model represents Bengaluru as a living network: ${segments} road segments, ${CITY.hospitals.length} hospitals, ${CITY.stations.length} response bases — projected from real geodetic coordinates onto the twin's ground plane.`
      : null;

  return (
    <div className="grid gap-8 md:grid-cols-[minmax(240px,320px)_1fr] md:gap-12">
      <SystemDiagram
        nodes={STAGES.map((s) => ({ label: s.label, sub: s.sub, icon: <Glyph name={s.glyph} /> }))}
        activeIndex={active}
        onNodeClick={setActive}
      />

      <div className="space-y-6">
        <ConceptBlock title={`STAGE ${String(active + 1).padStart(2, '0')} — ${stage.label}`} kind={stage.kind}>
          {stage.body}
        </ConceptBlock>

        {detail && (
          <div className="border border-hairline bg-panel-1 px-4 py-3">
            <p className="hud-stamp !text-[9px] mb-1.5 text-teal-core">CITY LAYER</p>
            <p className="text-xs leading-relaxed text-[var(--color-text-secondary)]">{detail}</p>
            <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 hud-stamp !text-[9px] text-[var(--color-text-muted)]">
              <span>ROAD NETWORK&nbsp;&nbsp;<span className="tnum text-[var(--color-text-secondary)]">{segments}</span></span>
              <span>MEDICAL NODES&nbsp;&nbsp;<span className="tnum text-[color:var(--color-infra-blue)]">{CITY.hospitals.length}</span></span>
              <span>RESPONSE BASES&nbsp;&nbsp;<span className="tnum text-teal-core">{CITY.stations.length}</span></span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
