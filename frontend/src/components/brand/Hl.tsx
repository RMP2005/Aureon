import type { ReactNode } from 'react';

/**
 * Semantic keyword highlight (refinement pass).
 *
 * Usage is contract-bound — the tone must match the meaning:
 *   reason → AI reasoning / decisions vocabulary (violet)
 *   crit   → danger / emergency vocabulary (red)
 *
 * Exact words only, never sentences. Direction: color → white.
 */
export default function Hl({
  kind,
  children,
}: {
  kind: 'reason' | 'crit';
  children: ReactNode;
}) {
  const cls = kind === 'reason' ? 'hl-reason' : 'hl-crit';
  return <span className={`hl ${cls}`}>{children}</span>;
}
