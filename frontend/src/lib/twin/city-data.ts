/**
 * Derived render buffers from the static city dataset (Phase 10B).
 * Built once at module load — zero per-frame allocation.
 */
import * as THREE from 'three';
import { CITY, project, safeProject, type HospitalLocation, type StationLocation } from './projection';

export const ROAD_TIERS = [0, 1, 2] as const;
export type RoadTier = (typeof ROAD_TIERS)[number];

/** Per-tier merged line-segment vertex buffers: [x1, z1, x2, z2, ...]. */
const tierBuffers = new Map<RoadTier, Float32Array | null>();

function buildTier(tier: RoadTier): Float32Array {
  const pts: number[] = [];
  for (const [lng1, lat1, lng2, lat2, t] of CITY.segments) {
    if (t !== tier) continue;
    // NaN defense: a single non-finite vertex poisons the whole merged
    // buffer and surfaces as "Computed radius is NaN" in Three.js.
    if (![lng1, lat1, lng2, lat2].every(Number.isFinite)) continue;
    const [x1, z1] = project(lng1, lat1);
    const [x2, z2] = project(lng2, lat2);
    pts.push(x1, z1, x2, z2);
  }
  return new Float32Array(pts);
}

/**
 * Road buffer for a tier, or null when the tier has no finite vertices.
 * Callers must not mount line segments against an empty position
 * attribute — an empty bounding box computes a NaN center.
 */
export function getRoadBuffer(tier: RoadTier): Float32Array | null {
  let buf = tierBuffers.get(tier) ?? null;
  if (buf === null) {
    const built = buildTier(tier);
    buf = built.length > 0 ? built : null;
    tierBuffers.set(tier, buf);
  }
  return buf;
}

/**
 * Road geometry for a tier, safe on every three.js version.
 *
 * Positions are expanded to itemSize-3 directly on the XZ plane (y=0).
 * Regression note: expanding the raw itemSize-2 buffer through
 * `applyMatrix4(makeRotationX(…))` poisons the attribute with NaN under
 * three r160+ ("Computed radius is NaN"), which silently rendered every
 * road invisible on both landing and command pages. No matrix — ever.
 *
 * Returns a FRESH geometry per call (landing mutates drawRange on its
 * instances; sharing would leak that state across routes).
 */
export function createRoadGeometry(tier: RoadTier): THREE.BufferGeometry | null {
  const buf = getRoadBuffer(tier);
  if (!buf) return null;
  const verts = buf.length / 2;
  const arr = new Float32Array(verts * 3);
  for (let v = 0; v < verts; v++) {
    arr[v * 3] = buf[v * 2]; // x
    arr[v * 3 + 1] = 0; // y — ground plane
    arr[v * 3 + 2] = buf[v * 2 + 1]; // z
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(arr, 3));
  return geo;
}

export interface PlacedHospital extends HospitalLocation {
  x: number;
  z: number;
}

export interface PlacedStation extends StationLocation {
  x: number;
  z: number;
}

export const HOSPITALS: PlacedHospital[] = CITY.hospitals.map((h) => {
  const [x, z] = safeProject(h.lng, h.lat);
  return { ...h, x, z };
});

export const STATIONS: PlacedStation[] = CITY.stations.map((s) => {
  const [x, z] = safeProject(s.lng, s.lat);
  return { ...s, x, z };
});
