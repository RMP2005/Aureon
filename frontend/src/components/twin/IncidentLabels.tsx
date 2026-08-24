'use client';

import { useEffect, useState } from 'react';
import { Html } from '@react-three/drei';
import { getLiveBuffer } from '@/lib/twin/live-buffer';
import { CENTER_LAT, CENTER_LNG, CITY, WORLD_SIZE } from '@/lib/twin/projection';
import { LOCALITIES } from '@/lib/compare/custom-analysis';

/**
 * Incident location markers (Phase 11K-optional).
 *
 * Purely additive HUD overlay: a small labeled chip above each active
 * incident, reading the SAME live buffer the beacons already render.
 * Touches nothing else — roads, routes, camera and beacon pipeline stay
 * exactly as approved.
 *
 * Each chip carries the incident's area name, resolved from its world
 * position through the same LOCALITIES table the custom simulator uses.
 *
 * Anti-clutter contract: chips appear only while four or fewer incidents
 * are active; heavier scenes fall back to the beacons alone.
 */

const MAX_LABELED = 4;
const POLL_MS = 500;

/** Smaller viewports show fewer floating labels — keep the map readable. */
function labelCap(): number {
  if (typeof window === 'undefined') return MAX_LABELED;
  return window.matchMedia('(max-width: 767px)').matches ? 2 : MAX_LABELED;
}

interface Chip {
  id: string;
  x: number;
  z: number;
  category: string;
  severity: string;
  area: string;
}

// Mirror of the projection constants (read-only math — no pipeline changes).
const BBOX = CITY.bbox;
const COS_LAT = Math.cos((CENTER_LAT * Math.PI) / 180);
const SPAN_LAT = BBOX.maxLat - BBOX.minLat;
const SPAN_LNG = (BBOX.maxLng - BBOX.minLng) * COS_LAT;
const PROJ_SCALE = WORLD_SIZE / Math.max(SPAN_LAT, SPAN_LNG);

/** Exact inverse of project() — world XZ back to geodetic lat/lng. */
function unproject(x: number, z: number): { lat: number; lng: number } {
  return {
    lng: CENTER_LNG + x / (COS_LAT * PROJ_SCALE),
    lat: CENTER_LAT - z / PROJ_SCALE,
  };
}

function haversineKm(aLat: number, aLng: number, bLat: number, bLng: number): number {
  const R = 6371;
  const dLat = ((bLat - aLat) * Math.PI) / 180;
  const dLng = ((bLng - aLng) * Math.PI) / 180;
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((aLat * Math.PI) / 180) * Math.cos((bLat * Math.PI) / 180) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(s));
}

/** Nearest known locality to a world position — "" when far outside town. */
function nearestArea(x: number, z: number): string {
  if (!Number.isFinite(x) || !Number.isFinite(z)) return '';
  const { lat, lng } = unproject(x, z);
  let best = '';
  let bestKm = Infinity;
  for (const l of LOCALITIES) {
    const km = haversineKm(lat, lng, l.lat, l.lng);
    if (km < bestKm) {
      bestKm = km;
      best = l.name;
    }
  }
  // Outside the demo's locality net — keep the chip minimal instead of
  // naming an implausible area. Half the city span is a generous cutoff.
  return bestKm <= WORLD_SIZE * 0.35 ? best : '';
}

function readChips(): Chip[] {
  try {
    const { incidents } = getLiveBuffer();
    const cap = labelCap();
    if (incidents.length > cap) return [];
    return incidents.slice(0, cap).map((i) => ({
      id: i.id,
      x: i.x,
      z: i.z,
      category: i.category,
      severity: i.severity,
      area: nearestArea(i.x, i.z),
    }));
  } catch {
    return [];
  }
}

export default function IncidentLabels() {
  const [chips, setChips] = useState<Chip[]>([]);

  useEffect(() => {
    setChips(readChips());
    const id = setInterval(() => setChips(readChips()), POLL_MS);
    return () => clearInterval(id);
  }, []);

  if (chips.length === 0) return null;

  return (
    <>
      {chips.map((c) => (
        <Html key={c.id} position={[c.x, 1.7, c.z]} center zIndexRange={[20, 10]} style={{ pointerEvents: 'none' }}>
          <div className="flex select-none flex-col items-center gap-0.5 whitespace-nowrap rounded border border-crit-red/40 bg-void/70 px-1.5 py-1 backdrop-blur-sm">
            <span className="flex items-center gap-1.5">
              <span className="hud-stamp !text-[8px] text-crit-red">{c.category || 'INCIDENT'}</span>
              {c.severity && (
                <span
                  aria-hidden
                  className={`h-1 w-1 rounded-full ${/crit|major|high/i.test(c.severity) ? 'bg-crit-red' : 'bg-amber-warn'}`}
                />
              )}
            </span>
            {c.area && (
              <span className="hud-stamp !text-[7px] leading-none text-[var(--color-text-secondary)]">
                {c.area}
              </span>
            )}
          </div>
        </Html>
      ))}
    </>
  );
}
