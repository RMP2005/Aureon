'use client';

import { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import TwinScene from './TwinScene';
import type { TwinPerfStats } from './StatsProbe';
import { useTwinStore } from '@/lib/twin/store';

/**
 * Twin canvas host (Phase 10B).
 * DPR clamped to [1, 2]; background click clears selection.
 */
export default function TwinCanvas({
  onStats,
}: {
  onStats?: (stats: TwinPerfStats) => void;
}) {
  return (
    <Canvas
      dpr={[1, 2]}
      camera={{ position: [0, 95, 78], fov: 50, near: 0.5, far: 800 }}
      gl={{ antialias: true, powerPreference: 'high-performance' }}
      onPointerMissed={() => useTwinStore.getState().select(null)}
    >
      <Suspense fallback={null}>
        <TwinScene onStats={onStats} />
      </Suspense>
    </Canvas>
  );
}
