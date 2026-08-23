'use client';

import type { SimulationRunResult, RunProgress } from '@/lib/api';

/**
 * Metrics strip (Phase 10D).
 * During the run: live operational counters. After completion: outcome KPIs
 * from the persisted result. Both are engine-reported values only.
 */
export default function MetricsStrip({
  progress,
  result,
}: {
  progress: RunProgress | null;
  result: SimulationRunResult | null;
}) {
  if (result) {
    const m = result.metrics;
    return (
      <div className="flex h-full items-stretch divide-x divide-[color:var(--color-hairline)] overflow-x-auto">
        <StripCell label="STRATEGY" value={result.strategy.replace(/\s*\(.*\)/, '')} />
        <StripCell label="MEAN RT" value={`${m.response_times_minutes.mean.toFixed(1)} min`} />
        <StripCell label="P90 RT" value={`${m.response_times_minutes.p90.toFixed(1)} min`} />
        <StripCell
          label="CRIT COMPLIANCE"
          value={`${m.critical_cases.target_compliance_percent.toFixed(0)}%`}
          accent={m.critical_cases.target_compliance_percent >= 80 ? 'teal' : 'amber'}
        />
        <StripCell label="CAPABILITY MATCH" value={`${m.clinical_quality.capability_match_percent.toFixed(0)}%`} />
        <StripCell label="COMPLETED" value={String(m.total_incidents_completed)} />
        <StripCell
          label="UNSERVICED"
          value={String(m.unserviced_incidents_count)}
          accent={m.unserviced_incidents_count > 0 ? 'crit' : undefined}
        />
        <StripCell label="FLEET UTIL" value={`${m.operations.fleet_utilization_percent.toFixed(0)}%`} />
      </div>
    );
  }

  if (progress) {
    return (
      <div className="flex h-full items-stretch divide-x divide-[color:var(--color-hairline)] overflow-x-auto">
        <StripCell label="STATUS" value={progress.status.toUpperCase()} accent={progress.status === 'running' ? 'teal' : undefined} />
        <StripCell label="PROGRESS" value={`${progress.progress_percent.toFixed(0)}%`} />
        <StripCell label="INCIDENTS REPORTED" value={String(progress.reported_incidents)} />
        <StripCell label="RESOLVED" value={String(progress.completed_incidents)} />
        <StripCell label="UNITS ENGAGED" value={String(progress.active_ambulances)} />
        <StripCell label="UNITS AVAILABLE" value={String(progress.available_ambulances)} />
      </div>
    );
  }

  return (
    <div className="flex h-full items-center justify-center">
      <p className="hud-stamp text-[var(--color-text-muted)]">
        NO ACTIVE RUN — LAUNCH A SIMULATION TO POPULATE OPERATIONS DATA
      </p>
    </div>
  );
}

function StripCell({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: 'teal' | 'amber' | 'crit';
}) {
  const tone =
    accent === 'teal'
      ? 'text-teal-core'
      : accent === 'amber'
        ? 'text-amber-warn'
        : accent === 'crit'
          ? 'text-crit-red'
          : '';
  return (
    <div className="flex min-w-[110px] flex-col justify-center px-4 py-2 leading-tight">
      <p className="hud-stamp !text-[9px] whitespace-nowrap text-[var(--color-text-muted)]">
        {label}
      </p>
      <p className={`tnum mt-0.5 truncate font-mono text-sm font-medium ${tone}`}>
        {value}
      </p>
    </div>
  );
}
