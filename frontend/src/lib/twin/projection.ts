/**
 * Bengaluru geodetic → twin world-space projection (Phase 10B).
 *
 * Equirectangular projection scaled so the full arterial network fits a
 * compact world, centered on the origin and laid onto the XZ plane.
 * North = -Z (standard map orientation when viewed from a southern camera).
 */
import cityJson from '@/data/bangalore-city.json';

export interface CityBBox {
  minLat: number;
  maxLat: number;
  minLng: number;
  maxLng: number;
}

export interface RoadSegment {
  lng1: number;
  lat1: number;
  lng2: number;
  lat2: number;
  tier: 0 | 1 | 2;
}

export interface HospitalLocation {
  id: string;
  name: string;
  lat: number;
  lng: number;
}

export interface StationLocation {
  id: string;
  name: string;
  lat: number;
  lng: number;
}

interface CityPayload {
  bbox: CityBBox;
  segments: [number, number, number, number, number][];
  hospitals: { id: string; name: string; lat: number; lng: number }[];
  stations: { id: string; name: string; lat: number; lng: number }[];
}

export const CITY = cityJson as CityPayload;

/** Full city spans this many world units across its larger dimension. */
export const WORLD_SIZE = 120;

const B = CITY.bbox;
export const CENTER_LAT = (B.minLat + B.maxLat) / 2;
export const CENTER_LNG = (B.minLng + B.maxLng) / 2;

// Longitude degrees are compressed by cos(latitude) in equirectangular maps.
const COS_LAT = Math.cos((CENTER_LAT * Math.PI) / 180);

const SPAN_LAT = B.maxLat - B.minLat;
const SPAN_LNG = (B.maxLng - B.minLng) * COS_LAT;
const LARGER_SPAN = Math.max(SPAN_LAT, SPAN_LNG);
const SCALE = WORLD_SIZE / LARGER_SPAN;

/** Project geodetic coordinates to world XZ. Returns [x, z]. */
export function project(lng: number, lat: number): [number, number] {
  const x = (lng - CENTER_LNG) * COS_LAT * SCALE;
  const z = -(lat - CENTER_LAT) * SCALE;
  return [x, z];
}

/**
 * Project with NaN defense (Phase 11-stability).
 *
 * Any non-finite geodetic input — a malformed engine snapshot, a missing
 * coordinate on first poll, corrupt JSON — would otherwise flow straight
 * into Three.js matrices and geometry attributes, where it surfaces as
 * "Computed radius is NaN" or invisible/broken rendering. Invalid
 * coordinates collapse to the city center instead of poisoning the scene.
 * Valid inputs pass through bit-identical.
 */
export function safeProject(lng: number, lat: number): [number, number] {
  if (!Number.isFinite(lng) || !Number.isFinite(lat)) {
    return [0, 0];
  }
  return project(lng, lat);
}

/** True when [x, z] can safely enter a Three.js matrix or attribute. */
export function isFiniteXZ(x: number, z: number): boolean {
  return Number.isFinite(x) && Number.isFinite(z);
}

/** Unproject world XZ back to [lng, lat] (selection readouts, debugging). */
export function unproject(x: number, z: number): [number, number] {
  const lng = x / (COS_LAT * SCALE) + CENTER_LNG;
  const lat = -z / SCALE + CENTER_LAT;
  return [lng, lat];
}
