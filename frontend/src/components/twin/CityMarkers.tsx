'use client';

import { useLayoutEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import type { ThreeEvent } from '@react-three/fiber';
import { HOSPITALS, STATIONS } from '@/lib/twin/city-data';
import { useTwinStore } from '@/lib/twin/store';

/**
 * Static city infrastructure markers (Phase 10B).
 * Hospitals: titanium octahedra — the only warm-metal elements in the scene,
 * reserved exclusively for clinical infrastructure.
 * Ambulance stations: low dark teal slabs flush with the ground plane.
 */
const TITANIUM = new THREE.Color('#D6B45A');
const STATION_TEAL = new THREE.Color('#0e5f54');

export function HospitalMarkers() {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const select = useTwinStore((s) => s.select);

  const matrices = useMemo(() => {
    const m = new THREE.Matrix4();
    return HOSPITALS.map((h) =>
      m.makeTranslation(h.x, 0.9, h.z).scale(new THREE.Vector3(1.4, 1.8, 1.4)).clone(),
    );
  }, []);

  useLayoutEffect(() => {
    const mesh = meshRef.current;
    if (!mesh) return;
    matrices.forEach((m, i) => mesh.setMatrixAt(i, m));
    mesh.instanceMatrix.needsUpdate = true;
  }, [matrices]);

  const handlePointerDown = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation();
    if (e.instanceId === undefined) return;
    select({ kind: 'hospital', id: HOSPITALS[e.instanceId].id });
  };

  return (
    <instancedMesh
      ref={meshRef}
      args={[undefined, undefined, HOSPITALS.length]}
      onPointerDown={handlePointerDown}
      frustumCulled={false}
    >
      <octahedronGeometry args={[0.55]} />
      <meshStandardMaterial
        color={TITANIUM}
        emissive={TITANIUM}
        emissiveIntensity={0.35}
        roughness={0.35}
        metalness={0.6}
      />
    </instancedMesh>
  );
}

export function StationMarkers() {
  const meshRef = useRef<THREE.InstancedMesh>(null);

  const matrices = useMemo(() => {
    const m = new THREE.Matrix4();
    return STATIONS.map((st) =>
      m.makeTranslation(st.x, 0.15, st.z).scale(new THREE.Vector3(1.1, 0.3, 1.1)).clone(),
    );
  }, []);

  useLayoutEffect(() => {
    const mesh = meshRef.current;
    if (!mesh) return;
    matrices.forEach((m, i) => mesh.setMatrixAt(i, m));
    mesh.instanceMatrix.needsUpdate = true;
  }, [matrices]);

  return (
    <instancedMesh
      ref={meshRef}
      args={[undefined, undefined, STATIONS.length]}
      frustumCulled={false}
    >
      <boxGeometry args={[1, 1, 1]} />
      <meshStandardMaterial color={STATION_TEAL} roughness={0.7} metalness={0.2} />
    </instancedMesh>
  );
}
