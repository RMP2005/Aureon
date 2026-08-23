import type { DispatchDecisionDetails } from '@/lib/api';

/**
 * Rationale parser (Phase 10E-2).
 *
 * Converts the strategy-published decision metadata into ordered,
 * human-readable evidence rows. Nothing here fabricates content: unknown
 * keys fall through to a generic label/value formatter, and when no
 * structured details exist the caller keeps showing the engine's own
 * rationale sentence.
 */

export interface EvidenceRow {
  label: string;
  value: string;
  /** Candidates flagged as chosen render with accent treatment. */
  accent?: boolean;
}

export interface ParsedDecision {
  mode?: string;
  overrideReason?: string;
  coverageScore?: number;
  candidateRows: EvidenceRow[];
  genericRows: EvidenceRow[];
}

const LABEL_OVERRIDES: Record<string, string> = {
  mode: 'MODE',
  override_reason: 'OVERRIDE',
  coverage_score: 'COVERAGE',
  candidates: 'CANDIDATES',
};

export function parseDecision(details: DispatchDecisionDetails): ParsedDecision {
  const known = new Set(Object.keys(LABEL_OVERRIDES));
  const candidateRows = formatCandidates(details.candidates);
  const genericRows: EvidenceRow[] = [];

  for (const [key, value] of Object.entries(details)) {
    if (known.has(key) || key === 'candidates') continue;
    if (value === null || value === undefined || value === '') continue;
    genericRows.push({
      label: key.replace(/_/g, ' ').toUpperCase(),
      value: typeof value === 'number' ? formatNumber(value) : String(value),
    });
  }

  return {
    mode: asString(details.mode),
    overrideReason: asString(details.override_reason),
    coverageScore: asNumber(details.coverage_score),
    candidateRows,
    genericRows,
  };
}

function formatCandidates(
  candidates: DispatchDecisionDetails['candidates'] | undefined,
): EvidenceRow[] {
  if (!Array.isArray(candidates) || candidates.length === 0) return [];
  return candidates.map((c) => {
    const name = c.callsign ?? c.ambulance_id ?? 'UNIT';
    const eta =
      typeof c.eta_sec === 'number' ? `${formatNumber(c.eta_sec / 60)} min` : null;
    const match =
      c.capability_match === true ? ' · CAP OK' : c.capability_match === false ? ' · CAP GAP' : '';
    return {
      label: c.selected ? 'SELECTED' : 'CONSIDERED',
      value: `${name}${eta ? ` · ETA ${eta}` : ''}${match}`,
      accent: Boolean(c.selected),
    };
  });
}

function asString(v: unknown): string | undefined {
  return typeof v === 'string' && v.length > 0 ? v : undefined;
}

function asNumber(v: unknown): number | undefined {
  return typeof v === 'number' && Number.isFinite(v) ? v : undefined;
}

export function formatNumber(n: number): string {
  return Number.isInteger(n) ? String(n) : n.toFixed(1);
}
