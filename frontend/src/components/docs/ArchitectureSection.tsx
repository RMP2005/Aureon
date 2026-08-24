'use client';

import { useState } from 'react';

/**
 * ArchitectureSection — collapsible developer view (Phase 11F).
 *
 * Default state is plain English. The technical inventory stays folded
 * until explicitly opened.
 */
const COLUMNS: { title: string; tone: string; items: string[] }[] = [
  {
    title: 'FRONTEND',
    tone: 'text-teal-core',
    items: [
      'Next.js — app shell & routing',
      'React Three Fiber — the digital twin',
      'Zustand — selection & session state',
      'TanStack Query — live run polling',
    ],
  },
  {
    title: 'BACKEND',
    tone: 'text-teal-core',
    items: [
      'FastAPI — run lifecycle & API envelope',
      'Simulation engine — deterministic city ticks',
      'SQLite (WAL) — runs, recordings, evidence',
    ],
  },
  {
    title: 'INTELLIGENCE',
    tone: 'text-violet-intel',
    items: [
      'Adaptive dispatch strategy — coverage-aware decisions',
      'Decision evidence — rationale published by the engine',
      'Replay pipeline — frame-recorded, immutable outcomes',
    ],
  },
];

export default function ArchitectureSection() {
  const [open, setOpen] = useState(false);

  return (
    <div className="border border-hairline bg-panel-1">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between px-4 py-3 text-left transition-colors hover:bg-white/[0.02]"
      >
        <span className="hud-stamp !text-[10px] text-[var(--color-text-secondary)]">
          ARCHITECTURE — FOR DEVELOPERS
        </span>
        <span
          aria-hidden
          className={`hud-stamp !text-[9px] text-[var(--color-text-muted)] transition-transform duration-200 ${
            open ? 'rotate-180' : ''
          }`}
        >
          ▾
        </span>
      </button>

      {open && (
        <div className="border-t border-hairline px-4 py-5">
          <div className="grid gap-8 md:grid-cols-3">
            {COLUMNS.map((c) => (
              <div key={c.title}>
                <p className={`hud-stamp !text-[10px] mb-3 ${c.tone}`}>{c.title}</p>
                <ul className="space-y-1.5 text-xs leading-relaxed text-[var(--color-text-secondary)]">
                  {c.items.map((i) => (
                    <li key={i}>— {i}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
