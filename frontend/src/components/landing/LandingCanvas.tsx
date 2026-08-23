'use client';

import { Suspense, useEffect, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import LandingScene from './LandingScene';

/**
 * Pinned cinematic canvas (Phase 10C).
 * Full viewport, behind the scroll content. DPR clamped; no interactions —
 * this is a film, not an instrument (the twin keeps those controls).
 *
 * Stability guard (Phase 11): WebGL tree mounts post-hydration only.
 */
export default function LandingCanvas() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    const id = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(id);
  }, []);

  if (!mounted) return null;

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
