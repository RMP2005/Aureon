'use client';

import { useEffect, useState } from 'react';
import AureonMark from '@/components/brand/AureonMark';

/**
 * System boot overlay (Phase 11-refinement).
 *
 * A compact instrument boot between landing and operations. Stamps map to
 * real Aureon subsystems; the whole sequence completes well inside the
 * 2-second entry budget while the camera sweep runs underneath.
 * Purely presentational — it never blocks data readiness.
 */
const BOOT_LINES = [
  'TWIN RENDER ONLINE',
  'TELEMETRY LINK OPEN',
  'EVIDENCE STORE MOUNTED',
] as const;

const LINE_STAGGER_MS = 240;
const HOLD_MS = 420;
const FADE_MS = 260;

export default function BootOverlay() {
  const [visibleLines, setVisibleLines] = useState(0);
  const [fading, setFading] = useState(false);
  const [gone, setGone] = useState(false);

  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = [];
    BOOT_LINES.forEach((_, i) => {
      timers.push(
        setTimeout(() => setVisibleLines(i + 1), i * LINE_STAGGER_MS),
      );
    });
    const total =
      (BOOT_LINES.length - 1) * LINE_STAGGER_MS +
      HOLD_MS;
    timers.push(setTimeout(() => setFading(true), total));
    timers.push(
      setTimeout(() => setGone(true), total + FADE_MS),
    );
    return () => timers.forEach(clearTimeout);
  }, []);

  if (gone) return null;

  return (
    <div
      className={`pointer-events-none absolute inset-0 z-30 flex items-center justify-center bg-void transition-opacity ${
        fading ? 'opacity-0' : 'opacity-100'
      }`}
      style={{ transitionDuration: `${FADE_MS}ms` }}
    >
      <div className="flex items-start gap-4">
        <AureonMark size={44} />
        <div className="pt-0.5">
          <p className="font-display text-lg font-semibold tracking-tight">
            Aureon
            <span className="ml-2 hud-stamp !text-[9px] align-middle text-[var(--color-text-muted)]">
              URBAN INTELLIGENCE OS
            </span>
          </p>
          <div className="mt-2 space-y-1">
            {BOOT_LINES.map((line, i) => (
              <p
                key={line}
                className={`hud-stamp !text-[9px] transition-opacity duration-150 ${
                  i < visibleLines ? 'opacity-100' : 'opacity-0'
                }`}
              >
                <span className="text-teal-core">✓</span>{' '}
                <span className="text-[var(--color-text-muted)]">{line}</span>
              </p>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
