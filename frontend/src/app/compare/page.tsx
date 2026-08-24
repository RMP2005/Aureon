'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  compareStrategies,
  getRunById,
  listSimulationResults,
  type ComparisonImprovements,
  type SimulationMetrics,
} from '@/lib/api';
import ScenarioDemo from '@/components/compare/ScenarioDemo';

/**
 * BASELINE vs AUREON compare architecture (Phase 10E-1, extended Phase 11I).
 *
 * Two experiences:
 *  - SCENARIO DEMO (default) — guided animated walkthrough with clearly
 *    stamped illustrative teaching values. Product understanding first.
 *  - ENGINE EVIDENCE — two fully engine-reported paths:
 *      1. PAIRED REPLAYS — completed runs sharing an exact scenario
 *         signature (duration · rate · seed), diffed metric-by-metric.
 *      2. CONTROLLED BENCHMARK — side-by-side run of both strategies on an
 *         identical schedule with its improvement report.
 * No synthetic values anywhere; absent data renders as absent.
 */

type Mode = 'demo' | 'evidence';

interface MetricRow {
  label: string;
  unit: string;
  get: (m: SimulationMetrics) => number;
  /** true → smaller is better; false → larger is better; null → informational */
  lowerBetter: boolean | null;
}

const ROWS: MetricRow[] = [
  { label: 'MEAN RESPONSE TIME', unit: ' min', get: (m) => m.response_times_minutes.mean, lowerBetter: true },
  { label: 'MEDIAN RESPONSE TIME', unit: ' min', get: (m) => m.response_times_minutes.median, lowerBetter: true },
  { label: 'P90 RESPONSE TIME', unit: ' min', get: (m) => m.response_times_minutes.p90, lowerBetter: true },
  { label: 'CRITICAL MEAN RT', unit: ' min', get: (m) => m.critical_cases.mean_response_time_min, lowerBetter: true },
  { label: 'GOLDEN-HOUR COMPLIANCE', unit: '%', get: (m) => m.critical_cases.target_compliance_percent, lowerBetter: false },
  { label: 'CAPABILITY MATCH', unit: '%', get: (m) => m.clinical_quality.capability_match_percent, lowerBetter: false },
  { label: 'HOSPITAL SUITABILITY', unit: '', get: (m) => m.clinical_quality.mean_hospital_suitability_score, lowerBetter: false },
  { label: 'COMPLETED INCIDENTS', unit: '', get: (m) => m.total_incidents_completed, lowerBetter: false },
  { label: 'UNSERVICED INCIDENTS', unit: '', get: (m) => m.unserviced_incidents_count, lowerBetter: true },
  { label: 'FLEET DISTANCE', unit: ' km', get: (m) => m.operations.total_fleet_distance_km, lowerBetter: true },
  { label: 'FLEET UTILIZATION', unit: '%', get: (m) => m.operations.fleet_utilization_percent, lowerBetter: null },
];

export default function ComparePage() {
  const runsQ = useQuery({
    queryKey: ['compare-run-list'],
    queryFn: listSimulationResults,
  });

  const singles = useMemo(
    () =>
      (runsQ.data?.data ?? []).filter(
        (r) => r.type === 'single_run' && r.status === 'completed',
      ),
    [runsQ.data],
  );

  // Full results for every completed single run (small payloads).
  const detailsQ = useQuery({
    queryKey: ['compare-details', singles.map((s) => s.run_id).join(',')],
    enabled: singles.length > 0,
    staleTime: 60_000,
    queryFn: async () => {
      const results = await Promise.all(
        singles.map(async (s) => {
          try {
            return (await getRunById(s.run_id)).data;
          } catch {
            return null;
          }
        }),
      );
      return results.filter((r) => r !== null);
    },
  });

  const groups = useMemo(() => {
    const details = detailsQ.data ?? [];
    const grouped = new Map<string, typeof details>();
    for (const d of details) {
      const sig = `${d.parameters.duration_minutes}|${d.parameters.incident_rate_per_hour}|${d.parameters.seed}`;
      const arr = grouped.get(sig) ?? [];
      arr.push(d);
      grouped.set(sig, arr);
    }
    return [...grouped.entries()]
      .map(([key, runs]) => ({
        key,
        baselines: runs.filter((r) => isBaseline(r.strategy)),
        aureons: runs.filter((r) => !isBaseline(r.strategy)),
      }))
      .filter((g) => g.baselines.length > 0 && g.aureons.length > 0);
  }, [detailsQ.data]);

  const [pairKey, setPairKey] = useState<string>('');
  const activeGroup = groups.find((g) => g.key === pairKey) ?? groups[0];

  const [baselineId, setBaselineId] = useState<string>('');
  const [aureonId, setAureonId] = useState<string>('');

  // Default each picker to the most recent run in the group.
  useEffect(() => {
    if (activeGroup && !baselineId && activeGroup.baselines.length > 0) {
      setBaselineId(activeGroup.baselines.at(-1)!.run_id);
    }
    if (activeGroup && !aureonId && activeGroup.aureons.length > 0) {
      setAureonId(activeGroup.aureons.at(-1)!.run_id);
    }
  }, [activeGroup, baselineId, aureonId, setBaselineId, setAureonId]);

  const baseline = activeGroup?.baselines.find((r) => r.run_id === baselineId) ?? activeGroup?.baselines.at(-1);
  const aureon = activeGroup?.aureons.find((r) => r.run_id === aureonId) ?? activeGroup?.aureons.at(-1);

  // Controlled benchmark runner (evaluator's identical-schedule comparison).
  const [benchParams, setBenchParams] = useState({ duration_minutes: 60, incident_rate_per_hour: 14, seed: 42 });
  const bench = useMutation({ mutationFn: compareStrategies });

  const [mode, setMode] = useState<Mode>('demo');

  return (
    <main className="flex min-h-dvh w-full flex-col bg-void lg:h-screen lg:w-screen lg:overflow-hidden">
      <header className="flex h-14 shrink-0 items-center justify-between gap-4 border-b border-hairline bg-panel-1 px-5">
        <div className="flex items-baseline gap-3">
          <span className="font-display text-base font-semibold tracking-tight">
            Aureon <span className="text-teal-core">·</span>{' '}
            <span className="hud-label align-middle text-[var(--color-text-secondary)]">
              Baseline vs Aureon
            </span>
          </span>
        </div>
        <div className="flex items-center gap-3">
          {/* Mode switcher */}
          <div className="flex rounded-md border border-hairline-strong p-0.5">
            {(
              [
                ['demo', 'SCENARIO DEMO'],
                ['evidence', 'ENGINE EVIDENCE'],
              ] as [Mode, string][]
            ).map(([value, label]) => (
              <button
                key={value}
                onClick={() => setMode(value)}
                className={`hud-label rounded px-3 py-1.5 !text-[9px] transition-colors ${
                  mode === value
                    ? 'bg-teal-core/15 text-teal-core'
                    : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <Link
            href="/command"
            className="hud-stamp rounded-md border border-hairline-strong px-3 py-1.5 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:border-white/20 transition-colors"
          >
            ← COMMAND
          </Link>
        </div>
      </header>

      {mode === 'demo' && (
        <div className="min-h-0 flex-1 overflow-y-auto">
          <ScenarioDemo />
        </div>
      )}

      {mode === 'evidence' && (
      <div className="grid min-h-0 flex-1 grid-cols-[24rem_1fr] gap-2 p-2">
        {/* Experiment setup */}
        <section className="flex min-h-0 flex-col gap-2 overflow-y-auto rounded-lg border border-hairline bg-panel-1/80 p-4 backdrop-blur-sm">
          <h2 className="hud-label text-[var(--color-text-secondary)]">Paired Replays</h2>

          {runsQ.isLoading && <p className="text-xs text-[var(--color-text-muted)]">Loading run archive…</p>}
          {!runsQ.isLoading && groups.length === 0 && (
            <p className="text-xs leading-relaxed text-[var(--color-text-muted)]">
              No comparable pairs yet. Run one{' '}
              <span className="text-crit-red">baseline</span> and one{' '}
              <span className="text-teal-core">Aureon</span> simulation with the
              same duration, rate, and seed — then diff them here.
            </p>
          )}

          {groups.length > 0 && (
            <>
              <label className="hud-stamp !text-[9px] block pt-2 text-[var(--color-text-muted)]">
                SCENARIO SIGNATURE (DURATION · RATE · SEED)
              </label>
              <select
                value={activeGroup?.key ?? ''}
                onChange={(e) => {
                  setPairKey(e.target.value);
                  setBaselineId('');
                  setAureonId('');
                }}
                className="tnum w-full rounded-md border border-hairline-strong bg-panel-2 px-2 py-1.5 font-mono text-xs"
              >
                {groups.map((g) => (
                  <option key={g.key} value={g.key}>
                    {signatureLabel(g.key)}
                  </option>
                ))}
              </select>

              <label className="hud-stamp !text-[9px] block pt-3 text-crit-red">BASELINE RUN</label>
              <select
                value={baseline?.run_id ?? ''}
                onChange={(e) => setBaselineId(e.target.value)}
                className="tnum w-full rounded-md border border-hairline-strong bg-panel-2 px-2 py-1.5 font-mono text-xs"
              >
                {activeGroup?.baselines.map((r) => (
                  <option key={r.run_id} value={r.run_id}>
                    {r.run_id} · {r.strategy}
                  </option>
                ))}
              </select>

              <label className="hud-stamp !text-[9px] block pt-3 text-teal-core">AUREON RUN</label>
              <select
                value={aureon?.run_id ?? ''}
                onChange={(e) => setAureonId(e.target.value)}
                className="tnum w-full rounded-md border border-hairline-strong bg-panel-2 px-2 py-1.5 font-mono text-xs"
              >
                {activeGroup?.aureons.map((r) => (
                  <option key={r.run_id} value={r.run_id}>
                    {r.run_id} · {r.strategy}
                  </option>
                ))}
              </select>
            </>
          )}

          <div className="mt-6 border-t border-hairline pt-4">
            <h2 className="hud-label text-[var(--color-text-secondary)]">Controlled Benchmark</h2>
            <p className="mt-1 text-[11px] leading-relaxed text-[var(--color-text-muted)]">
              Runs both strategies on a byte-identical generated schedule and
              persists the improvement report.
            </p>
            <div className="mt-3 grid grid-cols-3 gap-2">
              <NumField label="MIN" value={benchParams.duration_minutes} onChange={(v) => setBenchParams((p) => ({ ...p, duration_minutes: v }))} />
              <NumField label="RATE/H" value={benchParams.incident_rate_per_hour} onChange={(v) => setBenchParams((p) => ({ ...p, incident_rate_per_hour: v }))} />
              <NumField label="SEED" value={benchParams.seed} onChange={(v) => setBenchParams((p) => ({ ...p, seed: v }))} />
            </div>
            <button
              onClick={() => bench.mutate(benchParams)}
              disabled={bench.isPending}
              className="mt-3 w-full rounded-md bg-teal-core px-3 py-2 text-xs font-semibold text-black transition-all hover:brightness-110 disabled:opacity-50"
            >
              {bench.isPending ? 'RUNNING BOTH STRATEGIES…' : 'RUN BENCHMARK'}
            </button>
            {bench.isError && (
              <p className="mt-2 hud-stamp !text-[9px] text-crit-red">
                BENCHMARK FAILED — SEE SERVER LOGS
              </p>
            )}
          </div>
        </section>

        {/* Outcome delta */}
        <section className="flex min-h-0 flex-col gap-2 overflow-y-auto rounded-lg border border-hairline bg-panel-1/80 backdrop-blur-sm">
          <DeltaTable baseline={baseline ?? null} aureon={aureon ?? null} />
          {bench.data && <BenchmarkReport report={bench.data.data} />}
        </section>
      </div>
      )}
    </main>
  );
}

function isBaseline(strategy: string): boolean {
  return /nearest|baseline/i.test(strategy);
}

function signatureLabel(key: string): string {
  const [d, r, s] = key.split('|');
  return `${Number(d)}min · ${Number(r)}/h · seed ${s}`;
}

function NumField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <label className="block">
      <span className="hud-stamp !text-[9px] block text-[var(--color-text-muted)]">{label}</span>
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="tnum mt-1 w-full rounded-md border border-hairline-strong bg-panel-2 px-2 py-1.5 font-mono text-xs"
      />
    </label>
  );
}

function DeltaTable({
  baseline,
  aureon,
}: {
  baseline: { run_id: string; strategy: string; metrics: SimulationMetrics } | null;
  aureon: { run_id: string; strategy: string; metrics: SimulationMetrics } | null;
}) {
  if (!baseline || !aureon) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <p className="max-w-sm text-center text-xs leading-relaxed text-[var(--color-text-muted)]">
          Select a scenario signature with at least one baseline and one Aureon
          run to render the outcome delta.
        </p>
      </div>
    );
  }

  let improved = 0;
  let degraded = 0;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <header className="flex shrink-0 items-center justify-between border-b border-hairline px-4 py-2.5">
        <h2 className="hud-label text-[var(--color-text-secondary)]">Outcome Delta</h2>
        <span className="tnum truncate font-mono text-[10px] text-[var(--color-text-muted)]">
          {baseline.run_id} vs {aureon.run_id}
        </span>
      </header>
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-hairline">
            <th className="hud-stamp !text-[9px] px-4 py-2 font-normal text-[var(--color-text-muted)]">METRIC</th>
            <th className="hud-stamp !text-[9px] px-2 py-2 text-right font-normal text-crit-red">BASELINE</th>
            <th className="hud-stamp !text-[9px] px-2 py-2 text-right font-normal text-teal-core">AUREON</th>
            <th className="hud-stamp !text-[9px] px-4 py-2 text-right font-normal text-[var(--color-text-muted)]">Δ</th>
          </tr>
        </thead>
        <tbody>
          {ROWS.map((row) => {
            const b = row.get(baseline.metrics);
            const a = row.get(aureon.metrics);
            const delta = a - b;
            let tone = 'text-[var(--color-text-muted)]';
            if (row.lowerBetter !== null && Math.abs(delta) > 1e-9) {
              const better = row.lowerBetter ? delta < 0 : delta > 0;
              tone = better ? 'text-teal-core' : 'text-crit-red';
              if (better) improved++;
              else degraded++;
            }
            return (
              <tr key={row.label} className="border-b border-[color:var(--color-hairline)]">
                <td className="px-4 py-2 text-xs text-[var(--color-text-secondary)]">{row.label}</td>
                <td className="tnum px-2 py-2 text-right font-mono text-xs">{fmt(b)}{row.unit}</td>
                <td className="tnum px-2 py-2 text-right font-mono text-xs">{fmt(a)}{row.unit}</td>
                <td className={`tnum px-4 py-2 text-right font-mono text-xs ${tone}`}>
                  {row.lowerBetter === null ? '—' : `${delta >= 0 ? '+' : ''}${fmt(delta)}${row.unit}`}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <footer className="mt-auto flex items-center justify-between px-4 py-3">
        <span className="hud-stamp !text-[9px] text-[var(--color-text-muted)]">
          ENGINE-REPORTED VALUES ONLY
        </span>
        {(improved > 0 || degraded > 0) && (
          <span className="hud-stamp !text-[10px]">
            <span className="text-teal-core">{improved} IMPROVED</span>
            {' · '}
            <span className={degraded > 0 ? 'text-crit-red' : 'text-[var(--color-text-muted)]'}>
              {degraded} DEGRADED
            </span>
          </span>
        )}
      </footer>
    </div>
  );
}

function BenchmarkReport({
  report,
}: {
  report: {
    experiment_meta?: { duration_minutes: number; total_incidents: number };
    improvements?: ComparisonImprovements | Record<string, number>;
    comparison_id?: string;
  };
}) {
  if (!report.improvements) return null;
  const entries = Object.entries(report.improvements);
  return (
    <div className="border-t border-hairline p-4">
      <header className="flex items-center justify-between">
        <h2 className="hud-label text-[var(--color-text-secondary)]">
          Controlled Benchmark Report
        </h2>
        <span className="tnum font-mono text-[10px] text-[var(--color-text-muted)]">
          {report.comparison_id}
        </span>
      </header>
      <div className="mt-3 grid grid-cols-2 gap-x-8 gap-y-2 md:grid-cols-3">
        {entries.map(([k, v]) => (
          <div key={k} className="flex items-baseline justify-between gap-2">
            <span className="truncate text-[11px] text-[var(--color-text-secondary)]">
              {k.replace(/_/g, ' ').toUpperCase()}
            </span>
            <span className={`tnum shrink-0 font-mono text-xs ${v >= 0 ? 'text-teal-core' : 'text-crit-red'}`}>
              {v >= 0 ? '+' : ''}{v}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function fmt(v: number): string {
  if (!Number.isFinite(v)) return '—';
  return Number.isInteger(v) ? String(v) : v.toFixed(1);
}
