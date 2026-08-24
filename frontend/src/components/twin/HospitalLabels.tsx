'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { Html } from '@react-three/drei';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { HOSPITALS } from '@/lib/twin/city-data';

/**
 * HospitalLabels — Phase FINAL polish.
 *
 * Purely additive overlay: small HUD chips naming each blue hospital
 * beacon. Reads the same public HOSPITALS table the markers render from;
 * touches nothing in the marker pipeline, roads, camera or scene graph.
 *
 * Anti-clutter contract (information > decoration):
 *   - far orbit  (> FAR_DIST):  no labels
 *   - mid orbit:                a curated set of flagship facilities
 *   - close orbit (< MID_DIST): every hospital labeled
 * Bands carry hysteresis so wheel scrubbing never flickers.
 */

const FAR_DIST = 118;
const NEAR_DIST = 62;
const HYSTERESIS = 5;

type Tier = 'far' | 'mid' | 'near';

const FLAGSHIP_KEYWORDS = [
  'Narayana',
  'Apollo',
  'Manipal',
  'Vydehi',
  'Victoria',
  'Ramaiah',
  'Jayadeva',
  'NIMHANS',
  'Fortis',
  'Aster CMI',
  'St. John',
  'Sakra',
];

const FLAGSHIP_IDS = new Set(
  HOSPITALS.filter((h) => FLAGSHIP_KEYWORDS.some((k) => h.name.includes(k))).map((h) => h.id),
);

/** Split a long facility name into two compact HUD lines. */
function splitName(name: string): [string, string] {
  const words = name.split(' ');
  if (words.length <= 2) return [name, ''];
  const cut = Math.min(2, Math.ceil(words.length / 2));
  return [words.slice(0, cut).join(' '), words.slice(cut).join(' ')];
}

function tierFor(dist: number, prev: Tier): Tier {
  // Hysteresis: require crossing back beyond the threshold ± margin.
  const enterNear = NEAR_DIST - HYSTERESIS;
  const exitNear = NEAR_DIST + HYSTERESIS;
  const enterFar = FAR_DIST + HYSTERESIS;
  const exitFar = FAR_DIST - HYSTERESIS;
  if (prev === 'near' && dist < exitNear) return 'near';
  if (prev === 'mid' && dist >= enterNear && dist <= enterFar) return 'mid';
  if (prev === 'far' && dist > exitFar) return 'far';
  if (dist < enterNear) return 'near';
  if (dist > enterFar) return 'far';
  return 'mid';
}

export default function HospitalLabels() {
  const [tier, setTier] = useState<Tier>('far');
  const tierRef = useRef<Tier>('far');
  const camera = useThree((s) => s.camera);

  // Poll camera distance on interval instead of per-frame setState —
  // zero impact on the render loop's hot path.
  useEffect(() => {
    let raf = 0;
    let acc = 0;
    let last = performance.now();
    const tick = (now: number) => {
      acc += now - last;
      last = now;
      if (acc >= 250) {
        acc = 0;
        const next = tierFor(camera.position.distanceTo(new THREE.Vector3(0, 0, 0)), tierRef.current);
        if (next !== tierRef.current) {
          tierRef.current = next;
          setTier(next);
        }
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [camera]);

  const shown = useMemo(
    () =>
      tier === 'near'
        ? HOSPITALS
        : tier === 'mid'
          ? HOSPITALS.filter((h) => FLAGSHIP_IDS.has(h.id))
          : [],
    [tier],
  );

  if (shown.length === 0) return null;

  return (
    <>
      {shown.map((h) => {
        const [l1, l2] = splitName(h.name);
        return (
          <Html key={h.id} position={[h.x, 2.35, h.z]} center zIndexRange={[15, 5]} style={{ pointerEvents: 'none' }}>
            <div className="flex select-none flex-col items-center whitespace-nowrap rounded border border-[#4da3ff]/35 bg-void/70 px-1.5 py-0.5 backdrop-blur-sm transition-opacity duration-700">
              <span className="hud-stamp !text-[7px] !leading-[1.25] text-[#a8ccf5]">
                {l1.toUpperCase()}
              </span>
              {l2 && (
                <span className="hud-stamp !text-[6.5px] !leading-[1.25] text-[var(--color-text-muted)]">
                  {l2.toUpperCase()}
                </span>
              )}
            </div>
          </Html>
        );
      })}
    </>
  );
}
