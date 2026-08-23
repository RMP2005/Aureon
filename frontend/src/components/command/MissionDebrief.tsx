'use client';

import { useMemo } from 'react';
import type { ReplayEvent, RunReplayRecording } from '@/lib/api';
import { useReplayStore } from '@/lib/twin/replay';
import { EmptyNote, PanelFrame } from './primitives';

/**
 * Mission Debrief (Phase 10F-1).
 *
 * Upgrades replay from a scrubber into storytelling: every incident becomes
 * a chapter assembled from its recorded event sequence — reported → unit
 * dispatched → closed with measured response time. Chapters are derived
 * purely from the RunRecorder journal; nothing is inferred.
 */
export default function MissionDebrief({
  recording,
}: {
  recording: RunReplayRecording | null;
}) {
  const playheadSec = useReplayStore((s) => s.playheadSec);
  const activeEventId = useReplayStore((s) => s.activeEventId);
  const seekToEvent = useReplayStore((s) => s.seekToEvent);
  const guided = useReplayStore((s) => s.guided);
  const toggleGuided = useReplayStore((s) => s.toggleGuided);

  const chapters = useMemo(
    () => buildChapters(recording?.events ?? []),
    [recording],
  );

  return (
    <PanelFrame
      title="Mission Debrief"
      right={
        <button
          onClick={toggleGuided}
          title="Camera eases to each entity as the playhead crosses its events"
          className={`hud-stamp !text-[9px] rounded-sm border px-1.5 py-0.5 transition-colors ${
            guided
              ? 'border-teal-core/50 bg-teal-core/10 text-teal-core'
              : 'border-hairline-strong text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
          }`}
        >
          GUIDED {guided ? 'ON' : 'OFF'}
        </button>
      }
    >
      {chapters.length === 0 ? (
        <EmptyNote>
          No mission sequences recorded in this window.
        </EmptyNote>
      ) : (
        <ol className="divide-y divide-[color:var(--color-hairline)]">
          {chapters.map((ch) => {
            const isActive =
              playheadSec >= ch.startSec && playheadSec <= ch.endSec + 30;
            const played = playheadSec >= ch.endSec;
            const activeEventInChapter = ch.events.some(
              (e) => e.id === activeEventId,
            );
            return (
              <li key={ch.incidentId}>
                <button
                  onClick={() =>
                    seekToEvent(ch.reported ?? ch.events[0])
                  }
                  className={`w-full px-3 py-2 text-left transition-colors ${
                    activeEventInChapter
                      ? 'bg-teal-core/10 ring-1 ring-inset ring-teal-core/40'
                      : isActive
                        ? 'bg-white/[0.03]'
                        : 'hover:bg-white/[0.03]'
                  }`}
                >
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="truncate text-xs font-medium">
                      {ch.title}
                    </span>
                    <span className="tnum shrink-0 font-mono text-[10px] text-[var(--color-text-muted)]">
                      T+{format(ch.startSec)}
                    </span>
                  </div>

                  {/* Sequence rail — one dot per recorded fact */}
                  <div className="mt-1.5 flex items-center gap-1">
                    {ch.events.map((e) => (
                      <span
                        key={e.id}
                        title={`${kindLabel(e.kind)} · T+${format(e.sim_time_sec)}\n${e.text}`}
                        className={`h-1.5 w-1.5 rotate-45 ${
                          played ? toneFor(e.kind) : 'bg-white/20'
                        }`}
                      />
                    ))}
                    {played && (
                      <span className="ml-1 hud-stamp !text-[8px] text-teal-core">
                        ✓ CLOSED{ch.responseMin !== null && ` · ${ch.responseMin} MIN`}
                      </span>
                    )}
                  </div>

                  {/* Latest beat line */}
                  <p className="mt-1 truncate text-[11px] leading-snug text-[var(--color-text-muted)]">
                    {latestBeat(ch, playheadSec)}
                  </p>
                </button>
              </li>
            );
          })}
        </ol>
      )}
    </PanelFrame>
  );
}

// ---------------------------------------------------------------------------
// Chapter assembly — grouped strictly by recorder incident linkage.
// ---------------------------------------------------------------------------

interface Chapter {
  incidentId: string;
  title: string;
  startSec: number;
  endSec: number;
  events: ReplayEvent[];
  /** Reported event (chapter head) for seeking/focus. */
  reported: ReplayEvent | null;
  responseMin: string | null;
}

function buildChapters(events: ReplayEvent[]): Chapter[] {
  const byIncident = new Map<string, ReplayEvent[]>();
  for (const e of events) {
    const key = e.incident_id ?? (e.kind === 'INCIDENT' ? e.entity_id : null);
    if (!key) continue;
    const list = byIncident.get(key) ?? [];
    list.push(e);
    byIncident.set(key, list);
  }

  const chapters: Chapter[] = [];
  for (const [incidentId, evts] of byIncident) {
    if (evts.length === 0) continue;
    const sorted = [...evts].sort((a, b) => a.sim_time_sec - b.sim_time_sec);
    const reported = sorted.find((e) => e.kind === 'INCIDENT') ?? null;
    const resolved = sorted.find((e) => e.kind === 'RESOLVED') ?? null;
    // Outcome text: "inc_0007 closed · response 8.4 min · …"
    const rtMatch = resolved?.text.match(/response ([\d.]+) min/);
    chapters.push({
      incidentId,
      title:
        reported?.text.replace(/ reported · /, ' · ') ??
        `${incidentId.replace(/_/g, ' ').toUpperCase()} sequence`,
      startSec: sorted[0].sim_time_sec,
      endSec: resolved?.sim_time_sec ?? sorted[sorted.length - 1].sim_time_sec,
      events: sorted,
      reported,
      responseMin: rtMatch ? rtMatch[1] : null,
    });
  }
  chapters.sort((a, b) => a.startSec - b.startSec);
  return chapters;
}

function latestBeat(ch: Chapter, playheadSec: number): string {
  const past = ch.events.filter((e) => e.sim_time_sec <= playheadSec);
  const beat = past.length > 0 ? past[past.length - 1] : ch.events[0];
  return beat.text;
}

function toneFor(kind: string): string {
  switch (kind) {
    case 'INCIDENT':
      return 'bg-crit-red';
    case 'DISPATCH':
      return 'bg-teal-core';
    case 'RESOLVED':
      return 'bg-teal-core';
    default:
      return 'bg-white/40';
  }
}

function kindLabel(kind: string): string {
  switch (kind) {
    case 'INCIDENT':
      return 'REPORTED';
    case 'DISPATCH':
      return 'UNIT DISPATCHED';
    case 'RESOLVED':
      return 'CLOSED';
    case 'ADMISSION':
      return 'ADMISSION';
    default:
      return kind;
  }
}

function format(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}
