'use client';

import { useLayoutEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import CITY_DATA from '@/data/bangalore-city.json';
import { safeProject } from '@/lib/twin/projection';

/**
 * Route flow layer — twin edition.
 *
 * Teal packets streaming along real arterial segments: the movement
 * language that keeps the network legible between runs. Independent of
 * engine state; the map key's ROUTE FLOW row always has a real layer
 * behind it.
 */

const ROUTE_COUNT = 14;
const DOTS_PER_ROUTE = 7;
const TOTAL = ROUTE_COUNT * DOTS_PER_ROUTE;

interface FlowRoute {
  ax: number;
  az: number;
  bx: number;
  bz: number;
}

const ROUTES: FlowRoute[] = (() => {
  const segs = CITY_DATA.segments as unknown as [
    number,
    number,
    number,
    number,
    number,
  ][];
  const picked: FlowRoute[] = [];
  let cursor = 419 % Math.max(1, segs.length);
  let guard = 0;
  while (picked.length < ROUTE_COUNT && guard < 80_000) {
    guard += 1;
    cursor = (cursor + 691) % segs.length;
    const s = segs[cursor];
    if (!s || ![s[0], s[1], s[2], s[3]].every(Number.isFinite)) continue;
    const [ax, az] = safeProject(s[0], s[1]);
    const [bx, bz] = safeProject(s[2], s[3]);
    if (![ax, az, bx, bz].every(Number.isFinite)) continue;
    const len = Math.hypot(bx - ax, bz - az);
    if (len < 5 || len > 38) continue; // readable city-block routes
    picked.push({ ax, az, bx, bz });
  }
  return picked;
})();

export default function RouteFlowLayer() {
  const meshRef = useRef<THREE.InstancedMesh>(null);

  // Reusable work objects — zero per-frame allocation.
  const workMatrix = useMemo(() => new THREE.Matrix4(), []);
  const workPos = useMemo(() => new THREE.Vector3(), []);
  const workQuat = useMemo(
    () =>
      new THREE.Quaternion().setFromAxisAngle(
        new THREE.Vector3(1, 0, 0),
        -Math.PI / 2,
      ),
    [],
  );
  const workScale = useMemo(() => new THREE.Vector3(), []);
  const workColor = useMemo(() => new THREE.Color(), []);

  // Park every instance far below the plane until the first tick.
  useLayoutEffect(() => {
    const mesh = meshRef.current;
    if (!mesh) return;
    workPos.set(0, -10, 0);
    workScale.setScalar(0.0001);
    for (let i = 0; i < TOTAL; i++) {
      workMatrix.compose(workPos, workQuat, workScale);
      mesh.setMatrixAt(i, workMatrix);
      mesh.setColorAt(i, new THREE.Color('#16F2D4'));
    }
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  }, [workMatrix, workPos, workQuat, workScale]);

  useFrame(({ clock }) => {
    const mesh = meshRef.current;
    if (!mesh || ROUTES.length === 0) return;
    const t = clock.elapsedTime;

    for (let r = 0; r < ROUTES.length; r++) {
      const route = ROUTES[r];
      // Per-route speed keeps streams desynchronized.
      const speed = 0.045 + (((r * 37) % 23) / 23) * 0.04;

      for (let d = 0; d < DOTS_PER_ROUTE; d++) {
        const i = r * DOTS_PER_ROUTE + d;
        const u = (t * speed + d / DOTS_PER_ROUTE) % 1;
        const fadeEdge = Math.min(1, u * 8, (1 - u) * 8);
        const s = 0.15 * fadeEdge;

        workPos.set(
          route.ax + (route.bx - route.ax) * u,
          0.09,
          route.az + (route.bz - route.az) * u,
        );
        workScale.setScalar(Math.max(0.0001, s));
        workMatrix.compose(workPos, workQuat, workScale);
        mesh.setMatrixAt(i, workMatrix);

        const b = fadeEdge * (0.55 + 0.25 * Math.sin(t * 2 + i));
        workColor.setRGB(0.06 * b, 0.75 * b, 0.64 * b);
        mesh.setColorAt(i, workColor);
      }
    }
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  });

  return (
    <instancedMesh
      ref={meshRef}
      args={[undefined, undefined, TOTAL]}
      frustumCulled={false}
    >
      <circleGeometry args={[1, 10]} />
      <meshBasicMaterial
        transparent
        opacity={0.85}
        side={THREE.DoubleSide}
        depthWrite={false}
      />
    </instancedMesh>
  );
}
