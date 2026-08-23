'use client';

import type { SimulationRunResult } from '@/lib/api';

/**
 * Typed, grouped metrics panel (Phase 10A).
 * Replaces the naive Object.entries renderer that printed nested
 * stat objects as "[object Object]". Every field is addressed by name,
 * so backend contract changes surface at compile time.
 */
export default function MetricsPanel({ result }: { result: SimulationRunResult }) {
  const m = result.metrics;
  const rt = m.response_times_minutes;

  return (
    <section className="glass-panel rounded-2xl p-6 mb-6">
      <div className="flex items-baseline justify-between mb-5">
        <h2 className="font-display text-lg font-semibold">Run Result</h2>
        <span className="hud-stamp text-[var(--color-text-muted)]">
          {result.strategy.toUpperCase()} · SEED {result.parameters.seed}
        </span>
      </div>

      {/* Headline KPIs — the four numbers that decide a strategy */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        <Kpi label="Mean Response" value={rt.mean.toFixed(1)} unit="min" />
        <Kpi label="P90 Response" value={rt.p90.toFixed(1)} unit="min" />
        <Kpi
          label="Critical Compliance"
          value={m.critical_cases.target_compliance_percent.toFixed(0)}
          unit="%"
          accent={m.critical_cases.target_compliance_percent >= 80 ? 'teal' : 'amber'}
        />
        <Kpi
          label="Capability Match"
          value={m.clinical_quality.capability_match_percent.toFixed(0)}
          unit="%"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-6">
        <Group title="Incidents">
          <Row label="Reported" value={m.total_incidents_reported} />
          <Row label="Dispatched" value={m.total_incidents_dispatched} />
          <Row label="Completed" value={m.total_incidents_completed} />
          <Row
            label="Unserviced"
            value={m.unserviced_incidents_count}
            warn={m.unserviced_incidents_count > 0}
          />
        </Group>

        <Group title="Response Times">
          <Row label="Median" value={rt.median.toFixed(1)} unit="min" />
          <Row label="P95" value={rt.p95.toFixed(1)} unit="min" />
          <Row
            label="Min / Max"
            value={`${rt.min.toFixed(1)} / ${rt.max.toFixed(1)}`}
            unit="min"
          />
        </Group>

        <Group title="Critical Cases">
          <Row label="Count" value={m.critical_cases.count} />
          <Row
            label="Mean response"
            value={m.critical_cases.mean_response_time_min.toFixed(1)}
            unit="min"
          />
          <Row
            label="Target compliance"
            value={m.critical_cases.target_compliance_percent.toFixed(0)}
            unit="%"
          />
        </Group>

        <Group title="Clinical Quality">
          <Row
            label="Capability match"
            value={m.clinical_quality.capability_match_percent.toFixed(0)}
            unit="%"
          />
          <Row
            label="Hospital suitability"
            value={m.clinical_quality.mean_hospital_suitability_score.toFixed(2)}
          />
        </Group>

        <Group title="Operations">
          <Row
            label="Fleet distance"
            value={m.operations.total_fleet_distance_km.toFixed(1)}
            unit="km"
          />
          <Row
            label="Fleet utilization"
            value={m.operations.fleet_utilization_percent.toFixed(0)}
            unit="%"
          />
          <Row
            label="Missions / ambulance"
            value={m.operations.avg_missions_per_ambulance.toFixed(1)}
          />
        </Group>
      </div>
    </section>
  );
}

function Kpi({
  label,
  value,
  unit,
  accent = 'default',
}: {
  label: string;
  value: string;
  unit?: string;
  accent?: 'default' | 'teal' | 'amber';
}) {
  const accentClass =
    accent === 'teal'
      ? 'text-teal-core'
      : accent === 'amber'
        ? 'text-amber-warn'
        : 'text-[var(--color-text-primary)]';
  return (
    <div className="rounded-xl border border-hairline bg-panel-1 p-4">
      <p className="hud-label text-[var(--color-text-muted)] mb-1">{label}</p>
      <p className={`font-mono tabular text-2xl font-semibold ${accentClass}`}>
        {value}
        {unit && (
          <span className="text-sm text-[var(--color-text-muted)] ml-1">{unit}</span>
        )}
      </p>
    </div>
  );
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="hud-label text-[var(--color-text-muted)] mb-2">{title}</p>
      <dl>{children}</dl>
    </div>
  );
}

function Row({
  label,
  value,
  unit,
  warn = false,
}: {
  label: string;
  value: number | string;
  unit?: string;
  warn?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between border-b border-hairline py-1.5 last:border-b-0">
      <dt className="text-sm text-[var(--color-text-secondary)]">{label}</dt>
      <dd
        className={`font-mono tabular text-sm ${warn ? 'text-crit-red' : 'text-[var(--color-text-primary)]'}`}
      >
        {value}
        {unit && (
          <span className="text-xs text-[var(--color-text-muted)] ml-1">{unit}</span>
        )}
      </dd>
    </div>
  );
}
