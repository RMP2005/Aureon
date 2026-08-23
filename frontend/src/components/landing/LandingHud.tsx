'use client';

import { useEffect, useRef } from 'react';
import { getLandingProgress } from '@/lib/landing/progress';
import { CITY, CENTER_LAT, CENTER_LNG } from '@/lib/twin/projection';

/**
 * Scientific instrument overlay (Phase 11-refinement).
 *
 * Factual telemetry only — every number is derived from the real city
 * dataset. No cards, no chrome: fixed mono text in the lower-left that
 * reads like a range-instrument printout while the network materializes.
 * Fades out as the journey hands off to the epilogue.
 */
export default function LandingHud() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let raf = 0;
    const tick = () => {
      const el = ref.current;
      if (el) {
        const p = getLandingProgress();
        // Visible through the network reveal; gone before the epilogue.
        const opacity = p < 0.06 ? p / 0.06 : p > 0.82 ? Math.max(0, 1 - (p - 0.82) / 0.08) : 1;
        el.style.opacity = String(opacity);
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  const segments = CITY.segments.length.toLocaleString('en-US');
  const hospitals = CITY.hospitals.length;
  const stations = CITY.stations.length;
  const lat = `${Math.abs(CENTER_LAT).toFixed(2)}°${CENTER_LAT >= 0 ? 'N' : 'S'}`;
  const lng = `${Math.abs(CENTER_LNG).toFixed(2)}°${CENTER_LNG >= 0 ? 'E' : 'W'}`;

  return (
    <div
      ref={ref}
      className="pointer-events-none absolute bottom-7 left-6 z-10 hidden sm:block"
      style={{ opacity: 0 }}
    >
      <p className="hud-stamp !text-[9px] leading-relaxed text-teal-core">
        CITY MODEL ONLINE
      </p>
      <div className="mt-2 space-y-1 hud-stamp !text-[9px] leading-relaxed text-[var(--color-text-muted)]">
        <p>
          BENGALURU&nbsp;&nbsp;{lat} {lng}
        </p>
        <div className="h-px w-40 bg-hairline-strong" />
        <p>
          ROAD NETWORK<span className="float-right tnum ml-6">{segments} SEG</span>
        </p>
        <p>
          MEDICAL NODES<span className="float-right tnum ml-6">{hospitals}</span>
        </p>
        <p>
          RESPONSE BASES<span className="float-right tnum ml-6">{stations}</span>
        </p>
      </div>
    </div>
  );
}
