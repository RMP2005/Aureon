'use client';

import { useEffect, useRef } from 'react';
import { getLandingProgress } from '@/lib/landing/progress';
import MapLegend from '@/components/twin/MapLegend';

/**
 * Landing legend (Phase 11H) — the map key surfaces with the final reveal,
 * once the city itself is fully awake. Fades in over the epilogue window.
 */
export default function LandingLegend() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let raf = 0;
    const tick = () => {
      const el = ref.current;
      if (el) {
        const p = getLandingProgress();
        // Arrives as the response zones settle; never competes earlier.
        const opacity = p < 0.9 ? 0 : Math.min(1, (p - 0.9) / 0.07);
        el.style.opacity = String(opacity);
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  return (
    <div
      ref={ref}
      className="pointer-events-none absolute bottom-6 left-6 z-20 hidden sm:block"
      style={{ opacity: 0 }}
    >
      <MapLegend />
    </div>
  );
}
