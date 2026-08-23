'use client';

import { useLayoutEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import { useFrame, useThree } from '@react-three/fiber';
import { getRoadBuffer } from '@/lib/twin/city-data';
import { project } from '@/lib/twin/projection';
import { getLandingProgress } from '@/lib/landing/progress';
import CITY_DATA from '@/data/bangalore-city.json';

/**
 * Cinematic landing scene (Phase 10C).
 *
 * The city materializes as one continuous gesture driven solely by scroll
 * progress: arteries draw outward from the core, clinical infrastructure
 * rises last, the fleet wakes beneath it. No post-processing, no particles —
 * the drama is choreography of real city data.
 */

// --- Materialization windows (progress space) ---------------------------
const TIER_WINDOWS = [
  { tier: 0, start: 0.02, end: 0.26, finalOpacity: 0.85 },
  { tier: 1, start: 0.2, end: 0.48, finalOpacity: 0.5 },
  { tier: 2, start: 0.4, end: 0.68, finalOpacity: 0.22 },
] as const;

const HOSPITAL_WINDOW: [number, number] = [0.52, 0.64];
const STATION_WINDOW: [number, number] = [0.56, 0.68];
const FLEET_WINDOW: [number, number] = [0.58, 0.82];

const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);
const easeInOutSine = (t: number) => 0.5 - Math.cos(Math.PI * t) / 2;
const window01 = (p: number, w: readonly [number, number]) =>
  Math.min(1, Math.max(0, (p - w[0]) / (w[1] - w[0])));
const ramp = (p: number, a: number, b: number) =>
  easeOutCubic(Math.min(1, Math.max(0, (p - a) / (b - a))));

/** Camera glide path through the journey (top-down void → hero wide). */
const CAMERA_PATH = new THREE.CatmullRomCurve3(
  [
    new THREE.Vector3(0, 165, 8),
    new THREE.Vector3(6, 118, 46),
    new THREE.Vector3(30, 72, 92),
    new THREE.Vector3(-20, 40, 70),
    new THREE.Vector3(10, 30, 58),
    new THREE.Vector3(0, 76, 100),
  ],
  false,
  'catmullrom',
  0.35,
);

const TARGET_PATH = new THREE.CatmullRomCurve3([
  new THREE.Vector3(0, 0, 0),
  new THREE.Vector3(-4, 0, 2),
  new THREE.Vector3(6, 0, -6),
  new THREE.Vector3(-8, 0, 4),
  new THREE.Vector3(4, 0, -2),
  new THREE.Vector3(0, 0, 0),
]);

export default function LandingScene() {
  return (
    <>
      <color attach="background" args={['#05070D']} />
      <fog attach="fog" args={['#05070D', 130, 380]} />
      <LightRig />
      <MaterializingCity />
      <RisingInfrastructure />
      <AwakeningFleet />
      <CinematicCamera />
    </>
  );
}

function LightRig() {
  const hemiRef = useRef<THREE.HemisphereLight>(null);
  const dirRef = useRef<THREE.DirectionalLight>(null);

  useFrame(() => {
    const k = ramp(getLandingProgress(), 0.05, 0.55);
    if (hemiRef.current) hemiRef.current.intensity = 0.12 + k * 0.38;
    if (dirRef.current) dirRef.current.intensity = 0.15 + k * 0.4;
  });

  return (
    <>
      <hemisphereLight ref={hemiRef} args={['#1a2436', '#05070D', 0.12]} />
      <directionalLight
        ref={dirRef}
        position={[40, 90, 25]}
        intensity={0.15}
        color="#c9d6ea"
      />
    </>
  );
}

const TIER_TINTS: Record<number, string> = {
  0: '#8fa3bf',
  1: '#6b7d99',
  2: '#4a5872',
};

function MaterializingCity() {
  const tiers = useMemo(
    () =>
      TIER_WINDOWS.map(({ tier, start, end, finalOpacity }) => {
        const buffer = getRoadBuffer(tier);
        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(buffer, 2));
        geometry.applyMatrix4(new THREE.Matrix4().makeRotationX(Math.PI / 2));
        geometry.setDrawRange(0, 0);
        return {
          tier,
          start,
          end,
          finalOpacity,
          geometry,
          totalVertices: buffer.length / 2,
        };
      }),
    [],
  );

  const meshRefs = useRef<(THREE.LineSegments | null)[]>([]);

  useFrame(() => {
    const p = getLandingProgress();
    for (let i = 0; i < tiers.length; i++) {
      const t = tiers[i];
      const k = window01(p, [t.start, t.end]);
      // drawRange counts vertices; keep them paired for LineSegments
      t.geometry.setDrawRange(
        0,
        Math.floor((k * t.totalVertices) / 2) * 2,
      );
      const mesh = meshRefs.current[i];
      if (mesh) {
        (mesh.material as THREE.LineBasicMaterial).opacity =
          k * t.finalOpacity;
      }
    }
  });

  return (
    <>
      {tiers.map((t, i) => (
        <lineSegments
          key={t.tier}
          geometry={t.geometry}
          frustumCulled={false}
          ref={(el) => {
            meshRefs.current[i] = el;
          }}
        >
          <lineBasicMaterial
            color={TIER_TINTS[t.tier]}
            transparent
            opacity={0}
            depthWrite={false}
          />
        </lineSegments>
      ))}
    </>
  );
}

function RisingInfrastructure() {
  const hospGroup = useRef<THREE.Group>(null);
  const stnGroup = useRef<THREE.Group>(null);

  useFrame(() => {
    const p = getLandingProgress();
    const hk = ramp(p, HOSPITAL_WINDOW[0], HOSPITAL_WINDOW[1]);
    if (hospGroup.current) {
      hospGroup.current.scale.setScalar(Math.max(0.0001, hk));
      hospGroup.current.position.y = -(1 - hk) * 2.5;
    }
    const sk = ramp(p, STATION_WINDOW[0], STATION_WINDOW[1]);
    if (stnGroup.current) {
      stnGroup.current.scale.setScalar(Math.max(0.0001, sk));
      stnGroup.current.position.y = -(1 - sk) * 0.8;
    }
  });

  return (
    <>
      <group ref={hospGroup}>
        <HospitalPins />
      </group>
      <group ref={stnGroup}>
        <StationSlabs />
      </group>
    </>
  );
}

function HospitalPins() {
  const ref = useRef<THREE.InstancedMesh>(null);
  const mats = useMemo(
    () =>
      HOSPITAL_LANDING.map((h) =>
        new THREE.Matrix4()
          .makeTranslation(h.x, 0.9, h.z)
          .scale(new THREE.Vector3(1.5, 2, 1.5))
          .clone(),
      ),
    [],
  );
  applyMatricesOnMount(ref, mats);
  return (
    <instancedMesh
      ref={ref}
      args={[undefined, undefined, HOSPITAL_LANDING.length]}
      frustumCulled={false}
    >
      <octahedronGeometry args={[0.55]} />
      <meshStandardMaterial
        color="#D6B45A"
        roughness={0.35}
        metalness={0.6}
        emissiveIntensity={0}
      />
    </instancedMesh>
  );
}

function StationSlabs() {
  const ref = useRef<THREE.InstancedMesh>(null);
  const mats = useMemo(
    () =>
      STATION_LANDING.map((s) =>
        new THREE.Matrix4()
          .makeTranslation(s.x, 0.15, s.z)
          .scale(new THREE.Vector3(1.1, 0.3, 1.1))
          .clone(),
      ),
    [],
  );
  applyMatricesOnMount(ref, mats);
  return (
    <instancedMesh
      ref={ref}
      args={[undefined, undefined, STATION_LANDING.length]}
      frustumCulled={false}
    >
      <boxGeometry args={[1, 1, 1]} />
      <meshStandardMaterial color="#0e5f54" roughness={0.7} metalness={0.2} />
    </instancedMesh>
  );
}

function applyMatricesOnMount(
  ref: React.RefObject<THREE.InstancedMesh | null>,
  mats: THREE.Matrix4[],
) {
  useLayoutEffect(() => {
    const mesh = ref.current;
    if (!mesh) return;
    mats.forEach((m, i) => mesh.setMatrixAt(i, m));
    mesh.instanceMatrix.needsUpdate = true;
  }, [mats, ref]);
}

// --- The fleet awakens ---------------------------------------------------

const FLEET_COUNT = 22;

// --- Static data (non-interactive film props) ----------------------------

const CITY_SEG = CITY_DATA.segments as unknown as [number, number, number, number, number][];
const CITY_SEG_COUNT = CITY_SEG.length;

function toWorld(lng: number, lat: number) {
  const [x, z] = project(lng, lat);
  return { x, z };
}

const HOSPITAL_LANDING = CITY_DATA.hospitals.map((h) => ({
  ...h,
  ...toWorld(h.lng, h.lat),
}));

const STATION_LANDING = CITY_DATA.stations.map((s) => ({
  ...s,
  ...toWorld(s.lng, s.lat),
}));

/** Deterministic scatter: stride-sampled arterial midpoints across the grid. */
const FLEET_SPOTS = (() => {
  const spots: { x: number; z: number; phase: number; appearAt: number }[] = [];
  for (let i = 0; spots.length < FLEET_COUNT && i < 40000; i++) {
    const idx = (i * 697 + 1301) % Math.max(1, CITY_SEG_COUNT);
    const seg = CITY_SEG[idx];
    if (!seg) continue;
    const [x, z] = project((seg[0] + seg[2]) / 2, (seg[1] + seg[3]) / 2);
    const n = spots.length;
    spots.push({
      x,
      z,
      phase: (n * 137.5 * Math.PI) / 180,
      appearAt:
        FLEET_WINDOW[0] +
        (((n * 61) % 97) / 97) * (FLEET_WINDOW[1] - FLEET_WINDOW[0]),
    });
  }
  return spots;
})();

function AwakeningFleet() {
  const meshRef = useRef<THREE.InstancedMesh>(null);

  const workMatrix = useRef(new THREE.Matrix4());
  const workQuat = useRef(new THREE.Quaternion());
  const workPos = useRef(new THREE.Vector3());
  const workScaleV = useRef(new THREE.Vector3());
  const UP = useRef(new THREE.Vector3(0, 1, 0));

  useFrame(({ clock }) => {
    const mesh = meshRef.current;
    if (!mesh) return;
    const p = getLandingProgress();
    const t = clock.elapsedTime;

    for (let i = 0; i < FLEET_SPOTS.length; i++) {
      const u = FLEET_SPOTS[i];
      const k = p >= u.appearAt ? easeOutCubic((p - u.appearAt) / 0.08) : 0;
      const bob = k === 1 ? Math.sin(t * 1.3 + u.phase) * 0.07 : 0;
      workScaleV.current.setScalar(Math.max(0.0001, k));
      workPos.current.set(u.x, 0.45 + bob, u.z);
      workQuat.current.setFromAxisAngle(UP.current, Math.sin(u.phase) * Math.PI);
      workMatrix.current.compose(workPos.current, workQuat.current, workScaleV.current);
      mesh.setMatrixAt(i, workMatrix.current);
    }
    mesh.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh
      ref={meshRef}
      args={[undefined, undefined, FLEET_COUNT]}
      frustumCulled={false}
    >
      <capsuleGeometry args={[0.28, 0.55, 4, 10]} />
      {/* Fleet glow is state: units are "on watch" in this film */}
      <meshStandardMaterial
        color="#16F2D4"
        roughness={0.3}
        metalness={0.15}
        emissive="#16F2D4"
        emissiveIntensity={0.25}
      />
    </instancedMesh>
  );
}

// --- Camera --------------------------------------------------------------

function CinematicCamera() {
  const camera = useThree((s) => s.camera);
  const desiredPos = useRef(new THREE.Vector3());
  const desiredTarget = useRef(new THREE.Vector3());
  const currentTarget = useRef(new THREE.Vector3());

  useFrame((_, dt) => {
    const e = easeInOutSine(getLandingProgress());
    CAMERA_PATH.getPoint(e, desiredPos.current);
    TARGET_PATH.getPoint(e, desiredTarget.current);

    const k = 1 - Math.exp(-3.2 * dt);
    camera.position.lerp(desiredPos.current, k);
    currentTarget.current.lerp(desiredTarget.current, k);
    camera.lookAt(currentTarget.current);
  });

  return null;
}

