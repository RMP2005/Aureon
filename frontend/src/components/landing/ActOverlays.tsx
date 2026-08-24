'use client';

import type { ReactNode } from 'react';
import { ACTS, type ActDef, type HighlightKind } from '@/lib/landing/progress';
import Hl from '@/components/brand/Hl';
import LandingCTAs from './LandingCTAs';

/**
 * DOM copy layer for the landing journey (Phase 10C).
 * Each act's text lives inside its scroll band; GSAP (in the parent page)
 * fades them through their windows. The final act carries the CTAs.
 *
 * Phase 11-refinement: responsive clamp hardening (no overflow at any
 * viewport) and semantic keyword highlights.
 */
export default function ActOverlays() {
  return (
    <>
      {ACTS.map((act) => {
        const isLast = act.id === 'invitation';
        const align = isLast ? 'items-center text-center' : 'items-start';
        return (
          <section
            key={act.id}
            data-act={act.id}
            className={`relative flex ${align} pointer-events-none`}
            style={{ height: `${actSectionVh(act)}vh` }}
          >
            <div className="w-full max-w-6xl mx-auto px-6 md:px-8 flex flex-col justify-center">
              <p
                className="hud-stamp text-teal-core mb-5"
                data-act-copy={act.id}
              >
                {act.kicker}
              </p>
              <h2
                className="font-display font-semibold tracking-tight leading-[1.04] text-balance break-words text-[clamp(1.9rem,4.6vw,4rem)] max-w-3xl"
                data-act-copy={act.id}
              >
                {renderWithHighlights(act.title, act.highlights)}
              </h2>
              {act.body && (
                <p
                  className="mt-7 max-w-xl text-base md:text-lg text-[var(--color-text-secondary)] leading-relaxed"
                  data-act-copy={act.id}
                >
                  {renderWithHighlights(act.body, act.highlights)}
                </p>
              )}
              {isLast && (
                <div className="mt-12 flex w-full justify-center">
                  <LandingCTAs />
                </div>
              )}
            </div>
          </section>
        );
      })}
    </>
  );
}

/**
 * Wrap contract-bound phrases in semantic ink gradients. Applied to
 * whichever field contains the phrase (title or body). Phrases are
 * matched case-insensitively; unmatched text renders plain.
 */
function renderWithHighlights(
  text: string,
  highlights: ActDef['highlights'],
): ReactNode {
  if (!highlights?.length) return text;
  type Seg = { text: string; kind: HighlightKind | null };
  const segments: Seg[] = [{ text, kind: null }];
  for (const [phrase, kind] of highlights) {
    for (let i = 0; i < segments.length; ) {
      const seg = segments[i];
      if (seg.kind !== null) {
        i += 1;
        continue;
      }
      const idx = seg.text.toLowerCase().indexOf(phrase.toLowerCase());
      if (idx === -1) {
        i += 1;
        continue;
      }
      const before = seg.text.slice(0, idx);
      const after = seg.text.slice(idx + phrase.length);
      const parts: Seg[] = [
        ...(before ? [{ text: before, kind: null }] : []),
        { text: seg.text.slice(idx, idx + phrase.length), kind },
        ...(after ? [{ text: after, kind: null }] : []),
      ];
      const inserted = parts.length;
      segments.splice(i, 1, ...parts);
      i += inserted;
    }
  }
  return segments.map((seg, i) =>
    seg.kind ? (
      <Hl key={i} kind={seg.kind}>
        {seg.text}
      </Hl>
    ) : (
      <span key={i}>{seg.text}</span>
    ),
  );
}

/** Distribute section heights proportionally to each act's progress span. */
function actSectionVh(act: (typeof ACTS)[number]): number {
  const span = act.range[1] - act.range[0];
  // Total journey ≈ 520vh of scrollable content (plus 100vh sticky viewport).
  return Math.round(span * 620);
}
