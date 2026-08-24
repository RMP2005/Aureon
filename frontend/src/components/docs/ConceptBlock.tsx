import type { ReactNode } from 'react';

/**
 * ConceptBlock — documentation primitive (Phase 11F).
 *
 * Short-form concept explanation: a stamped title, one or two sentences,
 * optional keyword highlights via children. No cards-within-cards; the
 * hairline left rail carries the structure.
 */
export default function ConceptBlock({
  title,
  kind = 'system',
  children,
}: {
  title: string;
  /** Stamp color semantics: teal=system, violet=intelligence, titanium=evidence, red=critical. */
  kind?: 'system' | 'intelligence' | 'evidence' | 'critical';
  children: ReactNode;
}) {
  const tone =
    kind === 'intelligence'
      ? 'text-violet-intel'
      : kind === 'evidence'
        ? 'text-titanium'
        : kind === 'critical'
          ? 'text-crit-red'
          : 'text-teal-core';
  return (
    <div className="border-l border-hairline-strong pl-5 py-1">
      <p className={`hud-stamp !text-[10px] mb-2 ${tone}`}>{title}</p>
      <div className="max-w-xl text-sm leading-relaxed text-[var(--color-text-secondary)]">
        {children}
      </div>
    </div>
  );
}
