'use client';

import { Suspense, useEffect, useMemo, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import TwinScene from './TwinScene';
import type { TwinPerfStats } from './StatsProbe';
import { useTwinStore } from '@/lib/twin/store';

/**
 * Twin canvas host (Phase 10B).
 * DPR clamped to [1, 2]; background click clears selection.
 *
 * Stability guard (Phase 11): the WebGL tree mounts only after client
 * hydration completes. Mounting heavy R3F subtrees during the hydration
 * window races Next.js chunk execution and can surface as webpack
 * "Cannot read properties of undefined (reading 'call')" errors.
 *
 * Responsive pass: on PORTRAIT viewports only, the initial operational
 * framing pulls back so the full city fits the narrow field of view.
 * Landscape/desktop keeps the approved framing exactly (factor = 1).
 */
function initialCameraPosition(): [number, number, number] {
  if (typeof window === 'undefined') return [0, 95, 78];
  const aspect = window.innerWidth / Math.max(1, window.innerHeight);
  const factor = aspect >= 1 ? 1 : Math.min(1.55, (1 / aspect) * 0.92);
  return [0, 95 * factor, 78 * factor];
}

export default function TwinCanvas({
  onStats,
}: {
  onStats?: (stats: TwinPerfStats) => void;
}) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    const id = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(id);
  }, []);

  const cameraPosition = useMemo(initialCameraPosition, []);

  if (!mounted) return null;

  return (
    <Canvas
      dpr={[1, 2]}
      camera={{ position: cameraPosition, fov: 50, near: 0.5, far: 800 }}
      gl={{ antialias: true, powerPreference: 'high-performance' }}
      onPointerMissed={() => useTwinStore.getState().select(null)}
    >
      <Suspense fallback={null}>
        <TwinScene onStats={onStats} />
      </Suspense>
    </Canvas>
  );
}

