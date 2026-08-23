import type { ReactNode } from 'react';

/**
 * Semantic keyword highlight (Phase 11-refinement).
 *
 * Usage is contract-bound — the tone must match the meaning:
 *   reason   → AI reasoning, prediction, decisions, intelligence
 *   evidence → measured / audited / validated facts
 *   crit     → incidents, emergency response, danger (sparing!)
 *
 * These are ink gradients on words only. No decorative gradients.
 */
export default function Hl({
  kind,
  children,
}: {
  kind: 'reason' | 'evidence' | 'crit';
  children: ReactNode;
}) {
  const cls =
    kind === 'reason' ? 'hl-reason' : kind === 'evidence' ? 'hl-evidence' : 'hl-crit';
  return <span className={`hl ${cls}`}>{children}</span>;
}
