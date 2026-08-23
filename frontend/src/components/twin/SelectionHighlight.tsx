'use client';

import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { getLiveBuffer } from '@/lib/twin/live-buffer';
import { useTwinStore } from '@/lib/twin/store';
import { HOSPITALS } from '@/lib/twin/city-data';

/**
 * Selection highlight — a single ring that tracks the selected entity.
 * White for fleet (readable against teal), titanium for hospitals.
 */
const RING_COLOR_FLEET = new THREE.Color('#EDF2F7');
const RING_COLOR_HOSPITAL = new THREE.Color('#D6B45A');

export default function SelectionHighlight() {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const selection = useTwinStore((s) => s.selection);

  const matrix = useRef(new THREE.Matrix4());
  const quat = useRef(new THREE.Quaternion().setFromAxisAngle(
    new THREE.Vector3(1, 0, 0),
    -Math.PI / 2,
  ));
  const pos = useRef(new THREE.Vector3());
  const scale = useRef(new THREE.Vector3(1, 1, 1));

  useLayoutColorEffect(meshRef, selection);

  useFrame(({ clock }) => {
    const mesh = meshRef.current;
    if (!mesh || !selection) return;

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
    const pulse = 1 + 0.08 * Math.sin(clock.elapsedTime * 4);
    scale.current.setScalar(pulse);
    pos.current.set(x, 0.14, z);
    matrix.current.compose(pos.current, quat.current, scale.current);
    mesh.setMatrixAt(0, matrix.current);
    mesh.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, 1]} frustumCulled={false}>
      <ringGeometry args={[1.15, 1.35, 48]} />
      <meshBasicMaterial
        color={selection?.kind === 'hospital' ? RING_COLOR_HOSPITAL : RING_COLOR_FLEET}
        transparent
        opacity={selection ? 0.9 : 0}
        side={THREE.DoubleSide}
        depthWrite={false}
      />
    </instancedMesh>
  );
}

/** Hide the ring entirely when nothing is selected (matrix parked). */
function useLayoutColorEffect(
  meshRef: React.RefObject<THREE.InstancedMesh | null>,
  selection: ReturnType<typeof useTwinStore.getState>['selection'],
) {
  useEffect(() => {
    const mesh = meshRef.current;
    if (!mesh) return;
    const m = new THREE.Matrix4();
    if (selection === null) {
      m.makeScale(0, 0, 0);
      mesh.setMatrixAt(0, m.setPosition(new THREE.Vector3(0, -10, 0)));
    }
    mesh.instanceMatrix.needsUpdate = true;
  }, [meshRef, selection]);
}
