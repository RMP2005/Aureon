'use client';

import { useEffect, useRef, useState } from 'react';
import { useLedgerStore, type LedgerEvent } from '@/lib/command/ledger';
import { parseDecision } from '@/lib/command/rationale-parser';
import { EmptyNote, PanelFrame } from './primitives';

const KIND_STYLE: Record<string, { dot: string; label: string }> = {
  INCIDENT: { dot: 'bg-crit-red', label: 'text-crit-red' },
  DISPATCH: { dot: 'bg-teal-core', label: 'text-teal-core' },
  RESOLVED: { dot: 'bg-violet-intel', label: 'text-violet-intel' },
  LOG: { dot: 'bg-[var(--color-text-muted)]', label: 'text-[var(--color-text-muted)]' },
};

/**
 * Decision Ledger (Phase 10D, evidence expansion added in 10E-2).
 * LIVE entries are observed snapshot deltas; DISPATCH_LOG entries carry the
 * engine's own rationale text verbatim after run completion; REPLAY entries
 * stream in as the playhead crosses recorded events (Phase 10E-1).
 * Entries with structured decision metadata expand into evidence cards.
 */
export default function DecisionLedger() {
  const events = useLedgerStore((s) => s.events);
  const highlightId = useLedgerStore((s) => s.highlightId);
  const setHighlight = useLedgerStore((s) => s.setHighlight);
  const highlightRef = useRef<HTMLLIElement | null>(null);

  // Evidence link: a timeline-marker click flashes its ledger entry.
  useEffect(() => {
    if (!highlightId) return;
    highlightRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    const t = setTimeout(() => setHighlight(null), 2_400);
    return () => clearTimeout(t);
  }, [highlightId, setHighlight]);

  return (
    <PanelFrame
      title="Decision Ledger"
      right={
        <span className="hud-stamp !text-[9px] text-[var(--color-text-muted)]">
          OBSERVED · NOT PREDICTED
        </span>
      }
    >
      {events.length === 0 ? (
        <EmptyNote>
          Awaiting operational events — the ledger records only what the
          engine actually did.
        </EmptyNote>
      ) : (
        <ol className="divide-y divide-[color:var(--color-hairline)]">
          {events.map((e) => {
            const style = KIND_STYLE[e.kind] ?? KIND_STYLE.LOG;
            const highlighted = e.id === highlightId;
            return (
              <li
                key={e.id}
                ref={highlighted ? highlightRef : undefined}
                className={`px-3 py-2 transition-colors duration-300 ${
                  highlighted ? 'bg-teal-core/10 ring-1 ring-inset ring-teal-core/40' : ''
                }`}
              >
                <LedgerRow event={e} dot={style.dot} label={style.label} />
              </li>
            );
          })}
        </ol>
      )}
    </PanelFrame>
  );
}

function LedgerRow({
  event,
  dot,
  label,
}: {
  event: LedgerEvent;
  dot: string;
  label: string;
}) {
  const hasEvidence = Boolean(event.details && Object.keys(event.details).length > 0);
  const [open, setOpen] = useState(false);

  return (
    <div className="flex items-start gap-2.5">
      <span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${dot}`} />
      <div className="min-w-0 flex-1">
        <p className="text-xs leading-snug">{event.text}</p>
        <div className="mt-0.5 flex items-center gap-2">
          <p className="hud-stamp !text-[9px] text-[var(--color-text-muted)]">
            T+{formatSimSec(event.simSec)} ·{' '}
            <span className={label}>{sourceLabel(event)}</span>
            {event.severity && ` · ${event.severity.toUpperCase()}`}
          </p>
          {hasEvidence && (
            <button
              onClick={() => setOpen((o) => !o)}
              className="hud-stamp !text-[9px] text-violet-intel hover:text-[var(--color-text-primary)] transition-colors"
            >
              {open ? '[ HIDE EVIDENCE ]' : '[ EVIDENCE ]'}
            </button>
          )}
        </div>
        {hasEvidence && open && <EvidenceCard details={event.details!} />}
      </div>
    </div>
  );
}

/**
 * Structured evidence — every line is strategy-published metadata rendered
 * verbatim; the parser only formats, never invents.
 */
function EvidenceCard({ details }: { details: NonNullable<LedgerEvent['details']> }) {
  const parsed = parseDecision(details);

  return (
    <div className="mt-1.5 rounded border border-hairline bg-panel-1/60 p-2 space-y-1">
      {(parsed.mode || parsed.coverageScore !== undefined) && (
        <div className="flex items-center gap-2">
          {parsed.mode && (
            <span className="hud-stamp !text-[9px] rounded-sm bg-violet-intel/15 px-1.5 py-0.5 text-violet-intel">
              MODE · {parsed.mode.replace(/_/g, ' ').toUpperCase()}
            </span>
          )}
          {parsed.coverageScore !== undefined && (
            <span className="hud-stamp !text-[9px] text-[var(--color-text-muted)]">
              COVERAGE {parsed.coverageScore.toFixed(2)}
            </span>
          )}
        </div>
      )}

      {parsed.candidateRows.length > 0 && (
        <EvidenceSection title="UNITS EVALUATED" rows={parsed.candidateRows} />
      )}
      {parsed.overrideReason && (
        <p className="text-[11px] leading-snug text-amber-warn">
          OVERRIDE — {parsed.overrideReason}
        </p>
      )}
      {parsed.genericRows.length > 0 && (
        <EvidenceSection title="CONTEXT" rows={parsed.genericRows} />
      )}
    </div>
  );
}

function EvidenceSection({
  title,
  rows,
}: {
  title: string;
  rows: { label: string; value: string; accent?: boolean }[];
}) {
  return (
    <div>
      <p className="hud-stamp !text-[8px] text-[var(--color-text-muted)]">{title}</p>
      <ul className="mt-0.5 space-y-0.5">
        {rows.map((r, i) => (
          <li
            key={`${r.label}-${i}`}
            className={`flex items-baseline justify-between gap-2 text-[11px] leading-tight ${
              r.accent ? 'text-teal-core' : 'text-[var(--color-text-secondary)]'
            }`}
          >
            <span className="hud-stamp !text-[8px] shrink-0 text-[var(--color-text-muted)]">
              {r.label}
            </span>
            <span className={`font-mono tabular text-right ${r.accent ? 'font-semibold' : ''}`}>
              {r.value}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function sourceLabel(e: { source: string; kind: string }): string {
  if (e.source === 'LIVE') return e.kind;
  if (e.source === 'REPLAY') return `${e.kind} · REPLAY`;
  return 'ENGINE LOG';
}

function formatSimSec(sec: number): string {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}
