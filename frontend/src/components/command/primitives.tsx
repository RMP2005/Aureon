'use client';

/**
 * Command-center primitives (Phase 10D).
 * Dense chrome: hairline borders, HUD labels, color = state only.
 */

export function PanelFrame({
  title,
  right,
  children,
  className = '',
  bodyClassName = '',
}: {
  title: string;
  right?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section
      className={`flex min-h-0 flex-col rounded-lg border border-hairline bg-panel-1/80 backdrop-blur-sm ${className}`}
    >
      <header className="flex shrink-0 items-center justify-between border-b border-hairline px-3 py-2">
        <h2 className="hud-label text-[var(--color-text-secondary)]">{title}</h2>
        {right}
      </header>
      <div className={`min-h-0 flex-1 overflow-y-auto ${bodyClassName}`}>
        {children}
      </div>
    </section>
  );
}

const CHIP_TONES: Record<string, string> = {
  // Fleet states
  idle_at_base: 'text-[var(--color-text-muted)] border-hairline-strong',
  dispatched_to_scene: 'text-teal-core border-teal-core/30',
  on_scene_triage: 'text-amber-warn border-amber-warn/30',
  transporting_hospital: 'text-violet-intel border-violet-intel/30',
  at_hospital_handover: 'text-violet-intel border-violet-intel/30',
  returning_to_base: 'text-[var(--color-text-secondary)] border-hairline-strong',
  // Incident severities
  critical: 'text-crit-red border-crit-red/40 bg-crit-red/5',
  high: 'text-orange-high border-orange-high/30',
  medium: 'text-amber-warn border-amber-warn/30',
  low: 'text-[var(--color-text-secondary)] border-hairline-strong',
};

export function StatusChip({ value }: { value: string }) {
  const tone = CHIP_TONES[value] ?? 'text-[var(--color-text-secondary)] border-hairline-strong';
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-sm border px-1.5 py-0.5 hud-stamp !text-[10px] !tracking-[0.05em] ${tone}`}
    >
      {value.replace(/_/g, ' ')}
    </span>
  );
}

/** Occupancy bar — teal→amber→crit strictly by load thresholds. */
export function OccupancyBar({
  used,
  total,
}: {
  used: number;
  total: number;
}) {
  const pct = total > 0 ? Math.round((used / total) * 100) : 0;
  const tone =
    pct >= 90 ? 'bg-crit-red' : pct >= 70 ? 'bg-amber-warn' : 'bg-teal-core';
  return (
    <div className="flex items-center gap-2">
      <div className="h-1 w-full overflow-hidden rounded-full bg-white/8">
        <div className={`h-full rounded-full ${tone}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="tnum w-11 shrink-0 text-right font-mono text-[10px] text-[var(--color-text-muted)]">
        {used}/{total}
      </span>
    </div>
  );
}

export function EmptyNote({ children }: { children: React.ReactNode }) {
  return (
    <p className="px-3 py-4 text-center text-xs text-[var(--color-text-muted)]">
      {children}
    </p>
  );
}
