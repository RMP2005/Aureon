'use client';

import { useLayoutEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import type { ThreeEvent } from '@react-three/fiber';
import { HOSPITALS, STATIONS } from '@/lib/twin/city-data';
import { useTwinStore } from '@/lib/twin/store';

/**
 * Static city infrastructure markers.
 *
 * Hospitals: small blue glowing beacons at fixed real locations — soft,
 * premium, instantly readable as infrastructure. A ground halo carries the
 * "soft glow"; base emissive keeps them legible at close zoom.
 *
 * Ambulance stations: flat teal pads on the ground plane
 * (transport network owns teal).
 */
const INFRA_BLUE = new THREE.Color('#4da3ff');
const STATION_TEAL = new THREE.Color('#0e6e60');

export function HospitalMarkers() {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const haloRef = useRef<THREE.InstancedMesh>(null);
  const pillarRef = useRef<THREE.InstancedMesh>(null);
  const select = useTwinStore((s) => s.select);

  const matrices = useMemo(() => {
    const m = new THREE.Matrix4();
    return HOSPITALS.map((h) => m.makeTranslation(h.x, 1.0, h.z).clone());
  }, []);

  const haloMatrices = useMemo(() => {
    const q = new THREE.Quaternion().setFromAxisAngle(
      new THREE.Vector3(1, 0, 0),
      -Math.PI / 2,
    );
    return HOSPITALS.map((h) =>
      new THREE.Matrix4().compose(
        new THREE.Vector3(h.x, 0.07, h.z),
        q,
        new THREE.Vector3(2.6, 2.6, 2.6),
      ),
    );
  }, []);

  // Slim vertical light pillar rising through each beacon — reads as a
  // facility marker, not a random dot.
  const pillarMatrices = useMemo(
    () =>
      HOSPITALS.map((h) =>
        new THREE.Matrix4()
          .makeTranslation(h.x, 1.05, h.z)
          .scale(new THREE.Vector3(1, 1.9, 1))
          .clone(),
      ),
    [],
  );

  useLayoutEffect(() => {
    if (meshRef.current) {
      matrices.forEach((m, i) => meshRef.current!.setMatrixAt(i, m));
      meshRef.current.instanceMatrix.needsUpdate = true;
    }
    if (haloRef.current) {
      haloMatrices.forEach((m, i) => haloRef.current!.setMatrixAt(i, m));
      haloRef.current.instanceMatrix.needsUpdate = true;
    }
    if (pillarRef.current) {
      pillarMatrices.forEach((m, i) => pillarRef.current!.setMatrixAt(i, m));
      pillarRef.current.instanceMatrix.needsUpdate = true;
    }
  }, [matrices, haloMatrices, pillarMatrices]);

  const handlePointerDown = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation();
    if (e.instanceId === undefined) return;
    select({ kind: 'hospital', id: HOSPITALS[e.instanceId].id });
  };

  return (
    <>
      {/* Small glowing sphere — a beacon, never a block. */}
      <instancedMesh
        ref={meshRef}
        args={[undefined, undefined, HOSPITALS.length]}
        onPointerDown={handlePointerDown}
        frustumCulled={false}
      >
        <sphereGeometry args={[0.42, 20, 16]} />
        <meshStandardMaterial
          color={INFRA_BLUE}
          /* Base readability emissive: markers stay legible when the camera
             dives in. Occupancy state still owns any stronger glow once bed
             telemetry reaches the scene. */
          emissive={INFRA_BLUE}
          emissiveIntensity={0.55}
          roughness={0.35}
          metalness={0.1}
        />
      </instancedMesh>
      {/* Slim light pillar — facility presence, not a random dot. */}
      <instancedMesh
        ref={pillarRef}
        args={[undefined, undefined, HOSPITALS.length]}
        frustumCulled={false}
      >
        <cylinderGeometry args={[0.05, 0.05, 1, 8]} />
        <meshBasicMaterial
          color={INFRA_BLUE}
          transparent
          opacity={0.35}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </instancedMesh>
      {/* Soft glow disc under each site — presence, not decoration. */}
      <instancedMesh
        ref={haloRef}
        args={[undefined, undefined, HOSPITALS.length]}
        frustumCulled={false}
      >
        <circleGeometry args={[0.5, 24]} />
        <meshBasicMaterial
          color={INFRA_BLUE}
          transparent
          opacity={0.12}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
          side={THREE.DoubleSide}
        />
      </instancedMesh>
    </>
  );
}

export function StationMarkers() {
  const meshRef = useRef<THREE.InstancedMesh>(null);

  const matrices = useMemo(() => {
    const q = new THREE.Quaternion().setFromAxisAngle(
      new THREE.Vector3(1, 0, 0),
      -Math.PI / 2,
    );
    return STATIONS.map((st) =>
      new THREE.Matrix4().compose(
        new THREE.Vector3(st.x, 0.06, st.z),
        q,
        new THREE.Vector3(1.15, 1.15, 1.15),
      ),
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
      <circleGeometry args={[0.8, 24]} />
      <meshBasicMaterial
        color={STATION_TEAL}
        transparent
        opacity={0.75}
        side={THREE.DoubleSide}
        depthWrite={false}
      />
    </instancedMesh>
  );
}
