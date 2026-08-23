/**
 * Derived render buffers from the static city dataset (Phase 10B).
 * Built once at module load — zero per-frame allocation.
 */
import { CITY, project, type HospitalLocation, type StationLocation } from './projection';

export const ROAD_TIERS = [0, 1, 2] as const;
export type RoadTier = (typeof ROAD_TIERS)[number];

/** Per-tier merged line-segment vertex buffers: [x1, z1, x2, z2, ...]. */
const tierBuffers = new Map<RoadTier, Float32Array>();

function buildTier(tier: RoadTier): Float32Array {
  const pts: number[] = [];
  for (const [lng1, lat1, lng2, lat2, t] of CITY.segments) {
    if (t !== tier) continue;
    const [x1, z1] = project(lng1, lat1);
    const [x2, z2] = project(lng2, lat2);
    pts.push(x1, z1, x2, z2);
  }
  return new Float32Array(pts);
}

export function getRoadBuffer(tier: RoadTier): Float32Array {
  let buf = tierBuffers.get(tier);
  if (!buf) {
    buf = buildTier(tier);
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
  const [x, z] = project(h.lng, h.lat);
  return { ...h, x, z };
});

export const STATIONS: PlacedStation[] = CITY.stations.map((s) => {
  const [x, z] = project(s.lng, s.lat);
  return { ...s, x, z };
});
