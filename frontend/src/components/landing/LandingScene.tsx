'use client';

import { useLayoutEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import { useFrame, useThree } from '@react-three/fiber';
import { createRoadGeometry } from '@/lib/twin/city-data';
import { safeProject } from '@/lib/twin/projection';
import { getLandingProgress } from '@/lib/landing/progress';
import CITY_DATA from '@/data/bangalore-city.json';

/**
 * Cinematic landing scene (Phase 11H).
 *
 * The final reveal is the city itself awakening — no abstract shapes:
 *   roads draw outward from the core (primary routes brightest),
 *   hospitals rise as gold markers, ambulance bases settle teal,
 *   patrol units begin moving along real arteries,
 *   emergency beacons pulse at true street midpoints,
 *   response-zone boundaries surface last.
 *
 * Every object is a real dataset feature. Red appears only where
 * emergencies live; violet never appears here — nothing reasons yet.
 */

// --- Materialization windows (progress space) ---------------------------
// Roads stay a BACKGROUND layer — dim grey-white, never competing with the
// wordmark. Brightness only lifts gently through the final convergence.
const TIER_WINDOWS = [
  { tier: 0, start: 0.02, end: 0.26, finalOpacity: 0.58 },
  { tier: 1, start: 0.2, end: 0.48, finalOpacity: 0.32 },
  { tier: 2, start: 0.4, end: 0.68, finalOpacity: 0.14 },
] as const;

const ORB_WINDOW: [number, number] = [0.12, 0.38];
const HOSPITAL_WINDOW: [number, number] = [0.52, 0.64];
const STATION_WINDOW: [number, number] = [0.56, 0.68];
const FLEET_WINDOW: [number, number] = [0.58, 0.82];
const INCIDENT_WINDOW: [number, number] = [0.74, 0.9];

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
      {/* One world group — gathers toward center behind the title at the end */}
      <CityWorld>
        <MaterializingCity />
        <IntelligenceOrbs />
        <RisingInfrastructure />
        <PatrolFleet />
        <RouteFlow />
        <IncidentBeacons />
      </CityWorld>
      <CinematicCamera />
    </>
  );
}

/**
 * Hero convergence (final scroll): the entire city gently contracts toward
 * its centroid while brightening — elements gather behind the Aureon
 * title like a command-center visualization taking command of the frame.
 */
function CityWorld({ children }: { children: React.ReactNode }) {
  const group = useRef<THREE.Group>(null);
  useFrame(() => {
    const k = easeOutCubic(window01(getLandingProgress(), [0.86, 1]));
    if (group.current) group.current.scale.setScalar(1 - 0.055 * k);
  });
  return <group ref={group}>{children}</group>;
}

function LightRig() {
  const hemiRef = useRef<THREE.HemisphereLight>(null);
  const dirRef = useRef<THREE.DirectionalLight>(null);

  useFrame(() => {
    const k = ramp(getLandingProgress(), 0.05, 0.55);
    if (hemiRef.current) hemiRef.current.intensity = 0.12 + k * 0.42;
    if (dirRef.current) dirRef.current.intensity = 0.15 + k * 0.45;
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

/* --- Roads ---------------------------------------------------------------
   The map is a background layer: thin soft-white routes over the void.
   Primary expressways read slightly brighter; secondaries recede. The
   city stays dim so gold-free branding, teal, blue and red own the frame. */

const TIER_TINTS: Record<number, string> = {
  0: '#aab8cf',
  1: '#74869f',
  2: '#46536b',
};

function MaterializingCity() {
  const tiers = useMemo(
    () =>
      TIER_WINDOWS.map(({ tier, start, end, finalOpacity }) => {
        // itemSize-3 XZ geometry, no applyMatrix4 — the matrix path poisons
        // itemSize-2 attributes with NaN on three r160+ and blanks the map.
        const geometry = createRoadGeometry(tier);
        if (!geometry) return null;
        geometry.setDrawRange(0, 0);
        return {
          tier,
          start,
          end,
          finalOpacity,
          geometry,
          totalVertices: geometry.getAttribute('position').count,
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
    // Hero convergence: a gentle lift only — the map must never outshine
    // the wordmark, even at the final reveal.
    const converge = window01(p, [0.86, 1]);
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
        const base = k * t.finalOpacity;
        (mesh.material as THREE.LineBasicMaterial).opacity = Math.min(
          1,
          base + converge * 0.05,
        );
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

/* --- Infrastructure -------------------------------------------------------
   Hospitals: small blue glowing markers at fixed real locations — no
   blocks, no pyramids. Bases: flat teal pads (transport network). */

const INFRA_BLUE = '#4da3ff';

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
        <HospitalMarkers />
      </group>
      <group ref={stnGroup}>
        <StationPads />
      </group>
    </>
  );
}

/** Hospital marker matrices; glow discs lie flat beneath them.
    Filled after HOSPITAL_LANDING is derived — see static data section. */
let HOSPITAL_MATRICES: THREE.Matrix4[] = [];
let HALO_MATRICES: THREE.Matrix4[] = [];
const GROUND_QUAT = new THREE.Quaternion().setFromAxisAngle(
  new THREE.Vector3(1, 0, 0),
  -Math.PI / 2,
);

function HospitalMarkers() {
  const bodyRef = useRef<THREE.InstancedMesh>(null);
  const haloRef = useRef<THREE.InstancedMesh>(null);

  useLayoutEffect(() => {
    if (bodyRef.current) {
      HOSPITAL_MATRICES.forEach((m, i) => bodyRef.current!.setMatrixAt(i, m));
      bodyRef.current.instanceMatrix.needsUpdate = true;
    }
    if (haloRef.current) {
      HALO_MATRICES.forEach((m, i) => haloRef.current!.setMatrixAt(i, m));
      haloRef.current.instanceMatrix.needsUpdate = true;
    }
  }, []);

  return (
    <>
      {/* Small glowing sphere — reads as a beacon, never as a block. */}
      <instancedMesh
        ref={bodyRef}
        args={[undefined, undefined, HOSPITAL_LANDING.length]}
        frustumCulled={false}
      >
        <sphereGeometry args={[0.42, 20, 16]} />
        <meshStandardMaterial
          color={INFRA_BLUE}
          emissive={INFRA_BLUE}
          emissiveIntensity={0.55}
          roughness={0.35}
          metalness={0.1}
        />
      </instancedMesh>
      {/* Soft glow: flat additive disc on the ground under each site. */}
      <instancedMesh
        ref={haloRef}
        args={[undefined, undefined, HOSPITAL_LANDING.length]}
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

function StationPads() {
  const ref = useRef<THREE.InstancedMesh>(null);
  const mats = useMemo(
    () =>
      STATION_LANDING.map((s) =>
        new THREE.Matrix4().compose(
          new THREE.Vector3(s.x, 0.06, s.z),
          GROUND_QUAT,
          new THREE.Vector3(1.15, 1.15, 1.15),
        ),
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
      <circleGeometry args={[0.8, 24]} />
      <meshBasicMaterial
        color="#0e6e60"
        transparent
        opacity={0.75}
        side={THREE.DoubleSide}
        depthWrite={false}
      />
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

// --- Static city data (non-interactive film props) ------------------------

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

// Hospital marker matrices — built here, after HOSPITAL_LANDING exists.
HOSPITAL_MATRICES = HOSPITAL_LANDING.map((h) =>
  new THREE.Matrix4().makeTranslation(h.x, 1.0, h.z).clone(),
);
HALO_MATRICES = HOSPITAL_LANDING.map((h) =>
  new THREE.Matrix4().compose(
    new THREE.Vector3(h.x, 0.07, h.z),
    GROUND_QUAT,
    new THREE.Vector3(2.6, 2.6, 2.6),
  ),
);

/**
 * Deterministic sample of long arterial segments (world space).
 * Used by both the patrol fleet (patrol paths) and the beacons
 * (incident sites). Stride-sampled so coverage spreads city-wide.
 */
function sampleArterialSegments(count: number, seedOffset: number) {
  const picked: { ax: number; az: number; bx: number; bz: number }[] = [];
  let cursor = seedOffset % Math.max(1, CITY_SEG_COUNT);
  let guard = 0;
  while (picked.length < count && guard < 120_000) {
    guard += 1;
    cursor = (cursor + 613) % CITY_SEG_COUNT;
    const seg = CITY_SEG[cursor];
    if (!seg || ![seg[0], seg[1], seg[2], seg[3]].every(Number.isFinite)) continue;
    const [ax, az] = safeProject(seg[0], seg[1]);
    const [bx, bz] = safeProject(seg[2], seg[3]);
    if (![ax, az, bx, bz].every(Number.isFinite)) continue;
    const len = Math.hypot(bx - ax, bz - az);
    if (len < 5 || len > 40) continue; // real city-block-scale arteries
    picked.push({ ax, az, bx, bz });
  }
  return picked;
}

/* --- Patrol fleet ----------------------------------------------------------
   Replaces the old abstract ground-rings ("empty circles") with what the
   rings were pretending to be: ambulances alive in the network. Each unit
   glides along a REAL arterial segment, oriented to its direction of
   travel — the same capsule visual language as the command twin. */

const FLEET_COUNT = 18;
const FLEET_SPOTS = sampleArterialSegments(FLEET_COUNT, 11);

const TILT_QUAT = new THREE.Quaternion().setFromAxisAngle(
  new THREE.Vector3(1, 0, 0),
  Math.PI / 2,
); // capsule Y-axis → lie along travel direction
const UP_Y = new THREE.Vector3(0, 1, 0);

interface FleetUnit {
  ax: number;
  az: number;
  bx: number;
  bz: number;
  len: number;
  speed: number;
  phase: number;
  appearAt: number;
}

const FLEET_UNITS: FleetUnit[] = FLEET_SPOTS.map((s, n) => {
  const len = Math.hypot(s.bx - s.ax, s.bz - s.az);
  return {
    ...s,
    len,
    speed: 2.2 + ((n * 37) % 23) / 23 * 1.8,
    phase: ((n * 149) % 360) / 360 * len * 2,
    appearAt:
      FLEET_WINDOW[0] +
      (((n * 61) % 97) / 97) * (FLEET_WINDOW[1] - FLEET_WINDOW[0]),
  };
});

function PatrolFleet() {
  const meshRef = useRef<THREE.InstancedMesh>(null);

  const workMatrix = useRef(new THREE.Matrix4());
  const workPos = useRef(new THREE.Vector3());
  const workQuatYaw = useRef(new THREE.Quaternion());
  const workQuat = useRef(new THREE.Quaternion());
  const workScale = useRef(new THREE.Vector3());
  const workColor = useRef(new THREE.Color());

  useLayoutEffect(() => {
    const mesh = meshRef.current;
    if (!mesh) return;
    workScale.current.setScalar(0.0001);
    workPos.current.set(0, -10, 0);
    for (let i = 0; i < FLEET_UNITS.length; i++) {
      workQuat.current.identity();
      workMatrix.current.compose(workPos.current, workQuat.current, workScale.current);
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

    for (let i = 0; i < FLEET_UNITS.length; i++) {
      const u = FLEET_UNITS[i];
      const on = p >= u.appearAt ? Math.min(1, (p - u.appearAt) * 24) : 0;

      // Ping-pong along the artery: 0→len→0.
      const d = (u.phase + t * u.speed) % (u.len * 2);
      const s = d <= u.len ? d : u.len * 2 - d;
      const dirForward = d <= u.len ? 1 : -1;

      const nx = (u.bx - u.ax) / u.len;
      const nz = (u.bz - u.az) / u.len;

      workPos.current.set(u.ax + nx * s, 0.42, u.az + nz * s);
      // Yaw about Y applied over the tilt that lays the capsule flat.
      const yaw = Math.atan2(nx * dirForward, nz * dirForward);
      workQuatYaw.current.setFromAxisAngle(UP_Y, yaw);
      workQuat.current.copy(workQuatYaw.current).multiply(TILT_QUAT);
      workScale.current.setScalar(Math.max(0.0001, on));

      workMatrix.current.compose(workPos.current, workQuat.current, workScale.current);
      mesh.setMatrixAt(i, workMatrix.current);

      // Idle-patrol teal; every sixth unit runs violet — a unit currently
      // dispatched by the decision engine (AI-reasoning color, per contract).
      const b = 0.55 + 0.18 * Math.sin(t * 1.1 + i * 1.7);
      if (i % 6 === 2) {
        workColor.current.setRGB(0.48 * b, 0.36 * b, 1.0 * b);
      } else {
        workColor.current.setRGB(0.05 * b, 0.62 * b, 0.55 * b);
      }
      mesh.setColorAt(i, workColor.current);
    }
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  });

  return (
    <instancedMesh
      ref={meshRef}
      args={[undefined, undefined, FLEET_UNITS.length]}
      frustumCulled={false}
    >
      <capsuleGeometry args={[0.19, 0.45, 4, 8]} />
      <meshStandardMaterial roughness={0.35} metalness={0.2} />
    </instancedMesh>
  );
}

/* --- Route flow ------------------------------------------------------------
   Animated dotted lines showing WHERE units move: small packets of light
   streaming along real arteries. The path language is self-explanatory —
   movement direction is visible without a legend. */

const ROUTE_COUNT = 9;
const DOTS_PER_ROUTE = 7;
const ROUTE_SPOTS = sampleArterialSegments(ROUTE_COUNT, 777);

const ROUTE_WINDOW: [number, number] = [0.5, 0.72];

interface FlowRoute {
  ax: number;
  az: number;
  bx: number;
  bz: number;
  len: number;
  speed: number; // fraction of the route per second
  appearAt: number;
}

const FLOW_ROUTES: FlowRoute[] = ROUTE_SPOTS.map((s, n) => ({
  ...s,
  len: Math.hypot(s.bx - s.ax, s.bz - s.az),
  speed: 0.05 + (((n * 41) % 29) / 29) * 0.045,
  appearAt:
    ROUTE_WINDOW[0] + (n / ROUTE_COUNT) * (ROUTE_WINDOW[1] - ROUTE_WINDOW[0]),
}));

function RouteFlow() {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const total = ROUTE_COUNT * DOTS_PER_ROUTE;

  const workMatrix = useRef(new THREE.Matrix4());
  const workQuat = useRef(
    new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), -Math.PI / 2),
  );
  const workPos = useRef(new THREE.Vector3());
  const workScale = useRef(new THREE.Vector3());
  const workColor = useRef(new THREE.Color());

  useLayoutEffect(() => {
    const mesh = meshRef.current;
    if (!mesh) return;
    workPos.current.set(0, -10, 0);
    workScale.current.setScalar(0.0001);
    for (let i = 0; i < total; i++) {
      workMatrix.current.compose(workPos.current, workQuat.current, workScale.current);
      mesh.setMatrixAt(i, workMatrix.current);
      mesh.setColorAt(i, new THREE.Color('#16F2D4'));
    }
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  }, [total]);

  useFrame(({ clock }) => {
    const mesh = meshRef.current;
    if (!mesh) return;
    const p = getLandingProgress();
    const t = clock.elapsedTime;

    for (let r = 0; r < FLOW_ROUTES.length; r++) {
      const route = FLOW_ROUTES[r];
      const on = p >= route.appearAt ? Math.min(1, (p - route.appearAt) * 18) : 0;

      for (let d = 0; d < DOTS_PER_ROUTE; d++) {
        const i = r * DOTS_PER_ROUTE + d;
        // Evenly spaced packets marching one-way along the artery.
        const u = (t * route.speed + d / DOTS_PER_ROUTE) % 1;
        const fadeEdge = Math.min(1, u * 8, (1 - u) * 8); // soften the ends
        const s = 0.16 * on * fadeEdge;

        workPos.current.set(
          route.ax + (route.bx - route.ax) * u,
          0.09,
          route.az + (route.bz - route.az) * u,
        );
        workScale.current.setScalar(Math.max(0.0001, s));
        workMatrix.current.compose(workPos.current, workQuat.current, workScale.current);
        mesh.setMatrixAt(i, workMatrix.current);

        const b = on * fadeEdge * (0.5 + 0.25 * Math.sin(t * 2 + i));
        workColor.current.setRGB(0.35 * b, 0.75 * b, 0.68 * b);
        mesh.setColorAt(i, workColor.current);
      }
    }
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  });

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, ROUTE_COUNT * DOTS_PER_ROUTE]} frustumCulled={false}>
      <circleGeometry args={[1, 10]} />
      <meshBasicMaterial transparent opacity={0.85} side={THREE.DoubleSide} depthWrite={false} />
    </instancedMesh>
  );
}

/* --- Incident beacons ------------------------------------------------------
   Red exists ONLY where an emergency is. Each beacon is a small red marker
   with a slow sonar ring; major incidents breathe wider than minor ones —
   severity reads through size and rhythm, nothing else. */

const BEACON_COUNT = 6;
const BEACON_SPOTS = sampleArterialSegments(BEACON_COUNT, 4703);

interface Beacon {
  x: number;
  z: number;
  major: boolean;
  phase: number;
  appearAt: number;
}

const BEACONS: Beacon[] = BEACON_SPOTS.map((s, n) => ({
  x: (s.ax + s.bx) / 2,
  z: (s.az + s.bz) / 2,
  major: n % 3 === 0,
  phase: (n * 137.5 * Math.PI) / 180,
  appearAt:
    INCIDENT_WINDOW[0] +
    (((n * 53) % 89) / 89) * (INCIDENT_WINDOW[1] - INCIDENT_WINDOW[0]),
}));

function IncidentBeacons() {
  const ringRef = useRef<THREE.InstancedMesh>(null);
  const coreRef = useRef<THREE.InstancedMesh>(null);

  const workMatrix = useRef(new THREE.Matrix4());
  const workQuat = useRef(
    new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), -Math.PI / 2),
  );
  const workCoreQuat = useRef(new THREE.Quaternion());
  const workPos = useRef(new THREE.Vector3());
  const workScale = useRef(new THREE.Vector3());

  useLayoutEffect(() => {
    for (const ref of [ringRef, coreRef]) {
      const mesh = ref.current;
      if (!mesh) continue;
      workPos.current.set(0, -10, 0);
      workScale.current.setScalar(0.0001);
      for (let i = 0; i < BEACONS.length; i++) {
        workQuat.current.identity();
        workMatrix.current.compose(workPos.current, workQuat.current, workScale.current);
        mesh.setMatrixAt(i, workMatrix.current);
      }
      mesh.instanceMatrix.needsUpdate = true;
    }
  }, []);

  useFrame(({ clock }) => {
    const p = getLandingProgress();
    const t = clock.elapsedTime;

    for (let i = 0; i < BEACONS.length; i++) {
      const b = BEACONS[i];
      const on = p >= b.appearAt ? Math.min(1, (p - b.appearAt) * 20) : 0;
      if (!on && ringRef.current && coreRef.current) {
        workScale.current.setScalar(0.0001);
        workPos.current.set(0, -10, 0);
        workMatrix.current.compose(workPos.current, workQuat.current, workScale.current);
        ringRef.current.setMatrixAt(i, workMatrix.current);
        workMatrix.current.compose(workPos.current, workCoreQuat.current, workScale.current);
        coreRef.current.setMatrixAt(i, workMatrix.current);
        continue;
      }

      // Sonar cycle: ring expands and fades, restarts. Majors run wider.
      const maxR = b.major ? 2.6 : 1.5;
      const cycle = ((t * (b.major ? 0.55 : 0.75) + b.phase) % (Math.PI * 2)) / (Math.PI * 2);
      const r = maxR * (0.25 + 0.75 * easeOutCubic(cycle));

      workPos.current.set(b.x, 0.14, b.z);
      workScale.current.setScalar(r * on);
      workMatrix.current.compose(workPos.current, workQuat.current, workScale.current);
      if (ringRef.current) ringRef.current.setMatrixAt(i, workMatrix.current);

      // Core marker: steady presence under the ring.
      const cs = (b.major ? 0.42 : 0.3) * on * (1 + 0.12 * Math.sin(t * 2.2 + b.phase));
      workScale.current.setScalar(cs);
      workMatrix.current.compose(workPos.current, workCoreQuat.current, workScale.current);
      if (coreRef.current) coreRef.current.setMatrixAt(i, workMatrix.current);
    }

    if (ringRef.current) ringRef.current.instanceMatrix.needsUpdate = true;
    if (coreRef.current) coreRef.current.instanceMatrix.needsUpdate = true;
  });

  return (
    <>
      <instancedMesh ref={ringRef} args={[undefined, undefined, BEACONS.length]} frustumCulled={false}>
        <ringGeometry args={[0.86, 1, 40]} />
        <meshBasicMaterial color="#FF3655" transparent opacity={0.65} side={THREE.DoubleSide} depthWrite={false} />
      </instancedMesh>
      <instancedMesh ref={coreRef} args={[undefined, undefined, BEACONS.length]} frustumCulled={false}>
        <sphereGeometry args={[0.34, 16, 12]} />
        <meshBasicMaterial color="#FF3655" toneMapped={false} />
      </instancedMesh>
    </>
  );
}

/* --- Intelligence orbs ------------------------------------------------------
   The ambient "living city" layer: a handful of small teal lights drifting
   slowly above the arteries — the presence of live intelligence, felt long
   before any specific system appears. Restrained: few, dim, slow. */

const ORB_COUNT = 12;

const ORB_SPOTS = (() => {
  const spots: { x: number; z: number; phase: number; appearAt: number }[] = [];
  let cursor = 331 % Math.max(1, CITY_SEG_COUNT);
  let guard = 0;
  while (spots.length < ORB_COUNT && guard < 60_000) {
    guard += 1;
    cursor = (cursor + 977) % CITY_SEG_COUNT;
    const seg = CITY_SEG[cursor];
    if (!seg || ![seg[0], seg[1], seg[2], seg[3]].every(Number.isFinite)) continue;
    const [x, z] = safeProject((seg[0] + seg[2]) / 2, (seg[1] + seg[3]) / 2);
    if (!Number.isFinite(x) || !Number.isFinite(z)) continue;
    const n = spots.length;
    spots.push({
      x,
      z,
      phase: (n * 137.5 * Math.PI) / 180,
      appearAt: ORB_WINDOW[0] + (((n * 53) % 89) / 89) * (ORB_WINDOW[1] - ORB_WINDOW[0]),
    });
  }
  return spots;
})();

function IntelligenceOrbs() {
  const coreRef = useRef<THREE.InstancedMesh>(null);
  const glowRef = useRef<THREE.InstancedMesh>(null);

  const workMatrix = useRef(new THREE.Matrix4());
  const workPos = useRef(new THREE.Vector3());
  const workQuat = useRef(new THREE.Quaternion());
  const workScale = useRef(new THREE.Vector3());

  useLayoutEffect(() => {
    for (const ref of [coreRef, glowRef]) {
      const mesh = ref.current;
      if (!mesh) continue;
      workPos.current.set(0, -10, 0);
      workScale.current.setScalar(0.0001);
      for (let i = 0; i < ORB_SPOTS.length; i++) {
        workMatrix.current.compose(workPos.current, workQuat.current, workScale.current);
        mesh.setMatrixAt(i, workMatrix.current);
      }
      mesh.instanceMatrix.needsUpdate = true;
    }
  }, []);

  useFrame(({ clock }) => {
    const p = getLandingProgress();
    const t = clock.elapsedTime;

    for (let i = 0; i < ORB_SPOTS.length; i++) {
      const u = ORB_SPOTS[i];
      const on = ramp(p, u.appearAt, u.appearAt + 0.06);

      // Slow drift + breathing hover — presence without noise.
      const x = u.x + Math.sin(t * 0.11 + u.phase) * 2.2;
      const z = u.z + Math.cos(t * 0.09 + u.phase * 1.7) * 2.2;
      const y = 3.2 + Math.sin(t * 0.45 + u.phase) * 1.1;
      const s = on * (0.75 + 0.25 * Math.sin(t * 0.6 + u.phase));

      workPos.current.set(x, y, z);
      workScale.current.setScalar(Math.max(0.0001, s));
      workMatrix.current.compose(workPos.current, workQuat.current, workScale.current);
      if (coreRef.current) coreRef.current.setMatrixAt(i, workMatrix.current);

      // Halo shell breathes slightly larger than the core.
      workScale.current.setScalar(Math.max(0.0001, s * 2.4));
      workMatrix.current.compose(workPos.current, workQuat.current, workScale.current);
      if (glowRef.current) glowRef.current.setMatrixAt(i, workMatrix.current);
    }
    if (coreRef.current) coreRef.current.instanceMatrix.needsUpdate = true;
    if (glowRef.current) glowRef.current.instanceMatrix.needsUpdate = true;
  });

  return (
    <>
      <instancedMesh ref={coreRef} args={[undefined, undefined, ORB_COUNT]} frustumCulled={false}>
        <sphereGeometry args={[0.22, 14, 10]} />
        <meshBasicMaterial color="#16F2D4" transparent opacity={0.9} toneMapped={false} depthWrite={false} />
      </instancedMesh>
      <instancedMesh ref={glowRef} args={[undefined, undefined, ORB_COUNT]} frustumCulled={false}>
        <sphereGeometry args={[0.22, 14, 10]} />
        <meshBasicMaterial
          color="#16F2D4"
          transparent
          opacity={0.07}
          blending={THREE.AdditiveBlending}
          depthWrite={false}
        />
      </instancedMesh>
    </>
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
