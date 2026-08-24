'use client';

import { useMemo } from 'react';
import * as THREE from 'three';
import { createRoadGeometry, ROAD_TIERS, type RoadTier } from '@/lib/twin/city-data';

/**
 * The arterial skeleton — three merged LineSegments draw calls total.
 * Static geometry; the GPU does everything after mount.
 *
 * Hierarchy reads through brightness, not hue (city stays monochrome so
 * entity states own the color channel).
 */
const TIER_STYLE: Record<RoadTier, { opacity: number; tint: number }> = {
  0: { opacity: 0.92, tint: 0xcdd9ec }, // trunk / expressway — titanium-white
  1: { opacity: 0.55, tint: 0x76889f }, // primary arterial
  2: { opacity: 0.26, tint: 0x44516a }, // secondary
};

function TierLines({ tier }: { tier: RoadTier }) {
  // createRoadGeometry emits finite itemSize-3 XZ positions — no matrix
  // math, immune to the three r160+ itemSize-2 NaN regression.
  const geometry = useMemo(() => createRoadGeometry(tier), [tier]);

  if (!geometry) return null;

  const style = TIER_STYLE[tier];
  return (
    <lineSegments geometry={geometry} frustumCulled={false}>
      <lineBasicMaterial
        color={style.tint}
        transparent
        opacity={style.opacity}
        depthWrite={false}
      />
    </lineSegments>
  );
}

export default function CityRoads() {
  return (
    <group position-y={0}>
      {ROAD_TIERS.map((t) => (
        <TierLines key={t} tier={t} />
      ))}
    </group>
  );
}
