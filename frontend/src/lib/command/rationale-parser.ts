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

/** Plain-language display names for recurring evidence keys (Phase 11H). */
const GENERIC_LABELS: Record<string, string> = {
  eta_sec: 'TRAVEL TIME',
  travel_time_sec: 'TRAVEL TIME',
  eta_min: 'TRAVEL TIME',
  distance_km: 'DISTANCE',
  distance_to_scene_km: 'DISTANCE',
  response_time_sec: 'RESPONSE TIME',
  capability: 'EQUIPMENT',
  required_capability: 'EQUIPMENT NEEDED',
  severity: 'SEVERITY',
  priority: 'PRIORITY',
};

export function parseDecision(details: DispatchDecisionDetails): ParsedDecision {
  const known = new Set(Object.keys(LABEL_OVERRIDES));
  const candidateRows = formatCandidates(details.candidates);
  const genericRows: EvidenceRow[] = [];

  for (const [key, value] of Object.entries(details)) {
    if (known.has(key) || key === 'candidates') continue;
    if (value === null || value === undefined || value === '') continue;
    genericRows.push({
      label: (GENERIC_LABELS[key] ?? key.replace(/_/g, ' ')).toUpperCase(),
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
    // Plain-language outcome (Phase 11H): what happened, not acronyms.
    const eta =
      typeof c.eta_sec === 'number'
        ? `arrives in ${formatNumber(c.eta_sec / 60)} min`
        : null;
    const capability =
      c.capability_match === true
        ? 'right equipment'
        : c.capability_match === false
          ? 'lacks the required equipment'
          : null;
    const parts = [name, eta, capability].filter(Boolean).join(' · ');
    return {
      label: c.selected ? 'SELECTED' : 'CONSIDERED',
      value: parts,
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
