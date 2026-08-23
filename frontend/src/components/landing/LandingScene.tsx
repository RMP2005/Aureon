'use client';

import { useLayoutEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import { useFrame, useThree } from '@react-three/fiber';
import { getRoadBuffer } from '@/lib/twin/city-data';
import { safeProject } from '@/lib/twin/projection';
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
      <NetworkActivity />
      <EpilogueTopology />
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
        if (!buffer) return null;
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
      }).filter(
        (t): t is (typeof TIER_WINDOWS)[number] & {
          geometry: THREE.BufferGeometry;
          totalVertices: number;
        } => t !== null,
      ),
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

// --- Network activity ----------------------------------------------------
// Replaces the old placeholder capsules ("teal blobs") with data-driven
// system pulses: stride-sampled midpoints of REAL arterial segments, each
// breathing as a low ring on the ground plane — a living twin, not decor.
// No particles, no glow layers; brightness carries the activity.

const PULSE_COUNT = 22;

// --- Static data (non-interactive film props) ----------------------------

const CITY_SEG = CITY_DATA.segments as unknown as [number, number, number, number, number][];
const CITY_SEG_COUNT = CITY_SEG.length;

function toWorld(lng: number, lat: number) {
  const [x, z] = safeProject(lng, lat);
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
const PULSE_SPOTS = (() => {
  const spots: { x: number; z: number; phase: number; appearAt: number }[] = [];
  for (let i = 0; spots.length < PULSE_COUNT && i < 40000; i++) {
    const idx = (i * 697 + 1301) % Math.max(1, CITY_SEG_COUNT);
    const seg = CITY_SEG[idx];
    if (!seg) continue;
    if (![seg[0], seg[1], seg[2], seg[3]].every(Number.isFinite)) continue;
    const [x, z] = safeProject((seg[0] + seg[2]) / 2, (seg[1] + seg[3]) / 2);
    if (!Number.isFinite(x) || !Number.isFinite(z)) continue;
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

function NetworkActivity() {
  const meshRef = useRef<THREE.InstancedMesh>(null);

  const workMatrix = useRef(new THREE.Matrix4());
  const workQuat = useRef(
    new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), -Math.PI / 2),
  );
  const workPos = useRef(new THREE.Vector3());
  const workScaleV = useRef(new THREE.Vector3());
  const workColor = useRef(new THREE.Color());

  useLayoutEffect(() => {
    const mesh = meshRef.current;
    if (!mesh) return;
    // Park every instance hidden until the activity window opens.
    workPos.current.set(0, -10, 0);
    workScaleV.current.setScalar(0.0001);
    for (let i = 0; i < PULSE_SPOTS.length; i++) {
      workMatrix.current.compose(workPos.current, workQuat.current, workScaleV.current);
      mesh.setMatrixAt(i, workMatrix.current);
      mesh.setColorAt(i, new THREE.Color('#16F2D4'));
    }
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  }, []);

  useFrame(({ clock }) => {
    const mesh = meshRef.current;
    if (!mesh) return;
    const p = getLandingProgress();
    const t = clock.elapsedTime;

    // Epilogue handoff: pulses settle as the topology structure rises.
    const out = 1 - window01(p, [0.86, 0.93]);

    for (let i = 0; i < PULSE_SPOTS.length; i++) {
      const u = PULSE_SPOTS[i];
      const on = p >= u.appearAt ? 1 : 0;
      // Gentle sonar-like breath, phase-offset per node.
      const pulse = 0.5 + 0.5 * Math.sin(t * 1.4 + u.phase);
      const s = (0.55 + pulse * 0.75) * on * Math.max(0.0001, out);
      workScaleV.current.setScalar(s);
      workPos.current.set(u.x, 0.12, u.z);
      workMatrix.current.compose(workPos.current, workQuat.current, workScaleV.current);
      mesh.setMatrixAt(i, workMatrix.current);
      // Brightness carries the beat — no glow layers.
      const b = 0.22 + 0.5 * pulse * on * out;
      workColor.current.setScalar(b);
      mesh.setColorAt(i, workColor.current);
    }
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  });

  return (
    <instancedMesh
      ref={meshRef}
      args={[undefined, undefined, PULSE_COUNT]}
      frustumCulled={false}
    >
      <ringGeometry args={[0.72, 0.88, 32]} />
      <meshBasicMaterial color="#ffffff" toneMapped={false} transparent opacity={0.85} depthWrite={false} side={THREE.DoubleSide} />
    </instancedMesh>
  );
}

// --- Epilogue: district topology -----------------------------------------
// Replaces the old abstract capsule blobs with a structure that reads as
// the twin itself: titanium infrastructure rings traced at real city
// radii, a teal active-systems core, and radial survey spokes. Violet and
// red are absent by contract — nothing here reasons, nothing bleeds.

const RING_RADII = [16, 28, 40, 52];
const SPOKE_COUNT = 12;

function ringGeometry(radius: number): THREE.BufferGeometry {
  const pts: number[] = [];
  const N = 96;
  for (let i = 0; i < N; i++) {
    const a1 = (i / N) * Math.PI * 2;
    const a2 = ((i + 1) / N) * Math.PI * 2;
    pts.push(
      Math.cos(a1) * radius,
      Math.sin(a1) * radius,
      Math.cos(a2) * radius,
      Math.sin(a2) * radius,
    );
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pts), 2));
  geo.applyMatrix4(new THREE.Matrix4().makeRotationX(Math.PI / 2));
  return geo;
}

function EpilogueTopology() {
  const group = useRef<THREE.Group>(null);
  const coreRef = useRef<THREE.Mesh>(null);

  const rings = useMemo(
    () => RING_RADII.map((r) => ({ r, geo: ringGeometry(r) })),
    [],
  );
  const spokes = useMemo(() => {
    const pts: number[] = [];
    for (let i = 0; i < SPOKE_COUNT; i++) {
      const a = (i / SPOKE_COUNT) * Math.PI * 2;
      pts.push(
        Math.cos(a) * RING_RADII[0],
        Math.sin(a) * RING_RADII[0],
        Math.cos(a) * RING_RADII[RING_RADII.length - 1],
        Math.sin(a) * RING_RADII[RING_RADII.length - 1],
      );
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(pts), 2));
    geo.applyMatrix4(new THREE.Matrix4().makeRotationX(Math.PI / 2));
    return geo;
  }, []);

  useFrame(({ clock }) => {
    const p = getLandingProgress();
    const k = ramp(p, 0.87, 0.99);
    if (group.current) {
      group.current.scale.setScalar(Math.max(0.0001, k));
      group.current.position.y = -(1 - k) * 3;
    }
    // The core breathes — the twin is awake (state, not decoration).
    if (coreRef.current) {
      const s = 1 + 0.1 * Math.sin(clock.elapsedTime * 1.8);
      coreRef.current.scale.setScalar(s);
    }
  });

  return (
    <group ref={group}>
      {rings.map(({ r, geo }) => (
        <lineSegments key={r} geometry={geo} frustumCulled={false}>
          <lineBasicMaterial color="#D6B45A" transparent opacity={0.34} depthWrite={false} />
        </lineSegments>
      ))}
      <lineSegments geometry={spokes} frustumCulled={false}>
        <lineBasicMaterial color="#4a5872" transparent opacity={0.22} depthWrite={false} />
      </lineSegments>
      <mesh ref={coreRef} position={[0, 0.6, 0]}>
        <octahedronGeometry args={[1.1]} />
        <meshStandardMaterial
          color="#16F2D4"
          emissive="#16F2D4"
          emissiveIntensity={0.5}
          roughness={0.3}
          metalness={0.1}
        />
      </mesh>
    </group>
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

