'use client';

import { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  getRunLiveState,
  getRunById,
  type RunLiveState,
  type SimulationRunResult,
} from '@/lib/api';
import { ingestLiveState } from '@/lib/twin/live-buffer';
import { useLedgerStore, type LedgerEvent } from '@/lib/command/ledger';

export type FeedStatus = 'standby' | 'live' | 'ended';

let eventSeq = 0;
const nextEventId = () => `evt_${Date.now().toString(36)}_${eventSeq++}`;

/**
 * Command feed (Phase 10D) — the single data artery of the mission control.
 *
 * Polls the run-scoped B1 endpoint at 1 Hz, ingests each snapshot into the
 * twin's live buffer, and derives Decision-Ledger entries from observed
 * deltas between consecutive snapshots. On run completion it fetches the
 * persisted result for metrics + dispatch-log rationales. No synthetic
 * data anywhere: panels render exactly what the engine reported.
 */
export function useCommandFeed(runId: string | null) {
  const [status, setStatus] = useState<FeedStatus>(
    runId ? 'live' : 'standby',
  );
  const [result, setResult] = useState<SimulationRunResult | null>(null);
  const prevRef = useRef<RunLiveState | null>(null);
  const appendLedger = useLedgerStore((s) => s.append);

  const query = useQuery({
    queryKey: ['command-feed', runId],
    enabled: runId !== null && status !== 'ended',
    queryFn: async (): Promise<RunLiveState | null> => {
      try {
        const res = await getRunLiveState(runId as string);
        return res.data;
      } catch (e) {
        if (e instanceof Error && e.message.includes('404')) {
          return null; // live window closed — handled below
        }
        throw e;
      }
    },
    refetchInterval: 1_000,
    retry: false,
    staleTime: 0,
    gcTime: 0,
  });

  // Ingest + derive ledger deltas on every fresh snapshot.
  useEffect(() => {
    const state = query.data;
    if (!state || status === 'ended') return;

    ingestLiveState(state);
    deriveDeltas(prevRef.current, state, appendLedger);
    prevRef.current = state;
  }, [query.data, status, appendLedger]);

  // Terminal transition: freeze feed, pull archived result.
  useEffect(() => {
    if (!runId || status === 'ended' || query.data !== null) return;
    if (query.isSuccess || query.isError) {
      setStatus('ended');
    }
  }, [runId, status, query.data, query.isSuccess, query.isError]);

  useEffect(() => {
    if (status !== 'ended' || !runId || result) return;
    let cancelled = false;
    getRunById(runId)
      .then((res) => {
        if (cancelled) return;
        setResult(res.data);
        const log = res.data.dispatch_log_sample ?? [];
        appendLedger(
          log.map((entry): LedgerEvent => ({
            id: nextEventId(),
            kind: 'LOG',
            severity: entry.severity,
            text: `${entry.callsign} → ${entry.incident_id} (${entry.category}) · ${entry.rationale}`,
            simSec: entry.sim_time_sec,
            source: 'DISPATCH_LOG',
            // Structured decision evidence (Phase 10E-2).
            details: entry.decision ?? null,
          })),
        );
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [status, runId, result, appendLedger]);

  // Reset when switching runs — the ledger belongs to one run at a time.
  useEffect(() => {
    prevRef.current = null;
    setStatus(runId ? 'live' : 'standby');
    setResult(null);
    useLedgerStore.getState().clear();
  }, [runId]);

  return {
    liveState: query.data ?? null,
    progress: query.data?.run_status ?? null,
    result,
    status,
    lastSuccessAt: query.dataUpdatedAt,
    isFetching: query.isFetching,
  };
}

// ---------------------------------------------------------------------------
// Delta derivation — the ledger only records what actually changed.
// ---------------------------------------------------------------------------

function deriveDeltas(
  prev: RunLiveState | null,
  next: RunLiveState,
  append: (events: LedgerEvent[]) => void,
) {
  const events: LedgerEvent[] = [];
  const simSec = next.sim_time_sec;

  if (prev && next.completed_incidents_count > prev.completed_incidents_count) {
    const resolved = next.completed_incidents_count - prev.completed_incidents_count;
    events.push({
      id: nextEventId(),
      kind: 'RESOLVED',
      text:
        resolved === 1
          ? '1 incident closed · outcome logged'
          : `${resolved} incidents closed · outcomes logged`,
      simSec,
      source: 'LIVE',
    });
  }

  const prevIncidents = new Map(
    (prev?.active_incidents ?? []).map((i) => [i.id, i]),
  );

  for (const inc of next.active_incidents) {
    const before = prevIncidents.get(inc.id);
    if (!before) {
      events.push({
        id: nextEventId(),
        kind: 'INCIDENT',
        severity: inc.severity,
        text: `${inc.category.replace(/_/g, ' ').toUpperCase()} reported · ${inc.location_name}`,
        simSec,
        source: 'LIVE',
      });
    } else if (
      inc.assigned_ambulance &&
      inc.assigned_ambulance !== before.assigned_ambulance
    ) {
      events.push({
        id: nextEventId(),
        kind: 'DISPATCH',
        severity: inc.severity,
        text: `unit ${inc.assigned_ambulance} dispatched → ${inc.id}`,
        simSec,
        source: 'LIVE',
      });
    }
  }

  if (events.length > 0) append(events);
}
