'use client';

import { useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { getLiveBuffer } from '@/lib/twin/live-buffer';

const MAX_INCIDENTS = 48;

/**
 * Active incident beacons (Phase 10B).
 * Flat crit-red rings on the ground plane. The shared pulse is the scene's
 * heartbeat — urgency is communicated by rhythm, not by noise.
 */
export default function Incidents() {
  const meshRef = useRef<THREE.InstancedMesh>(null);

  const workMatrix = useRef(new THREE.Matrix4());
  const workQuat = useRef(new THREE.Quaternion().setFromAxisAngle(
    new THREE.Vector3(1, 0, 0),
    -Math.PI / 2,
  ));
  const workPos = useRef(new THREE.Vector3());
  const workScale = useRef(new THREE.Vector3());

  useFrame(({ clock }) => {
    const mesh = meshRef.current;
    if (!mesh) return;

    const { incidents } = getLiveBuffer();
    const pulse = 1 + 0.14 * Math.sin(clock.elapsedTime * 2.4);

    let i = 0;
    for (const inc of incidents) {
      if (i >= MAX_INCIDENTS) break;
      workScale.current.setScalar(pulse);
      workPos.current.set(inc.x, 0.12, inc.z);
      workMatrix.current.compose(workPos.current, workQuat.current, workScale.current);
      mesh.setMatrixAt(i, workMatrix.current);
      i += 1;
    }
    if (i < MAX_INCIDENTS) {
      workScale.current.setScalar(0);
      workPos.current.set(0, -10, 0);
      for (; i < MAX_INCIDENTS; i++) {
        workMatrix.current.compose(workPos.current, workQuat.current, workScale.current);
        mesh.setMatrixAt(i, workMatrix.current);
      }
    }
    mesh.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, MAX_INCIDENTS]} frustumCulled={false}>
      <ringGeometry args={[0.85, 1.15, 40]} />
      <meshBasicMaterial color="#FF3655" transparent opacity={0.75} side={THREE.DoubleSide} depthWrite={false} />
    </instancedMesh>
  );
}
