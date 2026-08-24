'use client';

import { useEffect, useRef, useState } from 'react';
import ConceptBlock from '@/components/docs/ConceptBlock';
import {
  analyzeCustomScenario,
  localityZone,
  INCIDENT_TYPES,
  LOCALITIES,
  SEVERITIES,
  TRAFFIC_OPTIONS,
  WEATHER_OPTIONS,
  TIME_OPTIONS,
  type CustomInputs,
  type CustomAnalysis,
  type Severity,
} from '@/lib/compare/custom-analysis';

/**
 * Compare demo experience (Phase 11J).
 *
 * Full-width product showcase with two modes:
 *  - PRESET SCENARIO — four canonical emergencies, animated side by side.
 *  - CUSTOM SCENARIO — user builds an emergency (type, location, severity,
 *    conditions) and receives a deterministic recommendation with a plain-
 *    English rationale.
 *
 * Honesty contract: all demo values are clearly stamped teaching examples.
 * Engine-reported evidence lives in the ENGINE EVIDENCE tab.
 */

/* ------------------------------------------------------------------ */
/* Shared visual atoms                                                 */
/* ------------------------------------------------------------------ */

const FIELD_CLS =
  'mt-1.5 w-full rounded-md border border-hairline-strong bg-panel-2 px-3 py-2.5 font-mono text-sm text-[var(--color-text-primary)] focus:border-teal-core/60 focus:outline-none';

function Icon({ children }: { children: React.ReactNode }) {
  return (
    <svg
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.3}
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-5 w-5 shrink-0"
      aria-hidden
    >
      {children}
    </svg>
  );
}

const ICONS = {
  cardiac: (
    <Icon>
      <path d="M8 13.6l-.74-.66C3.5 9.6 1.6 7.86 1.6 5.6A3.3 3.3 0 0 1 8 4.05 3.3 3.3 0 0 1 14.4 5.6c0 2.26-1.9 4-5.66 7.34L8 13.6z" />
      <path d="M2.8 8h2.4l1-1.6 1.6 3 1.2-2 1 1h2.2" />
    </Icon>
  ),
  collision: (
    <Icon>
      <path d="M2 10.5h12M4.2 10.5L5.4 6.8h5.2l1.2 3.7" />
      <path d="M6.4 6.8V4.6h3.2v2.2" />
      <circle cx="4.6" cy="12.2" r="1.3" />
      <circle cx="11.4" cy="12.2" r="1.3" />
      <path d="M8.6 1.6l-.9 1.6h1.8l-.9 1.6" />
    </Icon>
  ),
  fire: (
    <Icon>
      <path d="M8 1.6c1.9 2.4 4.3 4.3 4.3 7.2a4.3 4.3 0 1 1-8.6 0C3.7 5.9 6.1 4 8 1.6z" />
      <path d="M8 8.2c.9 1.1.9 2.3 0 3.4-.9-1.1-.9-2.3 0-3.4z" />
    </Icon>
  ),
  casualty: (
    <Icon>
      <rect x="2.4" y="6.4" width="4.4" height="7.2" />
      <rect x="9.2" y="3.2" width="4.4" height="10.4" />
      <path d="M4.6 9h1.6M5.4 8.2v1.6" />
      <path d="M11.4 6h1.4M11.4 8.6h1.4M11.4 11.2h1.4" />
    </Icon>
  ),
};

/* ------------------------------------------------------------------ */
/* Preset scenario data                                                */
/* ------------------------------------------------------------------ */

interface MetricSet {
  responseMin: number;
  coveragePct: number;
  capabilityPct: number;
  hospitalDelayMin: number;
}

interface TimelineStep {
  label: string;
  baselineSec: number;
  aureonSec: number;
}

interface DemoScenario {
  id: string;
  name: string;
  blurb: string;
  icon: React.ReactNode;
  baseline: MetricSet;
  aureon: MetricSet;
  timeline: TimelineStep[];
  story: string;
}

const SCENARIOS: DemoScenario[] = [
  {
    id: 'cardiac',
    name: 'Cardiac Emergency',
    blurb: 'A 62-year-old collapses downtown. Every minute decides outcome.',
    icon: ICONS.cardiac,
    baseline: { responseMin: 12.8, coveragePct: 61, capabilityPct: 58, hospitalDelayMin: 18 },
    aureon: { responseMin: 6.4, coveragePct: 94, capabilityPct: 96, hospitalDelayMin: 7 },
    timeline: [
      { label: 'CALL RECEIVED', baselineSec: 0, aureonSec: 0 },
      { label: 'UNIT DISPATCHED', baselineSec: 96, aureonSec: 41 },
      { label: 'ON SCENE', baselineSec: 768, aureonSec: 384 },
      { label: 'HOSPITAL ARRIVAL', baselineSec: 1848, aureonSec: 804 },
    ],
    story:
      'Traditional dispatch sent the closest ambulance. Aureon chose a unit slightly farther away because it carried advanced life-support equipment and sat near a cardiac-ready hospital with open capacity — cutting total time-to-treatment nearly in half.',
  },
  {
    id: 'collision',
    name: 'Traffic Collision',
    blurb: 'Two vehicles collide at a junction during evening rush hour.',
    icon: ICONS.collision,
    baseline: { responseMin: 11.2, coveragePct: 66, capabilityPct: 71, hospitalDelayMin: 14 },
    aureon: { responseMin: 5.9, coveragePct: 93, capabilityPct: 97, hospitalDelayMin: 6 },
    timeline: [
      { label: 'CALL RECEIVED', baselineSec: 0, aureonSec: 0 },
      { label: 'UNIT DISPATCHED', baselineSec: 88, aureonSec: 36 },
      { label: 'ON SCENE', baselineSec: 672, aureonSec: 354 },
      { label: 'HOSPITAL ARRIVAL', baselineSec: 1512, aureonSec: 714 },
    ],
    story:
      'The nearest unit was basic life-support only. Aureon dispatched a trauma-capable crew and pre-alerted the receiving hospital in parallel, so the trauma team was ready the moment the patient arrived.',
  },
  {
    id: 'fire',
    name: 'Apartment Fire',
    blurb: 'Kitchen fire spreads through a three-storey apartment block.',
    icon: ICONS.fire,
    baseline: { responseMin: 13.5, coveragePct: 58, capabilityPct: 64, hospitalDelayMin: 20 },
    aureon: { responseMin: 7.1, coveragePct: 90, capabilityPct: 98, hospitalDelayMin: 8 },
    timeline: [
      { label: 'CALL RECEIVED', baselineSec: 0, aureonSec: 0 },
      { label: 'UNIT DISPATCHED', baselineSec: 102, aureonSec: 47 },
      { label: 'ON SCENE', baselineSec: 810, aureonSec: 426 },
      { label: 'HOSPITAL ARRIVAL', baselineSec: 2010, aureonSec: 906 },
    ],
    story:
      'The closest ambulance had no burn-care supplies. Aureon routed a burn-capable crew while keeping the nearest unit en route for triage — both arrived inside eight minutes instead of fourteen.',
  },
  {
    id: 'casualty',
    name: 'Multiple Casualty',
    blurb: 'A building collapse injures a dozen people across two zones.',
    icon: ICONS.casualty,
    baseline: { responseMin: 15.4, coveragePct: 52, capabilityPct: 55, hospitalDelayMin: 22 },
    aureon: { responseMin: 7.8, coveragePct: 91, capabilityPct: 95, hospitalDelayMin: 9 },
    timeline: [
      { label: 'CALL RECEIVED', baselineSec: 0, aureonSec: 0 },
      { label: 'UNITS DISPATCHED', baselineSec: 118, aureonSec: 52 },
      { label: 'TRIAGE COMPLETE', baselineSec: 924, aureonSec: 468 },
      { label: 'ALL HOSPITALIZED', baselineSec: 2256, aureonSec: 1008 },
    ],
    story:
      'One-by-one dispatch left later victims waiting. Aureon coordinated a multi-unit response with staged triage priorities and distributed hospital destinations, so no single emergency room was overwhelmed.',
  },
];

const BAR_MAX = { responseMin: 24, coveragePct: 100, capabilityPct: 100, hospitalDelayMin: 30 } as const;
type BarKey = keyof typeof BAR_MAX;

const BARS: { key: BarKey; label: string; lowerBetter: boolean; fmt: (v: number) => string }[] = [
  { key: 'responseMin', label: 'RESPONSE TIME', lowerBetter: true, fmt: (v) => `${v.toFixed(1)} min` },
  { key: 'coveragePct', label: 'ZONE COVERAGE', lowerBetter: false, fmt: (v) => `${Math.round(v)}%` },
  { key: 'capabilityPct', label: 'CAPABILITY MATCH', lowerBetter: false, fmt: (v) => `${Math.round(v)}%` },
  { key: 'hospitalDelayMin', label: 'HOSPITAL DELAY', lowerBetter: true, fmt: (v) => `${v.toFixed(0)} min` },
];

type Phase = 'idle' | 'running' | 'done';
const RUN_MS = 2200;

function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3);
}

type SubMode = 'preset' | 'custom';

const DEFAULT_CUSTOM: CustomInputs = {
  type: 'Cardiac Emergency',
  location: 'Koramangala',
  severity: 'Critical',
  traffic: 'Heavy',
  weather: 'Clear',
  timeOfDay: 'Evening',
};

/* ------------------------------------------------------------------ */
/* Root                                                                */
/* ------------------------------------------------------------------ */

export default function ScenarioDemo() {
  const [subMode, setSubMode] = useState<SubMode>('custom');

  // Preset state lives here so both columns share it.
  const [scenarioId, setScenarioId] = useState<string>(SCENARIOS[0].id);
  const [phase, setPhase] = useState<Phase>('idle');
  const [progress, setProgress] = useState(0);
  const rafRef = useRef<number | null>(null);

  const scenario = SCENARIOS.find((s) => s.id === scenarioId) ?? SCENARIOS[0];

  useEffect(() => {
    if (phase !== 'running') return;
    const start = performance.now();
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / RUN_MS);
      if (p < 1) {
        setProgress(easeOutCubic(p));
        rafRef.current = requestAnimationFrame(tick);
      } else {
        setProgress(1);
        setPhase('done');
      }
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, [phase]);

  const chooseScenario = (id: string) => {
    setScenarioId(id);
    setPhase('idle');
    setProgress(0);
  };

  const runPreset = () => {
    setProgress(0);
    setPhase('running');
  };

  // Reveal gates driven by eased progress.
  const showBaseline = progress > 0.12;
  const showAureon = progress > 0.42;
  const showDelta = progress > 0.72;
  const showTimeline = progress > 0.55;

  // Custom state also shared across columns.
  const [customInputs, setCustomInputs] = useState<CustomInputs>(DEFAULT_CUSTOM);
  const [customRunning, setCustomRunning] = useState(false);
  const [customAnalysis, setCustomAnalysis] = useState<CustomAnalysis | null>(null);

  const runCustom = () => {
    setCustomAnalysis(null);
    setCustomRunning(true);
    // Brief beat so the transition reads as an analysis pass.
    setTimeout(() => {
      setCustomAnalysis(analyzeCustomScenario(customInputs));
      setCustomRunning(false);
    }, 900);
  };

  return (
    <div className="mx-auto flex w-full max-w-[1720px] flex-col gap-6 p-5 lg:p-8 xl:p-10">
      {/* Masthead */}
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
        <div className="max-w-2xl">
          <h1 className="font-display text-2xl font-semibold tracking-tight lg:text-3xl">
            See the difference dispatch makes
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-[var(--color-text-secondary)]">
            Pick a scenario or build your own, then watch how a conventional
            dispatcher and Aureon handle the same call — side by side, minute
            by minute.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <span className="hud-stamp !text-[9px] text-[var(--color-text-muted)]">
            ILLUSTRATIVE DEMO — NOT ENGINE OUTPUT
          </span>
          <div className="flex rounded-md border border-hairline-strong p-0.5">
            {(
              [
                ['custom', 'CUSTOM AI SIMULATOR'],
                ['preset', 'PRESET SCENARIOS'],
              ] as [SubMode, string][]
            ).map(([value, label]) => {
              const active = subMode === value;
              return (
                <button
                  key={value}
                  onClick={() => setSubMode(value)}
                  aria-pressed={active}
                  className={`hud-label flex items-center gap-1.5 rounded px-3 py-2 !text-[9px] transition-colors ${
                    active
                      ? 'border border-teal-core/50 bg-teal-core/15 text-teal-core shadow-[0_0_16px_rgba(45,212,191,0.12)]'
                      : 'border border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'
                  }`}
                >
                  {value === 'custom' && (
                    <span
                      aria-hidden
                      className={`h-1 w-1 rounded-full ${active ? 'bg-teal-core' : 'bg-[var(--color-text-muted)]'}`}
                    />
                  )}
                  {label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Full-height two-column stage */}
      <div className="grid flex-1 items-start gap-6 lg:grid-cols-[400px_minmax(0,1fr)] xl:grid-cols-[440px_minmax(0,1fr)]">
        {/* Left rail — setup */}
        <section className="flex flex-col gap-6 lg:sticky lg:top-0">
          <div>
            <RailHeading step="01" label="Choose scenario" />
            {subMode === 'preset' ? (
              <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
                {SCENARIOS.map((s) => {
                  const active = s.id === scenarioId;
                  return (
                    <button
                      key={s.id}
                      onClick={() => chooseScenario(s.id)}
                      disabled={phase === 'running'}
                      className={`rounded-lg border p-4 text-left transition-all ${
                        active
                          ? 'border-teal-core/60 bg-teal-core/[0.06]'
                          : 'border-hairline-strong hover:border-white/25 hover:bg-panel-2'
                      } ${phase === 'running' ? 'cursor-not-allowed opacity-70' : ''}`}
                    >
                      <div className={`flex items-center gap-2.5 ${active ? 'text-teal-core' : 'text-[var(--color-text-secondary)]'}`}>
                        {s.icon}
                        <span className="text-sm font-semibold">{s.name}</span>
                      </div>
                      <p className="mt-2 text-xs leading-snug text-[var(--color-text-muted)]">
                        {s.blurb}
                      </p>
                    </button>
                  );
                })}
              </div>
            ) : (
              <CustomForm
                inputs={customInputs}
                onChange={(patch) => setCustomInputs((p) => ({ ...p, ...patch }))}
                disabled={customRunning}
              />
            )}
          </div>

          <div>
            <RailHeading step="02" label={subMode === 'preset' ? 'Run the comparison' : 'Ask Aureon'} />
            {subMode === 'preset' ? (
              <button
                onClick={runPreset}
                disabled={phase === 'running'}
                className={`w-full rounded-md px-5 py-4 text-base font-semibold transition-all ${
                  phase === 'idle'
                    ? 'bg-teal-core text-black hover:brightness-110'
                    : phase === 'running'
                      ? 'bg-teal-core/40 text-black'
                      : 'border border-hairline-strong bg-panel-2 text-[var(--color-text-primary)] hover:border-white/25'
                }`}
              >
                {phase === 'idle' && `RUN COMPARISON — ${scenario.name.toUpperCase()}`}
                {phase === 'running' && 'DISPATCHING…'}
                {phase === 'done' && 'RE-RUN COMPARISON'}
              </button>
            ) : (
              <button
                onClick={runCustom}
                disabled={customRunning}
                className={`w-full rounded-md px-5 py-4 text-base font-semibold transition-all ${
                  customRunning
                    ? 'bg-teal-core/40 text-black'
                    : 'bg-teal-core text-black hover:brightness-110'
                }`}
              >
                {customRunning ? 'ANALYZING…' : 'RUN AUREON ANALYSIS'}
              </button>
            )}
          </div>
        </section>

        {/* Right stage — outcome */}
        <section className="flex min-w-0 flex-col gap-5">
          {subMode === 'preset' ? (
            <PresetOutcome
              scenario={scenario}
              progress={progress}
              phase={phase}
              showBaseline={showBaseline}
              showAureon={showAureon}
              showDelta={showDelta}
              showTimeline={showTimeline}
            />
          ) : (
            <CustomOutcome analysis={customAnalysis} running={customRunning} />
          )}

          <p className="pb-1 text-center text-[11px] leading-relaxed text-[var(--color-text-muted)]">
            These are teaching examples. For engine-reported evidence, open{' '}
            <span className="text-[var(--color-text-secondary)]">ENGINE EVIDENCE</span>{' '}
            above — every number there comes straight from simulation runs.
          </p>
        </section>
      </div>
    </div>
  );
}

function RailHeading({ step, label }: { step: string; label: string }) {
  return (
    <div className="mb-3 flex items-center gap-3">
      <span className="hud-label text-[var(--color-text-secondary)]">
        Step {step} · {label}
      </span>
      <div className="h-px flex-1 bg-[color:var(--color-hairline)]" />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Preset outcome                                                      */
/* ------------------------------------------------------------------ */

function PresetOutcome({
  scenario,
  progress,
  phase,
  showBaseline,
  showAureon,
  showDelta,
  showTimeline,
}: {
  scenario: DemoScenario;
  progress: number;
  phase: Phase;
  showBaseline: boolean;
  showAureon: boolean;
  showDelta: boolean;
  showTimeline: boolean;
}) {
  const rtImprovement = Math.round(
    ((scenario.baseline.responseMin - scenario.aureon.responseMin) /
      scenario.baseline.responseMin) * 100,
  );
  const ghGain = Math.max(
    0,
    Math.round((1 - scenario.aureon.responseMin / 60) * 100 -
      (1 - scenario.baseline.responseMin / 60) * 100),
  );
  const started = progress > 0;

  return (
    <div
      className={`flex min-h-[420px] flex-col gap-5 rounded-xl border border-hairline bg-panel-1/60 p-5 backdrop-blur-sm transition-opacity duration-500 lg:min-h-[540px] lg:p-6 ${
        started ? 'opacity-100' : 'pointer-events-none opacity-45'
      }`}
    >
      {!started && (
        <div className="flex flex-1 items-center justify-center">
          <p className="max-w-xs text-center text-sm leading-relaxed text-[var(--color-text-muted)]">
            Choose a scenario and press run — the outcome appears here,
            strategy against strategy.
          </p>
        </div>
      )}

      {started && (
        <>
          {/* Headline delta */}
          <div className="grid gap-4 md:grid-cols-2">
            <StrategyCard
              tone="baseline"
              visible={showBaseline}
              title="BASELINE DISPATCH"
              subtitle="Closest unit wins"
              headline={`${scenario.baseline.responseMin.toFixed(1)} min`}
              caption="mean response time"
            />
            <StrategyCard
              tone="aureon"
              visible={showAureon}
              title="AUREON"
              subtitle="Right unit, right hospital, right now"
              headline={`${scenario.aureon.responseMin.toFixed(1)} min`}
              caption="mean response time"
            />
          </div>

          {/* Animated metric bars */}
          {(showBaseline || showAureon) && (
            <div className="rounded-lg border border-hairline bg-panel-1/80 p-4 lg:p-5">
              {BARS.map((bar) => (
                <MetricBarRow
                  key={bar.key}
                  label={bar.label}
                  lowerBetter={bar.lowerBetter}
                  fmt={bar.fmt}
                  baseline={scenario.baseline[bar.key]}
                  aureon={scenario.aureon[bar.key]}
                  max={BAR_MAX[bar.key]}
                  showBaseline={showBaseline}
                  showAureon={showAureon}
                />
              ))}
            </div>
          )}

          {/* Improvement chips */}
          {showDelta && (
            <div className="flex flex-wrap gap-2.5">
              <Chip label="FASTER RESPONSE" value={`${rtImprovement > 0 ? '−' : '+'}${Math.abs(rtImprovement)}%`} good={rtImprovement > 0} />
              <Chip label="GOLDEN HOUR WINDOW" value={`+${ghGain} PTS`} good={ghGain > 0} />
              <Chip
                label="CAPABILITY MATCH"
                value={`${scenario.baseline.capabilityPct}→${scenario.aureon.capabilityPct}%`}
                good={scenario.aureon.capabilityPct >= scenario.baseline.capabilityPct}
              />
            </div>
          )}

          {/* Response timeline */}
          {showTimeline && (
            <div className="rounded-lg border border-hairline bg-panel-1/80 p-4 lg:p-5">
              <ResponseTimeline steps={scenario.timeline} progress={progress} />
            </div>
          )}

          {/* Plain-English decision story */}
          {phase === 'done' && (
            <div className="fade-up">
              <ConceptBlock title="WHAT AUREON DID DIFFERENTLY" kind="intelligence">
                {scenario.story}
              </ConceptBlock>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function StrategyCard({
  tone,
  visible,
  title,
  subtitle,
  headline,
  caption,
}: {
  tone: 'baseline' | 'aureon';
  visible: boolean;
  title: string;
  subtitle: string;
  headline: string;
  caption: string;
}) {
  const accent = tone === 'baseline' ? 'text-crit-red' : 'text-teal-core';
  const border = tone === 'baseline' ? 'border-crit-red/30' : 'border-teal-core/40';
  const glow =
    tone === 'aureon' ? 'shadow-[0_0_36px_-10px_var(--color-teal-core)]' : '';
  return (
    <div
      className={`rounded-xl border bg-panel-1/80 p-5 backdrop-blur-sm transition-all duration-500 lg:p-6 ${border} ${glow} ${
        visible ? 'translate-y-0 opacity-100' : 'translate-y-1.5 opacity-0'
      }`}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <span className={`hud-label !text-[10px] ${accent}`}>{title}</span>
        <span className="text-[11px] italic text-[var(--color-text-muted)]">{subtitle}</span>
      </div>
      <div
        className={`tnum mt-3 font-display text-5xl font-semibold tracking-tight lg:text-6xl ${
          tone === 'baseline'
            ? 'text-[var(--color-text-secondary)]'
            : 'text-[var(--color-text-primary)]'
        }`}
      >
        {headline}
      </div>
      <div className="hud-stamp mt-2 !text-[9px] text-[var(--color-text-muted)]">
        {caption.toUpperCase()}
      </div>
    </div>
  );
}

function MetricBarRow({
  label,
  lowerBetter,
  fmt,
  baseline,
  aureon,
  max,
  showBaseline,
  showAureon,
}: {
  label: string;
  lowerBetter: boolean;
  fmt: (v: number) => string;
  baseline: number;
  aureon: number;
  max: number;
  showBaseline: boolean;
  showAureon: boolean;
}) {
  const bPct = (baseline / max) * 100;
  const aPct = (aureon / max) * 100;
  const aureonWins = lowerBetter ? aureon < baseline : aureon > baseline;
  return (
    <div className="py-2.5 first:pt-0 last:pb-0">
      <div className="mb-2 flex items-baseline justify-between">
        <span className="hud-label !text-[9px] text-[var(--color-text-muted)]">{label}</span>
        {showBaseline && showAureon && (
          <span className={`tnum font-mono text-xs ${aureonWins ? 'text-teal-core' : 'text-crit-red'}`}>
            {fmt(baseline)} → {fmt(aureon)}
          </span>
        )}
      </div>
      <BarTrack visible={showBaseline} pct={bPct} tone="baseline" valueLabel={fmt(baseline)} />
      <div className="h-1.5" />
      <BarTrack visible={showAureon} pct={aPct} tone="aureon" valueLabel={fmt(aureon)} />
    </div>
  );
}

function BarTrack({
  pct,
  tone,
  visible,
  valueLabel,
}: {
  pct: number;
  tone: 'baseline' | 'aureon';
  visible: boolean;
  valueLabel: string;
}) {
  const filled =
    tone === 'baseline'
      ? 'bg-gradient-to-r from-slate-600 to-slate-400'
      : 'bg-gradient-to-r from-teal-core/60 to-teal-core';
  return (
    <div className="flex items-center gap-3">
      <div className="relative h-2 flex-1 overflow-hidden rounded-full bg-[color:var(--color-hairline)]">
        <div
          className={`absolute inset-y-0 left-0 rounded-full transition-all duration-700 ease-out ${filled}`}
          style={{ width: visible ? `${Math.min(100, pct)}%` : '0%' }}
        />
      </div>
      <span
        className={`tnum w-20 shrink-0 text-right font-mono text-xs transition-opacity duration-500 ${
          visible ? 'opacity-100' : 'opacity-0'
        } ${tone === 'baseline' ? 'text-[var(--color-text-muted)]' : 'text-teal-core'}`}
      >
        {valueLabel}
      </span>
    </div>
  );
}

function Chip({ label, value, good }: { label: string; value: string; good: boolean }) {
  return (
    <span
      className={`hud-stamp rounded-md border px-3 py-1.5 !text-[11px] ${
        good
          ? 'border-teal-core/40 bg-teal-core/[0.07] text-teal-core'
          : 'border-crit-red/40 bg-crit-red/[0.07] text-crit-red'
      }`}
    >
      {label} · <span className="tnum font-semibold">{value}</span>
    </span>
  );
}

function ResponseTimeline({
  steps,
  progress,
}: {
  steps: TimelineStep[];
  progress: number;
}) {
  const maxSec = Math.max(...steps.map((s) => Math.max(s.baselineSec, s.aureonSec)));
  const localT = Math.max(0, Math.min(1, (progress - 0.55) / 0.45));

  const Row = ({ tone }: { tone: 'baseline' | 'aureon' }) => (
    <div className="relative h-7">
      <div
        className="absolute top-1/2 h-px -translate-y-1/2"
        style={{
          left: 0,
          width: `${localT * 100}%`,
          background:
            tone === 'baseline'
              ? 'linear-gradient(to right, transparent, rgba(148,163,184,0.55))'
              : 'linear-gradient(to right, transparent, var(--color-teal-core))',
        }}
      />
      {steps.map((step, i) => {
        const sec = tone === 'baseline' ? step.baselineSec : step.aureonSec;
        const x = (sec / maxSec) * 100;
        const reached = localT >= x / 100 || sec === 0;
        return (
          <div
            key={i}
            className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2"
            style={{ left: `${x}%` }}
          >
            <div
              className={`h-2.5 w-2.5 rotate-45 border ${
                reached
                  ? tone === 'baseline'
                    ? 'border-slate-300 bg-slate-500'
                    : 'border-teal-core bg-teal-core shadow-[0_0_10px_var(--color-teal-core)]'
                  : 'border-hairline-strong bg-transparent'
              }`}
            />
          </div>
        );
      })}
    </div>
  );

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <span className="hud-label !text-[9px] text-[var(--color-text-muted)]">RESPONSE TIMELINE</span>
        <div className="flex gap-4">
          <span className="hud-stamp !text-[9px] text-crit-red">■ BASELINE</span>
          <span className="hud-stamp !text-[9px] text-teal-core">■ AUREON</span>
        </div>
      </div>
      <div className="relative mb-1 h-4 pl-2">
        <span className="hud-stamp absolute left-2 !text-[8px] text-crit-red">● INCIDENT</span>
      </div>
      <div className="pl-2">
        <Row tone="baseline" />
        <div className="my-1.5 h-px bg-[color:var(--color-hairline)]" />
        <Row tone="aureon" />
      </div>
      <div className="mt-3 flex flex-wrap justify-between gap-x-4 gap-y-1 pl-2">
        {steps.map((s, i) => (
          <span key={i} className="hud-stamp !text-[8px] text-[var(--color-text-muted)]">
            {s.label} · {fmtClock(s.baselineSec)} → {fmtClock(s.aureonSec)}
          </span>
        ))}
      </div>
    </div>
  );
}

function fmtClock(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return m > 0 ? `${m}:${String(s).padStart(2, '0')}` : `0:${String(s).padStart(2, '0')}`;
}

/* ------------------------------------------------------------------ */
/* Custom scenario — form                                              */
/* ------------------------------------------------------------------ */

const SEVERITY_TONE: Record<Severity, string> = {
  Low: 'text-[var(--color-text-secondary)]',
  Medium: 'text-sky-300',
  High: 'text-amber-warn',
  Critical: 'text-crit-red',
};
const SEVERITY_ACTIVE: Record<Severity, string> = {
  Low: 'bg-white/10 border-white/30',
  Medium: 'bg-sky-400/15 border-sky-300/50',
  High: 'bg-amber-warn/15 border-amber-warn/50',
  Critical: 'bg-crit-red/15 border-crit-red/50',
};

function CustomForm({
  inputs,
  onChange,
  disabled,
}: {
  inputs: CustomInputs;
  onChange: (patch: Partial<CustomInputs>) => void;
  disabled: boolean;
}) {
  return (
    <div className={`flex flex-col gap-4 rounded-lg border border-hairline bg-panel-1/70 p-4 backdrop-blur-sm ${disabled ? 'opacity-70' : ''}`}>
      <label className="block">
        <span className="hud-stamp !text-[9px] block text-[var(--color-text-muted)]">INCIDENT TYPE</span>
        <select
          value={inputs.type}
          onChange={(e) => onChange({ type: e.target.value as CustomInputs['type'] })}
          className={FIELD_CLS}
        >
          {INCIDENT_TYPES.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </label>

      <label className="relative block">
        <span className="hud-stamp !text-[9px] block text-[var(--color-text-muted)]">
          LOCATION{localityZone(inputs.location) ? ` · ${localityZone(inputs.location)?.toUpperCase()}` : ''}
        </span>
        <LocationField value={inputs.location} onChange={(v) => onChange({ location: v })} disabled={disabled} />
      </label>

      <div>
        <span className="hud-stamp !text-[9px] block text-[var(--color-text-muted)]">SEVERITY</span>
        <div className="mt-1.5 grid grid-cols-4 gap-1.5">
          {SEVERITIES.map((sev) => {
            const active = inputs.severity === sev;
            return (
              <button
                key={sev}
                onClick={() => onChange({ severity: sev })}
                disabled={disabled}
                className={`rounded-md border px-1 py-2 text-xs font-semibold transition-all ${
                  active
                    ? `${SEVERITY_ACTIVE[sev]} ${SEVERITY_TONE[sev]}`
                    : 'border-hairline-strong text-[var(--color-text-muted)] hover:border-white/25 hover:text-[var(--color-text-secondary)]'
                }`}
              >
                {sev}
              </button>
            );
          })}
        </div>
      </div>

      <details className="group rounded-md border border-hairline bg-panel-2/50 px-3 py-2.5">
        <summary className="cursor-pointer select-none text-xs text-[var(--color-text-secondary)] marker:content-none">
          <span className="hud-stamp !text-[9px] text-[var(--color-text-muted)] group-open:text-teal-core">
            OPTIONAL CONTEXT {inputs.weather !== 'Clear' || inputs.timeOfDay !== 'Afternoon' ? '· SET' : ''}
          </span>
        </summary>
        <div className="mt-3 flex flex-col gap-3">
          <ContextSelect label="TRAFFIC CONDITION" value={inputs.traffic} options={[...TRAFFIC_OPTIONS]} onChange={(v) => onChange({ traffic: v })} />
          <ContextSelect label="WEATHER" value={inputs.weather} options={[...WEATHER_OPTIONS]} onChange={(v) => onChange({ weather: v })} />
          <ContextSelect label="TIME OF DAY" value={inputs.timeOfDay} options={[...TIME_OPTIONS]} onChange={(v) => onChange({ timeOfDay: v })} />
        </div>
      </details>
    </div>
  );
}

/**
 * Searchable locality selector — filters real Bengaluru areas as you type,
 * accepts any custom location, keyboard-friendly.
 */
function LocationField({
  value,
  onChange,
  disabled,
}: {
  value: string;
  onChange: (v: string) => void;
  disabled: boolean;
}) {
  const [open, setOpen] = useState(false);
  const q = value.trim().toLowerCase();
  const matches =
    q.length === 0
      ? LOCALITIES
      : LOCALITIES.filter((l) => l.name.toLowerCase().includes(q));

  return (
    <div className="relative">
      <input
        value={value}
        disabled={disabled}
        onChange={(e) => {
          onChange(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        placeholder="Type or pick an area…"
        className={`${FIELD_CLS} placeholder:text-[var(--color-text-muted)]/60`}
        role="combobox"
        aria-expanded={open && matches.length > 0}
        aria-label="Incident location"
      />
      {open && matches.length > 0 && (
        <ul className="absolute inset-x-0 top-full z-20 mt-1 max-h-52 overflow-y-auto rounded-md border border-hairline-strong bg-panel-2 py-1 shadow-xl">
          {matches.map((l) => (
            <li key={l.name}>
              <button
                type="button"
                onMouseDown={(e) => {
                  // Select before the input's blur closes the list.
                  e.preventDefault();
                  onChange(l.name);
                  setOpen(false);
                }}
                className={`flex w-full items-center justify-between px-3 py-2 text-left font-mono text-xs transition-colors ${
                  l.name.toLowerCase() === q
                    ? 'bg-teal-core/15 text-teal-core'
                    : 'text-[var(--color-text-secondary)] hover:bg-white/5 hover:text-[var(--color-text-primary)]'
                }`}
              >
                {l.name}
                <span className="hud-stamp !text-[8px] text-[var(--color-text-muted)]">
                  {(localityZone(l.name) ?? '').toUpperCase()}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ContextSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <label className="block">
      <span className="hud-stamp !text-[9px] block text-[var(--color-text-muted)]">{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)} className={FIELD_CLS}>
        {options.map((o) => (
          <option key={o} value={o}>{o}</option>
        ))}
      </select>
    </label>
  );
}

/* ------------------------------------------------------------------ */
/* Custom scenario — outcome                                           */
/* ------------------------------------------------------------------ */

function CustomOutcome({
  analysis,
  running,
}: {
  analysis: CustomAnalysis | null;
  running: boolean;
}) {
  return (
    <div className="flex min-h-[420px] flex-col gap-5 rounded-xl border border-hairline bg-panel-1/60 p-5 backdrop-blur-sm lg:min-h-[540px] lg:p-6">
      {!analysis && !running && (
        <div className="flex flex-1 items-center justify-center">
          <p className="max-w-sm text-center text-sm leading-relaxed text-[var(--color-text-muted)]">
            Describe an emergency on the left, then run the analysis. Aureon&apos;s
            recommended unit, response time, destination hospital, and its
            reasoning appear here.
          </p>
        </div>
      )}

      {running && (
        <div className="flex flex-1 flex-col items-center justify-center gap-4">
          <span className="hud-label animate-pulse text-teal-core">ANALYZING NETWORK STATE…</span>
          <div className="h-px w-48 overflow-hidden bg-[color:var(--color-hairline)]">
            <div className="h-full w-1/2 animate-pulse bg-teal-core" />
          </div>
        </div>
      )}

      {analysis && (
        <>
          {/* Recommendation tiles */}
          <div className="grid gap-4 md:grid-cols-3">
            <ResultTile
              label="RECOMMENDED UNIT"
              value={analysis.unitId}
              sub={`${analysis.unitClass} · ${analysis.zoneName}, ${analysis.unitsAvailable} crews on duty`}
              accent
            />
            <ResultTile
              label="ESTIMATED RESPONSE"
              value={`${analysis.etaMinutes.toFixed(1)} min`}
              sub={`${analysis.distanceKm.toFixed(1)} km approach, condition-adjusted`}
            />
            <ResultTile
              label="HOSPITAL RECOMMENDED"
              value={analysis.hospitalName}
              sub={`${hospitalSub(analysis)}`}
            />
          </div>

          {/* Rationale */}
          <ConceptBlock title="WHY AUREON SELECTED THIS" kind="intelligence">
            {analysis.explanation}
          </ConceptBlock>

          <div className="rounded-lg border border-hairline bg-panel-1/80 p-4 lg:p-5">
            <span className="hud-label !text-[9px] block text-[var(--color-text-muted)]">
              DECISION FACTORS
            </span>
            <ul className="mt-3 space-y-2.5">
              {analysis.factors.map((f, i) => (
                <li key={i} className="flex gap-2.5 text-sm leading-relaxed text-[var(--color-text-secondary)]">
                  <span className="mt-0.5 shrink-0 text-teal-core">▸</span>
                  {f}
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </div>
  );
}

function hospitalSub(a: CustomAnalysis): string {
  return `${a.hospitalReason} — ${a.hospitalDistanceKm.toFixed(1)} km transfer.`;
}

function ResultTile({
  label,
  value,
  sub,
  accent = false,
}: {
  label: string;
  value: string;
  sub: string;
  accent?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border p-5 transition-all duration-500 ${
        accent
          ? 'border-teal-core/40 bg-panel-1/80 shadow-[0_0_36px_-10px_var(--color-teal-core)]'
          : 'border-hairline-strong bg-panel-1/80'
      }`}
    >
      <span className={`hud-label !text-[9px] block ${accent ? 'text-teal-core' : 'text-[var(--color-text-muted)]'}`}>
        {label}
      </span>
      <div
        className={`tnum mt-2.5 break-words font-display text-2xl font-semibold tracking-tight lg:text-3xl ${
          accent ? 'text-teal-core' : 'text-[var(--color-text-primary)]'
        }`}
      >
        {value}
      </div>
      <p className="mt-2 text-xs leading-snug text-[var(--color-text-muted)]">{sub}</p>
    </div>
  );
}
