'use client';

import { useLedgerStore } from '@/lib/command/ledger';
import { EmptyNote, PanelFrame } from './primitives';

const KIND_STYLE: Record<string, { dot: string; label: string }> = {
  INCIDENT: { dot: 'bg-crit-red', label: 'text-crit-red' },
  DISPATCH: { dot: 'bg-teal-core', label: 'text-teal-core' },
  RESOLVED: { dot: 'bg-violet-intel', label: 'text-violet-intel' },
  LOG: { dot: 'bg-[var(--color-text-muted)]', label: 'text-[var(--color-text-muted)]' },
};

/**
 * Decision Ledger (Phase 10D).
 * LIVE entries are observed snapshot deltas; DISPATCH_LOG entries carry the
 * engine's own rationale text verbatim after run completion.
 */
export default function DecisionLedger() {
  const events = useLedgerStore((s) => s.events);

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
            return (
              <li key={e.id} className="flex items-start gap-2.5 px-3 py-2">
                <span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${style.dot}`} />
                <div className="min-w-0 flex-1">
                  <p className="text-xs leading-snug">{e.text}</p>
                  <p className="mt-0.5 hud-stamp !text-[9px] text-[var(--color-text-muted)]">
                    T+{formatSimSec(e.simSec)} ·{' '}
                    <span className={style.label}>
                      {e.source === 'LIVE' ? e.kind : 'ENGINE LOG'}
                    </span>
                    {e.severity && ` · ${e.severity.toUpperCase()}`}
                  </p>
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </PanelFrame>
  );
}

function formatSimSec(sec: number): string {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}
