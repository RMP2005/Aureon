/**
 * Derived render buffers from the static city dataset (Phase 10B).
 * Built once at module load — zero per-frame allocation.
 */
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
