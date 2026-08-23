'use client';

import { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import LandingScene from './LandingScene';

/**
 * Pinned cinematic canvas (Phase 10C).
 * Full viewport, behind the scroll content. DPR clamped; no interactions —
 * this is a film, not an instrument (the twin keeps those controls).
 */
export default function LandingCanvas() {
  return (
    <Canvas
      dpr={[1, 2]}
      camera={{ position: [0, 165, 8], fov: 50, near: 0.5, far: 900 }}
      gl={{ antialias: true, powerPreference: 'high-performance' }}
    >
      <Suspense fallback={null}>
        <LandingScene />
      </Suspense>
    </Canvas>
  );
}
