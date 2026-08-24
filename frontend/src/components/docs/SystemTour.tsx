'use client';

import { useEffect, useState } from 'react';

/**
 * SystemTour (Phase 11F) — six-step guided walkthrough.
 *
 * Each step pairs a schematic visual with a two-sentence explanation.
 * Controls: NEXT / BACK / SKIP. Completion persists to localStorage under
 * `aureon:docs_completed`; the tour never starts itself after that.
 */

const STORAGE_KEY = 'aureon:docs_completed';

interface Step {
  id: string;
  stamp: string;
  title: string;
  body: string;
}

const STEPS: Step[] = [
  {
    id: 'twin',
    stamp: '01',
    title: 'This is the digital twin',
    body: "Aureon recreates a simplified version of Bengaluru's emergency network. Roads, districts and distances are real — projected from geodetic data.",
  },
  {
    id: 'hospitals',
    stamp: '02',
    title: 'Hospitals',
    body: 'Hospitals are evaluated based on capacity, availability, and capability. Blue glowing markers mark clinical infrastructure.',
  },
  {
    id: 'ambulances',
    stamp: '03',
    title: 'Ambulance units',
    body: 'Units move through the network and respond to incidents. Bright teal means an active response; dim teal is capacity at rest.',
  },
  {
    id: 'incidents',
    stamp: '04',
    title: 'Incidents',
    body: 'Emergencies appear dynamically and create response challenges. Red is reserved for true critical events — you will only see it when it matters.',
  },
  {
    id: 'decisions',
    stamp: '05',
    title: 'AI decisions',
    body: 'The AI does not only choose an action. It records why that action was selected — factors considered, tradeoffs made, alternatives rejected.',
  },
  {
    id: 'replay',
    stamp: '06',
    title: 'Replay and analysis',
    body: 'Every simulation can be replayed and inspected. The debrief reconstructs each mission from recorded facts, not memory.',
  },
];

/* --- Schematic visuals (pure SVG, one per step) -------------------------- */

function TwinVisual() {
  return (
    <svg viewBox="0 0 200 120" className="w-full max-w-sm" aria-hidden>
      <g stroke="#3a4658" strokeWidth="1">
        <path d="M10 30h180M10 60h180M10 90h180M40 10v100M80 10v100M120 10v100M160 10v100" opacity="0.55" />
      </g>
      <path d="M10 60h180M100 10v100" stroke="#8fa3bf" strokeWidth="1.6" />
      <rect x="94" y="54" width="12" height="12" fill="none" stroke="#16F2D4" strokeWidth="1.4" />
      <text x="112" y="64" fill="#93a0b4" fontSize="7" fontFamily="monospace">CITY CORE</text>
    </svg>
  );
}

function HospitalsVisual() {
  return (
    <svg viewBox="0 0 200 120" className="w-full max-w-sm" aria-hidden>
      <g stroke="#3a4658" strokeWidth="1">
        <path d="M10 30h180M10 60h180M10 90h180M40 10v100M80 10v100M120 10v100M160 10v100" opacity="0.4" />
      </g>
      {[
        [50, 38],
        [130, 52],
        [86, 88],
      ].map(([x, y], i) => (
        <g key={i}>
          <circle cx={x} cy={y} r="4" fill="#4da3ff" opacity="0.95" />
          <circle cx={x} cy={y} r="8" fill="none" stroke="#4da3ff" strokeWidth="0.8" opacity="0.35" />
        </g>
      ))}
      <text x="142" y="46" fill="#93a0b4" fontSize="7" fontFamily="monospace">CAPACITY · CAPABILITY</text>
    </svg>
  );
}

function AmbulancesVisual() {
  return (
    <svg viewBox="0 0 200 120" className="w-full max-w-sm" aria-hidden>
      <g stroke="#3a4658" strokeWidth="1">
        <path d="M10 30h180M10 60h180M10 90h180M40 10v100M80 10v100M120 10v100M160 10v100" opacity="0.4" />
      </g>
      {[
        [40, 30, 96],
        [120, 60, 20],
        [80, 90, 150],
      ].map(([x, y, dash], i) => (
        <g key={i}>
          <path d={`M${x} ${y}h56`} stroke="#16F2D4" strokeWidth="1.2" strokeDasharray="3 5" opacity="0.6" />
          <rect x={x + 22} y={y - 3} width="9" height="6" fill="#16F2D4" opacity="0.95" />
          <text x={x} y={y - 8} fill="#5b6678" fontSize="6.5" fontFamily="monospace" opacity={i === 0 ? 0 : 1}>EN ROUTE</text>
          <text x={x} y={y - 8} fill="#5b6678" fontSize="6.5" fontFamily="monospace">{dash > 100 ? 'RESPONDING' : ''}</text>
        </g>
      ))}
    </svg>
  );
}

function IncidentsVisual() {
  return (
    <svg viewBox="0 0 200 120" className="w-full max-w-sm" aria-hidden>
      <g stroke="#3a4658" strokeWidth="1">
        <path d="M10 30h180M10 60h180M10 90h180M40 10v100M80 10v100M120 10v100M160 10v100" opacity="0.4" />
      </g>
      {[
        [70, 45, 14],
        [140, 78, 10],
      ].map(([x, y, r], i) => (
        <g key={i}>
          <circle cx={x} cy={y} r={r} fill="none" stroke="#FF3655" strokeWidth="1.2" opacity="0.85" />
          <circle cx={x} cy={y} r={r * 0.45} fill="none" stroke="#FF3655" strokeWidth="1" opacity="0.5" />
          <text x={Number(x) + Number(r) + 6} y={Number(y) + 3} fill="#93a0b4" fontSize="7" fontFamily="monospace">
            {i === 0 ? 'CRITICAL' : 'HIGH'}
          </text>
        </g>
      ))}
    </svg>
  );
}

function DecisionVisual() {
  return (
    <svg viewBox="0 0 200 120" className="w-full max-w-sm" aria-hidden>
      {[0, 1, 2].map((r) => (
        <g key={r}>
          <rect x="24" y={26 + r * 26} width="152" height="18" fill="none" stroke={r === 0 ? '#7C5CFF' : '#3a4658'} strokeWidth="1.2" />
          <text x="32" y={38 + r * 26} fontSize="7" fontFamily="monospace" fill={r === 0 ? '#B9A5FF' : '#5b6678'}>
            {r === 0 ? '▸ DISPATCH ALS-CBD-03' : r === 1 ? 'REJECTED ALS-IND-07 · slower' : 'REJECTED BLS-EAST-02 · capability'}
          </text>
        </g>
      ))}
      <text x="24" y="18" fontSize="7" fontFamily="monospace" fill="#7C5CFF">DECISION LEDGER · RATIONALE RECORDED</text>
    </svg>
  );
}

function ReplayVisual() {
  return (
    <svg viewBox="0 0 200 120" className="w-full max-w-sm" aria-hidden>
      <rect x="24" y="58" width="152" height="4" fill="#111a2e" />
      <rect x="24" y="58" width="92" height="4" fill="#16F2D4" opacity="0.8" />
      {[
        [58, 'INCIDENT'],
        [116, 'DISPATCH'],
        [148, 'RESOLVED'],
      ].map(([x, label]) => (
        <g key={label as string}>
          <rect x={(x as number) - 3} y="56" width="6" height="8" fill="#FF3655" transform={`rotate(45 ${x} 60)`} opacity={label === 'RESOLVED' ? 1 : 0.75} />
          <text x={(x as number) - 14} y="76" fontSize="6.5" fontFamily="monospace" fill="#5b6678">{label}</text>
        </g>
      ))}
      <path d="M24 44v28M176 44v28" stroke="#3a4658" strokeWidth="1" />
      <text x="24" y="98" fontSize="7" fontFamily="monospace" fill="#93a0b4">T+00:00</text>
      <text x="146" y="98" fontSize="7" fontFamily="monospace" fill="#93a0b4">T+36:00</text>
    </svg>
  );
}

const VISUALS = [TwinVisual, HospitalsVisual, AmbulancesVisual, IncidentsVisual, DecisionVisual, ReplayVisual];

/* ------------------------------------------------------------------------- */

export default function SystemTour() {
  const [stepIndex, setStepIndex] = useState<number | null>(null);
  const [completed, setCompleted] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setReady(true);
    try {
      setCompleted(window.localStorage.getItem(STORAGE_KEY) === '1');
    } catch {
      /* storage unavailable — treat as not completed */
    }
  }, []);

  const finish = () => {
    try {
      window.localStorage.setItem(STORAGE_KEY, '1');
    } catch {
      /* non-fatal */
    }
    setCompleted(true);
    setStepIndex(null);
  };

  const step = stepIndex !== null ? STEPS[stepIndex] : null;
  const Visual = stepIndex !== null ? VISUALS[stepIndex] : null;

  return (
    <div>
      {!step && (
        <button
          type="button"
          onClick={() => setStepIndex(0)}
          className="rounded-md bg-teal-core px-7 py-3 text-[13px] font-semibold tracking-wide text-black transition-all hover:brightness-110 hover:shadow-[0_0_24px_rgba(22,242,212,0.25)]"
        >
          {ready && completed ? '↻ REPLAY SYSTEM TOUR' : '▶ START SYSTEM TOUR'}
        </button>
      )}

      {step && Visual && (
        <div className="border border-hairline bg-panel-1">
          {/* Step header */}
          <div className="flex items-center justify-between border-b border-hairline px-4 py-2.5">
            <p className="hud-stamp !text-[10px] text-teal-core">
              STEP {step.stamp} / 06 — {step.title.toUpperCase()}
            </p>
            <button
              type="button"
              onClick={finish}
              className="hud-stamp !text-[9px] text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text-secondary)]"
            >
              SKIP ✕
            </button>
          </div>

          {/* Body */}
          <div className="grid items-center gap-6 px-5 py-6 md:grid-cols-2 md:gap-10">
            <div
              className={`border border-hairline bg-panel-2 p-4 ${
                step.id === 'decisions' ? '[&_*]:![animation:none]' : ''
              }`}
            >
              <Visual />
            </div>
            <p className="max-w-md text-sm leading-relaxed text-[var(--color-text-secondary)]">
              {step.body}
            </p>
          </div>

          {/* Controls */}
          <div className="flex items-center justify-between border-t border-hairline px-4 py-3">
            <button
              type="button"
              disabled={stepIndex === 0}
              onClick={() => setStepIndex((i) => Math.max(0, (i ?? 0) - 1))}
              className="hud-stamp !text-[10px] rounded-md border border-hairline-strong px-4 py-2 text-[var(--color-text-secondary)] transition-colors hover:text-[var(--color-text-primary)] disabled:opacity-30 disabled:hover:text-[var(--color-text-secondary)]"
            >
              ← BACK
            </button>

            {/* Progress diamonds */}
            <div className="flex items-center gap-2" aria-hidden>
              {STEPS.map((s, i) => (
                <span
                  key={s.id}
                  className={`h-1.5 w-1.5 rotate-45 ${
                    i === stepIndex ? 'bg-teal-core' : i < (stepIndex ?? 0) ? 'bg-teal-core/40' : 'bg-white/15'
                  }`}
                />
              ))}
            </div>

            {stepIndex === STEPS.length - 1 ? (
              <button
                type="button"
                onClick={finish}
                className="hud-stamp !text-[10px] rounded-md bg-teal-core px-4 py-2 font-semibold text-black transition-all hover:brightness-110"
              >
                FINISH ✓
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setStepIndex((i) => Math.min(STEPS.length - 1, (i ?? 0) + 1))}
                className="hud-stamp !text-[10px] rounded-md border border-teal-core/50 bg-teal-core/10 px-4 py-2 text-teal-core transition-colors hover:bg-teal-core/20"
              >
                NEXT →
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
