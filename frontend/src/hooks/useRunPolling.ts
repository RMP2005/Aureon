'use client';

import { useCallback, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getRunStatus, type RunProgress } from '@/lib/api';

/**
 * Adaptive run-status polling (Phase 10A).
 *
 * - Polls 1 Hz while queued/running; stops on terminal states.
 * - Backs off exponentially (1s → 8s) on transient fetch failures.
 * - Only surfaces an error after MAX_FAILURES consecutive misses, so a
 *   network blip never aborts an in-flight simulation display.
 */
const ACTIVE_INTERVAL_MS = 1_000;
const MAX_BACKOFF_MS = 8_000;
const MAX_FAILURES = 5;

export function useRunPolling(onCompleted?: (runId: string) => void) {
  const [runId, setRunId] = useState<string | null>(null);
  const notifiedRef = useRef(false);
  const onCompletedRef = useRef(onCompleted);
  onCompletedRef.current = onCompleted;

  const query = useQuery({
    queryKey: ['run-status', runId],
    enabled: runId !== null,
    queryFn: () => getRunStatus(runId as string),
    refetchInterval: (q) => {
      const data = q.state.data?.data;
      if (!data || data.status === 'queued' || data.status === 'running') {
        const failures = q.state.fetchFailureCount;
        return failures === 0
          ? ACTIVE_INTERVAL_MS
          : Math.min(ACTIVE_INTERVAL_MS * 2 ** failures, MAX_BACKOFF_MS);
      }
      return false; // completed / failed — stop
    },
    retry: MAX_FAILURES,
    retryDelay: (attempt) =>
      Math.min(ACTIVE_INTERVAL_MS * 2 ** attempt, MAX_BACKOFF_MS),
  });

  const progress: RunProgress | null = query.data?.data ?? null;

  if (
    progress &&
    (progress.status === 'completed' || progress.status === 'failed')
  ) {
    if (!notifiedRef.current) {
      notifiedRef.current = true;
      if (progress.status === 'completed' && progress.run_id) {
        onCompletedRef.current?.(progress.run_id);
      }
    }
  }

  const startPolling = useCallback((id: string) => {
    notifiedRef.current = false;
    setRunId(id);
  }, []);

  const stopPolling = useCallback(() => {
    setRunId(null);
  }, []);

  return {
    progress,
    /** Non-null only after sustained failures — blips stay invisible. */
    error:
      query.failureCount >= MAX_FAILURES
        ? 'Lost contact with the simulation service.'
        : null,
    isPolling: runId !== null,
    startPolling,
    stopPolling,
  };
}
