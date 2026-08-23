'use client';

import { useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';

export interface TwinPerfStats {
  fps: number;
  drawCalls: number;
  triangles: number;
}

/**
 * Performance baseline probe (Phase 10B).
 * Samples the renderer's frame stats twice per second and reports upward
 * through a callback — renders nothing, keeps zero React state.
 */
export default function StatsProbe({
  onStats,
}: {
  onStats: (stats: TwinPerfStats) => void;
}) {
  const gl = useThree((s) => s.gl);
  const ema = useRef(60);
  const sinceReport = useRef(0);
  const onStatsRef = useRef(onStats);
  onStatsRef.current = onStats;

  useFrame((_, dt) => {
    if (dt > 0) {
      const fps = 1 / dt;
      ema.current = ema.current * 0.95 + fps * 0.05;
    }
    sinceReport.current += dt;
    if (sinceReport.current >= 0.5) {
      sinceReport.current = 0;
      onStatsRef.current({
        fps: Math.round(ema.current),
        drawCalls: gl.info.render.calls,
        triangles: gl.info.render.triangles,
      });
    }
  });

  return null;
}
