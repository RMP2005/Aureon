'use client';

import { useLayoutEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import type { ThreeEvent } from '@react-three/fiber';
import { advanceMotions, getLiveBuffer } from '@/lib/twin/live-buffer';
import { useTwinStore } from '@/lib/twin/store';

/**
 * Fleet layer — one InstancedMesh driven entirely from the transient live
 * buffer inside useFrame. Zero React re-renders per tick; positions ease
 * toward each engine snapshot (dead-reckoning between polls).
 *
 * Color = state, never decoration:
 *   available  → dim teal (dormant capacity)
 *   en_route   → bright teal glow (active response)
 *   at_scene   → amber (on scene)
 *   returning  → violet (repositioning)
 *   other      → slate
 */
const STATUS_COLORS: Record<string, THREE.Color> = {
  available: new THREE.Color('#0c7f70'),
  at_station: new THREE.Color('#0c7f70'),
  en_route: new THREE.Color('#16F2D4'),
  on_scene: new THREE.Color('#F5B841'),
  at_scene: new THREE.Color('#F5B841'),
  returning: new THREE.Color('#7C5CFF'),
  to_hospital: new THREE.Color('#16F2D4'),
};
const FALLBACK_COLOR = new THREE.Color('#4a5872');
const SELECTED_COLOR = new THREE.Color('#EDF2F7');
const UP = new THREE.Vector3(0, 1, 0);
const WORK_POS = new THREE.Vector3();

export default function Ambulances({ maxFleet = 64 }: { maxFleet?: number }) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const select = useTwinStore((s) => s.select);

  const workMatrix = useMemo(() => new THREE.Matrix4(), []);
  const workQuat = useMemo(() => new THREE.Quaternion(), []);
  const workScale = useMemo(() => new THREE.Vector3(1, 1, 1), []);
  const idList = useRef<string[]>([]);

  useLayoutEffect(() => {
    const mesh = meshRef.current;
    if (!mesh) return;
    // Hide unused instances by zero-scaling them once at mount.
    workScale.setScalar(0);
    for (let i = 0; i < maxFleet; i++) {
      WORK_POS.set(0, -10, 0); // park hidden beneath the plane
      workMatrix.compose(WORK_POS, workQuat, workScale);
      mesh.setMatrixAt(i, workMatrix);
      mesh.setColorAt(i, FALLBACK_COLOR);
    }
    workScale.setScalar(1);
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  }, [maxFleet, workMatrix, workQuat, workScale]);

  const handleClick = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation();
    const id = idList.current[e.instanceId ?? -1];
    if (id) select({ kind: 'ambulance', id });
  };

  useFrame((_, dt) => {
    const mesh = meshRef.current;
    if (!mesh) return;

    advanceMotions(dt);
    const buffer = getLiveBuffer();
    const selectedId = useTwinStore.getState().selection?.id ?? null;

    let i = 0;
    idList.current.length = 0;
    for (const m of buffer.ambulances.values()) {
      if (i >= maxFleet) break;

      workQuat.setFromAxisAngle(UP, Math.atan2(m.tx - m.x, m.tz - m.z));
      WORK_POS.set(m.x, 0.45, m.z);
      workMatrix.compose(WORK_POS, workQuat, workScale);
      mesh.setMatrixAt(i, workMatrix);

      const color =
        m.id === selectedId
          ? SELECTED_COLOR
          : (STATUS_COLORS[m.status] ?? FALLBACK_COLOR);
      mesh.setColorAt(i, color);

      idList.current.push(m.id);
      i += 1;
    }

    // Zero out the tail so stale instances vanish when fleet shrinks.
    if (i < maxFleet) {
      workScale.setScalar(0);
      WORK_POS.set(0, -10, 0);
      for (; i < maxFleet; i++) {
        workMatrix.compose(WORK_POS, workQuat, workScale);
        mesh.setMatrixAt(i, workMatrix);
      }
      workScale.setScalar(1);
    }

    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  });

  return (
    <instancedMesh
      ref={meshRef}
      args={[undefined, undefined, maxFleet]}
      onClick={handleClick}
      frustumCulled={false}
    >
      <capsuleGeometry args={[0.28, 0.55, 4, 10]} />
      <meshStandardMaterial roughness={0.3} metalness={0.15} />
    </instancedMesh>
  );
}
