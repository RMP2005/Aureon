'use client';

import { useEffect, useState } from 'react';

/**
 * OnboardingOverlay (Phase 11H) — minimal first-visit map key.
 *
 * Explains the three moving elements users actually ask about. Shows once
 * per browser (`aureon:onboarding_v1`); never interrupts a replay session;
 * dismissible and self-expiring. Optional by design.
 */

const STORAGE_KEY = 'aureon:onboarding_v1';
const AUTO_HIDE_MS = 24_000;

const ENTRIES: { swatch: React.ReactNode; title: string; body: string }[] = [
  {
    swatch: (
      <span aria-hidden className="flex h-3 w-3 shrink-0 items-center justify-center rounded-full border-[1.5px] border-crit-red" />
    ),
    title: 'Incidents',
    body: 'Emergency events detected across the city.',
  },
  {
    swatch: (
      <span aria-hidden className="h-1.5 w-4 shrink-0 rounded-full bg-teal-core" />
    ),
    title: 'Units',
    body: 'Response vehicles dispatched by Aureon’s decision engine.',
  },
  {
    swatch: (
      <span aria-hidden className="flex gap-[3px]">
        {[0, 1, 2].map((d) => (
          <span key={d} className="h-1 w-1 rounded-full bg-teal-core/70" />
        ))}
      </span>
    ),
    title: 'Routes',
    body: 'Live paths showing optimized movement.',
  },
];

export default function OnboardingOverlay() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    let shown = false;
    try {
      shown = window.localStorage.getItem(STORAGE_KEY) === '1';
    } catch {
      /* storage unavailable — stay hidden rather than nag every load */
    }
    if (shown) return;

    const t = window.setTimeout(() => setVisible(true), 1200);
    return () => window.clearTimeout(t);
  }, []);

  useEffect(() => {
    if (!visible) return;
    const t = window.setTimeout(() => dismiss(), AUTO_HIDE_MS);
    return () => window.clearTimeout(t);
  }, [visible]);

  const dismiss = () => {
    setVisible(false);
    try {
      window.localStorage.setItem(STORAGE_KEY, '1');
    } catch {
      /* non-fatal */
    }
  };

  if (!visible) return null;

  return (
    <div className="absolute bottom-3 right-3 z-30 w-60 animate-[fadeIn_240ms_ease-out]">
      <div className="pointer-events-auto border border-hairline-strong bg-panel-1/90 px-3.5 py-3 backdrop-blur-md">
        <div className="flex items-baseline justify-between gap-2">
          <p className="hud-stamp !text-[9px] text-teal-core">READING THE MAP</p>
          <button
            type="button"
            onClick={dismiss}
            aria-label="Dismiss guide"
            className="hud-stamp !text-[9px] text-[var(--color-text-muted)] transition-colors hover:text-[var(--color-text-secondary)]"
          >
            ✕
          </button>
        </div>
        <ul className="mt-2.5 space-y-2.5">
          {ENTRIES.map((e) => (
            <li key={e.title} className="flex items-start gap-2.5">
              <span className="mt-0.5">{e.swatch}</span>
              <span>
                <span className="block text-xs font-medium text-[var(--color-text-primary)]">
                  {e.title}
                </span>
                <span className="mt-0.5 block text-[11px] leading-snug text-[var(--color-text-secondary)]">
                  {e.body}
                </span>
              </span>
            </li>
          ))}
        </ul>
        <button
          type="button"
          onClick={dismiss}
          className="hud-stamp mt-3 w-full rounded-sm border border-teal-core/40 bg-teal-core/10 px-2 py-1.5 !text-[9px] text-teal-core transition-colors hover:bg-teal-core/20"
        >
          GOT IT
        </button>
      </div>
    </div>
  );
}
