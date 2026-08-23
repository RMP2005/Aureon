/**
 * Landing scroll progress (Phase 10C).
 *
 * Module-level singleton written by GSAP ScrollTrigger's onUpdate and read
 * every frame inside the R3F render loop. Deliberately NOT React state —
 * scroll drives ~120 updates/sec and none of them may re-render the tree.
 */

/** Total scrollable length expressed in viewport-heights of content. */
export const JOURNEY_VH = 520;

export type HighlightKind = 'reason' | 'crit';

export interface ActDef {
  id: string;
  /** Progress range [start, end]. */
  range: [number, number];
  kicker: string;
  title: string;
  body: string;
  /**
   * Exact phrases to render as semantic ink gradients. Contract-bound and
   * intentionally sparse: ONLY explicitly requested words may appear here
   * (refinement pass: 'wrong' → crit in Act III, 'words' → reason in
   * Act IV). Matched case-insensitively against kicker/title/body.
   */
  highlights?: [phrase: string, kind: HighlightKind][];
}

export const ACTS: ActDef[] = [
  {
    id: 'awakening',
    range: [0.0, 0.2],
    kicker: 'Act I — Awakening',
    title: 'A city of twelve million bets on minutes.',
    body: 'Before dawn, before the first siren, Bengaluru is already moving. This is the network that keeps it alive.',
  },
  {
    id: 'materialize',
    range: [0.2, 0.45],
    kicker: 'Act II — Materialization',
    title: 'One living network.',
    body: 'Arteries and intersections resolved into a single navigable organism — the digital twin of a metropolis.',
  },
  {
    id: 'pulse',
    range: [0.45, 0.68],
    kicker: 'Act III — The Pulse',
    title: 'Hesitation is the only wrong answer.',
    body: 'An emergency breaks the pattern. Fourteen units redistribute across the grid before the first call ends.',
    highlights: [['wrong', 'crit']],
  },
  {
    id: 'intelligence',
    range: [0.68, 0.88],
    kicker: 'Act IV — The Intelligence',
    title: 'Decided in milliseconds. Explained in words.',
    body: 'Aureon weighs traffic, capability and outcome — then shows its reasoning. Accountable intelligence, awake at city scale.',
    highlights: [['words', 'reason']],
  },
  {
    id: 'invitation',
    range: [0.88, 1.0],
    kicker: 'Epilogue',
    title: 'Enter the twin.',
    body: '',
  },
];

const store = { progress: 0 };

export function setLandingProgress(p: number): void {
  store.progress = Math.min(1, Math.max(0, p));
}

export function getLandingProgress(): number {
  return store.progress;
}
