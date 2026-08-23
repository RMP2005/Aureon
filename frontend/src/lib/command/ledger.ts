import { create } from 'zustand';

/**
 * Decision Ledger (Phase 10D).
 *
 * Every entry is derived from authoritative engine snapshots or persisted
 * dispatch logs — never fabricated. LIVE events are observed deltas between
 * consecutive snapshots; LOG events come verbatim from the run's dispatch
 * log sample with the engine's own rationale text.
 */
export interface LedgerEvent {
  id: string;
  kind: 'INCIDENT' | 'DISPATCH' | 'RESOLVED' | 'LOG';
  severity?: string;
  text: string;
  /** Simulation seconds at observation — drives timeline markers. */
  simSec: number;
  source: 'LIVE' | 'DISPATCH_LOG' | 'REPLAY';
}

interface LedgerStore {
  events: LedgerEvent[];
  /** Transient evidence-link highlight (marker click → ledger entry). */
  highlightId: string | null;
  append: (events: LedgerEvent[]) => void;
  setHighlight: (id: string | null) => void;
  clear: () => void;
}

const MAX_EVENTS = 200;

export const useLedgerStore = create<LedgerStore>((set) => ({
  events: [],
  highlightId: null,
  append: (incoming) =>
    set((s) => ({ events: [...incoming, ...s.events].slice(0, MAX_EVENTS) })),
  setHighlight: (highlightId) => set({ highlightId }),
  clear: () => set({ events: [], highlightId: null }),
}));
