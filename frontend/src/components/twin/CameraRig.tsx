'use client';

import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';
import { useTwinStore } from '@/lib/twin/store';
import { getLiveBuffer } from '@/lib/twin/live-buffer';
import { HOSPITALS } from '@/lib/twin/city-data';
import { consumeIntroSweep } from '@/lib/twin/intro';

/** Operational camera default (TwinCanvas initial position). */
const OPERATIONAL_POSITION = new THREE.Vector3(0, 95, 78);
const OPERATIONAL_TARGET = new THREE.Vector3(0, 0, 0);
/** Landing journey's final hero framing — continuity handoff start. */
const LANDING_HERO_POSITION = new THREE.Vector3(0, 76, 100);
/** Entry budget (Phase 11-refinement): sweep + boot ≤ 2 seconds total. */
const INTRO_SWEEP_SEC = 1.6;

/**
 * Camera rig (Phase 10B) — blueprint camera-stability rules:
 *  - No auto-orbit. The city holds still unless the user moves it.
 *  - Polar clamp keeps the horizon honest; you can never go under the map.
 *  - Selection focus is a one-shot eased glide, cancelled instantly by any
 *    user input — the operator always wins.
 * Phase 10F-1: on arrival from the landing journey, a one-shot intro sweep
 * descends from the landing's hero framing into operational view.
 */
export default function CameraRig() {
  const controlsRef = useRef<OrbitControlsImpl>(null);
  const selection = useTwinStore((s) => s.selection);

  // One-shot tween state (intro sweep + selection focus)
  const tween = useRef<{
    active: boolean;
    t: number;
    duration: number;
    targetFrom: THREE.Vector3;
    targetTo: THREE.Vector3;
    posFrom?: THREE.Vector3;
    posTo?: THREE.Vector3;
  } | null>(null);

  // Intro sweep (Phase 10F-1, hardened Phase 11-stability): armed by
  // ?intro=1 on the command page. Consumed once the rig is actually
  // ready — if the scene never mounts or the controls are missing, the
  // request expires harmlessly instead of throwing.
  const [sweepArmed, setSweepArmed] = useState(false);
  useEffect(() => {
    if (!consumeIntroSweep()) return;
    setSweepArmed(true);
  }, []);

  useEffect(() => {
    if (!sweepArmed) return;
    const controls = controlsRef.current;
    // Scene not ready yet (canvas still initializing): skip safely. The
    // camera simply starts at its operational framing — no crash, no
    // partial gesture.
    if (!controls || !controls.object) {
      setSweepArmed(false);
      return;
    }
    tween.current = {
      active: true,
      t: 0,
      duration: INTRO_SWEEP_SEC,
      targetFrom: OPERATIONAL_TARGET.clone(),
      targetTo: OPERATIONAL_TARGET.clone(),
      posFrom: LANDING_HERO_POSITION.clone(),
      posTo: OPERATIONAL_POSITION.clone(),
    };
    // Jump to the landing's hero framing so the descent reads as one
    // continuous gesture from the journey above.
    controls.object.position.copy(LANDING_HERO_POSITION);
    setSweepArmed(false);
  }, [sweepArmed]);

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
    } else if (selection.kind === 'incident') {
      const inc = getLiveBuffer().incidents.find((i) => i.id === selection.id);
      if (inc) {
        x = inc.x;
        z = inc.z;
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
      duration: 0.6,
      targetFrom: controls.target.clone(),
      targetTo: new THREE.Vector3(x, 0, z),
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

    tw.t = Math.min(1, tw.t + dt / tw.duration);
    // easeInOutCubic — gentle departure, gentle arrival
    const k =
      tw.t < 0.5
        ? 4 * tw.t * tw.t * tw.t
        : 1 - Math.pow(-2 * tw.t + 2, 3) / 2;
    controls.target.lerpVectors(tw.targetFrom, tw.targetTo, k);

    // Intro sweep also glides camera position; selection focus only pans.
    if (tw.posFrom && tw.posTo && controls.object) {
      controls.object.position.lerpVectors(tw.posFrom, tw.posTo, k);
    }

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
