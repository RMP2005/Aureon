'use client';

import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';
import { useTwinStore } from '@/lib/twin/store';
import { getLiveBuffer } from '@/lib/twin/live-buffer';
import { HOSPITALS } from '@/lib/twin/city-data';

/**
 * Camera rig (Phase 10B) — blueprint camera-stability rules:
 *  - No auto-orbit. The city holds still unless the user moves it.
 *  - Polar clamp keeps the horizon honest; you can never go under the map.
 *  - Selection focus is a one-shot eased glide, cancelled instantly by any
 *    user input — the operator always wins.
 */
export default function CameraRig() {
  const controlsRef = useRef<OrbitControlsImpl>(null);
  const selection = useTwinStore((s) => s.selection);

  // One-shot selection focus tween state
  const tween = useRef<{
    active: boolean;
    t: number;
    from: THREE.Vector3;
    to: THREE.Vector3;
  } | null>(null);

  useEffect(() => {
    const controls = controlsRef.current;
    if (!controls || !selection) {
      tween.current = null;
      return;
    }

    let x: number | null = null;
    let z: number | null = null;
    if (selection.kind === 'ambulance') {
      const m = getLiveBuffer().ambulances.get(selection.id);
      if (m) {
        x = m.x;
        z = m.z;
      }
    } else {
      const h = HOSPITALS.find((hp) => hp.id === selection.id);
      if (h) {
        x = h.x;
        z = h.z;
      }
    }
    if (x === null || z === null) return;

    tween.current = {
      active: true,
      t: 0,
      from: controls.target.clone(),
      to: new THREE.Vector3(x, 0, z),
    };
  }, [selection]);

  // Any user gesture cancels an in-flight focus tween
  useEffect(() => {
    const controls = controlsRef.current;
    if (!controls) return;
    const cancel = () => {
      tween.current = null;
    };
    controls.addEventListener('start', cancel);
    return () => controls.removeEventListener('start', cancel);
  }, []);

  useFrame((_, dt) => {
    const tw = tween.current;
    const controls = controlsRef.current;
    if (!tw?.active || !controls) return;

    tw.t = Math.min(1, tw.t + dt / 0.6);
    // easeOutCubic
    const k = 1 - Math.pow(1 - tw.t, 3);
    controls.target.lerpVectors(tw.from, tw.to, k);

    // Glide only pans; zoom/rotation stay under user control
    if (tw.t >= 1) tween.current = null;
  });

  return (
    <OrbitControls
      ref={controlsRef}
      makeDefault
      enableDamping
      dampingFactor={0.08}
      minDistance={10}
      maxDistance={220}
      minPolarAngle={0.15}
      maxPolarAngle={1.32}
      target={[0, 0, 0]}
    />
  );
}
