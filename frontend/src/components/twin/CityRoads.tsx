'use client';

import { useMemo } from 'react';
import * as THREE from 'three';
import { getRoadBuffer, ROAD_TIERS, type RoadTier } from '@/lib/twin/city-data';

/**
 * The arterial skeleton — three merged LineSegments draw calls total.
 * Static geometry; the GPU does everything after mount.
 *
 * Hierarchy reads through brightness, not hue (city stays monochrome so
 * entity states own the color channel).
 */
const TIER_STYLE: Record<RoadTier, { opacity: number; tint: number }> = {
  0: { opacity: 0.85, tint: 0x8fa3bf }, // trunk / expressway
  1: { opacity: 0.5, tint: 0x6b7d99 }, // primary arterial
  2: { opacity: 0.22, tint: 0x4a5872 }, // secondary
};

function TierLines({ tier }: { tier: RoadTier }) {
  const geometry = useMemo(() => {
    const buffer = getRoadBuffer(tier);
    // Empty network data → no geometry at all. Mounting a zero-vertex
    // position attribute makes Three.js compute a NaN bounding sphere.
    if (!buffer) return null;
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(buffer, 2));
    // Z-up data → lie flat onto XZ plane
    geo.applyMatrix4(new THREE.Matrix4().makeRotationX(Math.PI / 2));
    return geo;
  }, [tier]);

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
