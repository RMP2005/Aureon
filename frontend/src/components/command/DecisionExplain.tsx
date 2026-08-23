'use client';

import { useState } from 'react';
import type { DispatchDecisionDetails } from '@/lib/api';
import { parseDecision } from '@/lib/command/rationale-parser';

/**
 * "Explain This Decision" (Phase 10F-1).
 *
 * Renders ONLY strategy-published engine evidence: the detected mode,
 * factors that scored, and every evaluated alternative with its outcome
 * (selected vs rejected). The rationale sentence is the engine's own.
 * When no structured evidence exists yet, the caller shows a pending note —
 * nothing is ever inferred or fabricated here.
 */

export interface ExplainContext {
  callsign?: string;
  incidentId?: string;
  rationale?: string;
}

export default function DecisionExplain({
  details,
  context,
  compact = false,
}: {
  details: DispatchDecisionDetails;
  context?: ExplainContext;
  compact?: boolean;
}) {
  const parsed = parseDecision(details);

  // Alternatives: selected first, rejected after — order is presentation
  // only; every row's data comes verbatim from the engine metadata.
  const selected = parsed.candidateRows.filter((r) => r.accent);
  const rejected = parsed.candidateRows.filter((r) => !r.accent);
  const alternatives = [...selected, ...rejected];

  return (
    <div
      className={`rounded border border-hairline bg-panel-1/60 ${compact ? 'p-2' : 'p-3'} space-y-2.5`}
      data-explain-panel
    >
      {/* Header — what was decided */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="hud-stamp !text-[9px] rounded-sm bg-teal-core/15 px-1.5 py-0.5 text-teal-core">
          DECISION · {context?.callsign ?? 'UNIT'}
        </span>
        {parsed.mode && (
          <span className="hud-stamp !text-[9px] rounded-sm bg-violet-intel/15 px-1.5 py-0.5 text-violet-intel">
            MODE · {parsed.mode.replace(/_/g, ' ').toUpperCase()}
          </span>
        )}
      </div>

      {/* The engine's own words */}
      {context?.rationale && (
        <blockquote className={`border-l-2 border-teal-core/50 pl-2 text-xs leading-snug text-[var(--color-text-primary)] ${compact ? '' : 'text-[13px]'}`}>
          “{context.rationale}”
        </blockquote>
      )}

      {/* Factors considered */}
      {(parsed.coverageScore !== undefined || parsed.genericRows.length > 0) && (
        <section>
          <SectionTitle>FACTORS CONSIDERED</SectionTitle>
          <div className="mt-1 space-y-1">
            {parsed.coverageScore !== undefined && (
              <FactorRow
                label="COVERAGE SCORE"
                value={parsed.coverageScore.toFixed(2)}
              />
            )}
            {parsed.genericRows.map((r) => (
              <FactorRow key={r.label} label={r.label} value={r.value} />
            ))}
          </div>
        </section>
      )}

      {/* Tradeoffs / override reasoning */}
      {parsed.overrideReason && (
        <section>
          <SectionTitle>TRADEOFF</SectionTitle>
          <p className="mt-1 rounded-sm bg-amber-warn/10 px-2 py-1.5 text-[11px] leading-snug text-amber-warn">
            {parsed.overrideReason}
          </p>
        </section>
      )}

      {/* Selected vs rejected alternatives */}
      {alternatives.length > 0 && (
        <section>
          <SectionTitle>
            ALTERNATIVES · {selected.length} SELECTED / {rejected.length} REJECTED
          </SectionTitle>
          <ul className="mt-1 space-y-0.5">
            {alternatives.map((r, i) => (
              <li
                key={`${r.label}-${i}`}
                className={`flex items-baseline justify-between gap-2 text-[11px] leading-tight ${
                  r.accent ? 'text-teal-core' : 'text-[var(--color-text-muted)]'
                }`}
              >
                <span className="hud-stamp !text-[8px] shrink-0 w-[68px]">
                  {r.accent ? '▸ SELECTED' : 'REJECTED'}
                </span>
                <span className={`tnum flex-1 text-right font-mono ${r.accent ? 'font-semibold' : ''}`}>
                  {r.value}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {alternatives.length === 0 &&
        parsed.genericRows.length === 0 &&
        !parsed.mode &&
        !parsed.overrideReason && (
          <p className="hud-stamp !text-[9px] text-[var(--color-text-muted)]">
            NO STRUCTURED EVIDENCE PUBLISHED FOR THIS DECISION — RATIONALE TEXT ONLY
          </p>
        )}
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <p className="hud-stamp !text-[8px] text-[var(--color-text-muted)]">{children}</p>
  );
}

function FactorRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-2 text-[11px] leading-tight">
      <span className="hud-stamp !text-[8px] shrink-0 text-[var(--color-text-muted)]">
        {label}
      </span>
      <span className="tnum font-mono text-right">{value}</span>
    </div>
  );
}

/** Pending-state hint for decisions whose evidence isn't published yet. */
export function ExplainButton({
  disabled,
  open,
  onClick,
  label,
}: {
  disabled?: boolean;
  /** Whether the associated explain panel is currently expanded. */
  open?: boolean;
  onClick: () => void;
  /** Dense contexts (ledger rows) use a shorter stamp. */
  label?: string;
}) {
  return (
    <button
      title={
        disabled
          ? 'Structured evidence publishes at run completion'
          : 'Show factors, tradeoffs and alternatives from engine evidence'
      }
      onClick={onClick}
      disabled={disabled}
      className={`hud-stamp !text-[9px] rounded-sm border px-1.5 py-0.5 transition-colors ${
        disabled
          ? 'cursor-not-allowed border-hairline text-[var(--color-text-muted)] opacity-60'
          : 'border-violet-intel/40 text-violet-intel hover:bg-violet-intel/10'
      }`}
    >
      {disabled
        ? '[ EVIDENCE AT DEBRIEF ]'
        : open
          ? '[ HIDE DECISION ]'
          : (label ?? '[ EXPLAIN THIS DECISION ]')}
    </button>
  );
}
