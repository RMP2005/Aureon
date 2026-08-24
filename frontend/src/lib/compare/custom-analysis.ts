import { CITY } from '@/lib/twin/projection';

/**
 * Deterministic custom-scenario analysis (Phase 11K).
 *
 * Builds a stable, geographically grounded teaching prediction:
 *   real localities with coordinates, real hospital sites with capability
 *   profiles, ambulance bases drawn from the actual response-station
 *   dataset, and haversine-based travel math shaped by conditions.
 *
 * Same inputs → same recommendation, every time. Clearly stamped as an
 * illustrative demonstration in the UI — decision-language realism, not
 * live engine output.
 */

/* ------------------------------------------------------------------ */
/* City knowledge tables                                               */
/* ------------------------------------------------------------------ */

export const INCIDENT_TYPES = [
  'Cardiac Emergency',
  'Traffic Collision',
  'Fire Emergency',
  'Respiratory Distress',
  'Multiple Casualty',
] as const;

export const SEVERITIES = ['Low', 'Medium', 'High', 'Critical'] as const;
export const TRAFFIC_OPTIONS = ['Light', 'Moderate', 'Heavy', 'Gridlock'] as const;
export const WEATHER_OPTIONS = ['Clear', 'Rain', 'Heavy Rain', 'Fog'] as const;
export const TIME_OPTIONS = ['Morning', 'Afternoon', 'Evening', 'Night'] as const;

export type IncidentType = (typeof INCIDENT_TYPES)[number];
export type Severity = (typeof SEVERITIES)[number];

export interface Locality {
  name: string;
  lat: number;
  lng: number;
}

/** Real Bengaluru localities — the demo's response-zone anchors. */
export const LOCALITIES: Locality[] = [
  { name: 'Koramangala', lat: 12.9352, lng: 77.6245 },
  { name: 'Indiranagar', lat: 12.9784, lng: 77.6408 },
  { name: 'Whitefield', lat: 12.9698, lng: 77.75 },
  { name: 'Electronic City', lat: 12.8452, lng: 77.6602 },
  { name: 'MG Road', lat: 12.9757, lng: 77.6068 },
  { name: 'HSR Layout', lat: 12.9116, lng: 77.6474 },
  { name: 'Jayanagar', lat: 12.925, lng: 77.5938 },
  { name: 'Marathahalli', lat: 12.9569, lng: 77.7011 },
  { name: 'Hebbal', lat: 13.0358, lng: 77.597 },
  { name: 'Yeshwanthpur', lat: 13.0284, lng: 77.5409 },
  { name: 'Bellandur', lat: 12.926, lng: 77.6762 },
  { name: 'BTM Layout', lat: 12.9166, lng: 77.6101 },
  { name: 'Rajajinagar', lat: 12.991, lng: 77.5526 },
  { name: 'JP Nagar', lat: 12.9063, lng: 77.5857 },
];

type Capability = 'cardiac' | 'trauma' | 'burn' | 'pulmonary' | 'general';

interface HospitalProfile {
  name: string;
  lat: number;
  lng: number;
  capabilities: Capability[];
  /** Relative intake capacity 1–5 — drives load-balancing choices. */
  capacity: number;
}

const CAPABILITY_CYCLE: Capability[][] = [
  ['cardiac', 'general'],
  ['trauma', 'general'],
  ['burn', 'general'],
  ['pulmonary', 'cardiac'],
  ['trauma', 'burn'],
];

/** Real hospital sites from the twin dataset, enriched with demo capability
    profiles (name keywords respected where present). */
const HOSPITALS: HospitalProfile[] = (() => {
  const base = CITY.hospitals.map((h, i) => {
    const caps = new Set<Capability>(['general']);
    const n = h.name.toLowerCase();
    if (n.includes('cardiac')) caps.add('cardiac');
    if (n.includes('trauma')) caps.add('trauma');
    if (n.includes('burn') || n.includes('fire')) caps.add('burn');
    if (n.includes('pulmon') || n.includes('respir') || n.includes('chest')) caps.add('pulmonary');
    // Guarantee specialty coverage across the network.
    for (const c of CAPABILITY_CYCLE[i % CAPABILITY_CYCLE.length]) caps.add(c);
    return { name: h.name, lat: h.lat, lng: h.lng, capabilities: [...caps], capacity: 0 };
  });
  // Deterministic capacity spread 2–5.
  base.forEach((h, i) => {
    h.capacity = ((i * 7 + 3) % 4) + 2;
  });
  return base;
})();

/** Ambulance bases — the real response-station dataset. */
interface Base {
  id: string;
  name: string;
  lat: number;
  lng: number;
}
const BASES: Base[] = CITY.stations.map((s) => ({
  id: s.id,
  name: s.name,
  lat: s.lat,
  lng: s.lng,
}));

/* ------------------------------------------------------------------ */
/* Condition models                                                    */
/* ------------------------------------------------------------------ */

const TRAFFIC_SPEED: Record<string, number> = { Light: 1.15, Moderate: 1.0, Heavy: 0.72, Gridlock: 0.52 };
const WEATHER_SPEED: Record<string, number> = { Clear: 1.0, Rain: 0.93, 'Heavy Rain': 0.85, Fog: 0.9 };
const TIME_SPEED: Record<string, number> = { Morning: 0.9, Afternoon: 1.0, Evening: 0.85, Night: 1.08 };
const PRIORITY_BOOST: Record<Severity, number> = { Critical: 1.18, High: 1.1, Medium: 1.0, Low: 0.95 };

function hashStr(s: string): number {
  let h = 5381;
  for (let i = 0; i < s.length; i++) {
    h = ((h << 5) + h + s.charCodeAt(i)) >>> 0;
  }
  return h >>> 0;
}

/** Great-circle distance in km. */
function haversineKm(aLat: number, aLng: number, bLat: number, bLng: number): number {
  const R = 6371;
  const dLat = ((bLat - aLat) * Math.PI) / 180;
  const dLng = ((bLng - aLng) * Math.PI) / 180;
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((aLat * Math.PI) / 180) * Math.cos((bLat * Math.PI) / 180) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(s));
}

/** Response-zone naming from geography relative to the city centroid. */
function zoneOf(lat: number, lng: number): string {
  const cLat = LOCALITIES.reduce((a, l) => a + l.lat, 0) / LOCALITIES.length;
  const cLng = LOCALITIES.reduce((a, l) => a + l.lng, 0) / LOCALITIES.length;
  const ns = lat >= cLat ? 'North' : 'South';
  const ew = lng >= cLng ? 'East' : 'West';
  const dLat = Math.abs(lat - cLat);
  const dLng = Math.abs(lng - cLng);
  if (dLat < 0.03 && dLng < 0.03) return 'Central Zone';
  return `${dLng > dLat ? ew : ns} Zone`;
}

function locationCode(location: string): string {
  const letters = location.replace(/[^a-zA-Z]/g, '').toUpperCase();
  return letters.length >= 3 ? letters.slice(0, 3) : letters.length > 0 ? letters.padEnd(3, 'X') : 'BLR';
}

/** Resolve free-text input to a known locality, else city-center default. */
function resolveLocality(input: string): { loc: Locality; known: boolean } {
  const q = input.trim().toLowerCase();
  if (!q) return { loc: LOCALITIES[0], known: true };
  const hit =
    LOCALITIES.find((l) => l.name.toLowerCase() === q) ??
    LOCALITIES.find((l) => l.name.toLowerCase().includes(q));
  if (hit) return { loc: hit, known: true };
  return { loc: { name: input.trim(), lat: 12.9352 + (((hashStr(q) >>> 3) % 80) - 40) / 4000, lng: 77.6245 + (((hashStr(q) >>> 7) % 120) - 60) / 4000 }, known: false };
}

/* ------------------------------------------------------------------ */
/* Analysis                                                            */
/* ------------------------------------------------------------------ */

export interface CustomInputs {
  type: IncidentType;
  location: string;
  severity: Severity;
  traffic: string;
  weather: string;
  timeOfDay: string;
}

export interface CustomAnalysis {
  unitId: string;
  unitClass: string;
  etaMinutes: number;
  distanceKm: number;
  hospitalName: string;
  hospitalReason: string;
  hospitalDistanceKm: number;
  zoneName: string;
  unitsAvailable: number;
  explanation: string;
  factors: string[];
}

const NEEDS: Record<IncidentType, { capability: Capability; alsRequired: boolean; label: string }> = {
  'Cardiac Emergency': { capability: 'cardiac', alsRequired: true, label: 'advanced life support with a cardiac monitor' },
  'Traffic Collision': { capability: 'trauma', alsRequired: true, label: 'trauma care and extrication equipment' },
  'Fire Emergency': { capability: 'burn', alsRequired: true, label: 'burn care and airway management' },
  'Respiratory Distress': { capability: 'pulmonary', alsRequired: true, label: 'oxygen therapy and ventilator support' },
  'Multiple Casualty': { capability: 'trauma', alsRequired: true, label: 'mass-casualty triage coordination' },
};

export function analyzeCustomScenario(inputs: CustomInputs): CustomAnalysis {
  const seed = hashStr(
    `${inputs.type}|${inputs.location.trim().toLowerCase()}|${inputs.severity}|${inputs.traffic}|${inputs.weather}|${inputs.timeOfDay}`,
  );
  const { loc } = resolveLocality(inputs.location);
  const need = NEEDS[inputs.type];
  const mci = inputs.type === 'Multiple Casualty';

  /* Unit selection — nearest base with a capable, available crew. */
  const rankedBases = BASES.map((b) => ({ b, km: haversineKm(loc.lat, loc.lng, b.lat, b.lng) })).sort(
    (a, z) => a.km - z.km,
  );
  let chosenBase = rankedBases[0];
  let reroutedNote = '';
  for (let hop = 0; hop < Math.min(3, rankedBases.length); hop++) {
    const cand = rankedBases[hop];
    const availSeed = hashStr(`${cand.b.id}|${inputs.timeOfDay}|${inputs.severity}`);
    const available = ((availSeed >>> 4) % 10) >= (hop === 0 ? 1 : 3); // nearest usually free
    if (available || hop === Math.min(2, rankedBases.length - 1)) {
      chosenBase = cand;
      if (hop > 0) {
        reroutedNote = `The closest base was already committed, so ${locationCode(loc.name)} was covered from ${cand.b.name}.`;
      }
      break;
    }
  }

  const roadFactor = 1.32; // street routing exceeds straight-line distance
  const distanceKm = Math.round(chosenBase.km * roadFactor * 10) / 10;

  const speed =
    34 * // km/h urban cruise
    (TRAFFIC_SPEED[inputs.traffic] ?? 1) *
    (WEATHER_SPEED[inputs.weather] ?? 1) *
    (TIME_SPEED[inputs.timeOfDay] ?? 1) *
    PRIORITY_BOOST[inputs.severity];
  const dispatchOverheadMin = inputs.traffic === 'Gridlock' ? 1.2 : 0.7;
  const driveMin = (distanceKm / speed) * 60;
  const etaMinutes = Math.max(2.4, Math.round((dispatchOverheadMin + driveMin) * 10) / 10);

  const unitPrefix = mci ? 'MCI' : need.alsRequired || inputs.severity === 'Critical' ? 'ALS' : 'BLS';
  const unitNumber = String(((seed >>> 2) % 17) + 1).padStart(2, '0');
  const unitId = `${unitPrefix}-${locationCode(loc.name)}-${unitNumber}`;
  const unitClass = mci
    ? 'Multi-unit response convoy'
    : unitPrefix === 'ALS'
      ? 'Advanced Life Support ambulance'
      : 'Basic Life Support ambulance';

  // Crews on duty around the incident zone right now (demo telemetry).
  const unitsAvailable = 3 + ((seed >>> 6) % 7);

  /* Hospital selection — nearest capable site, load-balanced for MCI. */
  const capable = HOSPITALS.filter((h) => h.capabilities.includes(need.capability));
  const pool = capable.length > 0 ? capable : HOSPITALS;
  const scored = pool
    .map((h) => ({ h, km: haversineKm(loc.lat, loc.lng, h.lat, h.lng) }))
    .sort((a, z) => a.km - z.km);
  let pick = scored[0];
  if (mci) {
    // Load balancing: among the four nearest, prefer intake capacity.
    const near = scored.slice(0, Math.min(4, scored.length));
    near.sort((a, z) => z.h.capacity - a.h.capacity || a.km - z.km);
    pick = near[0];
  }
  const hospitalName = pick.h.name;
  const hospitalDistanceKm = Math.round(pick.km * roadFactor * 10) / 10;

  const reasonByType: Record<IncidentType, string> = {
    'Cardiac Emergency': 'its cardiac care unit is ready to receive',
    'Traffic Collision': 'its trauma team is on standby',
    'Fire Emergency': 'its burn unit has open capacity',
    'Respiratory Distress': 'its respiratory care team is available',
    'Multiple Casualty': `it holds the highest intake headroom (${pick.h.capacity}/5) of nearby sites`,
  };

  const weatherFragment =
    inputs.weather !== 'Clear' ? `, ${inputs.weather.toLowerCase()} weather` : '';

  const explanation =
    `Aureon selected ${unitId} because it balanced distance (${distanceKm.toFixed(1)} km from base ${chosenBase.b.name}), ` +
    `${need.label}, ${inputs.traffic.toLowerCase()} traffic${weatherFragment}, and hospital availability at ${hospitalName}.`;

  /* Adaptive decision factors — what matters changes with the emergency. */
  const goldenHour =
    inputs.severity === 'Critical'
      ? `${etaMinutes.toFixed(1)} min keeps treatment inside the golden hour`
      : `${etaMinutes.toFixed(1)} min response against a ${BASE_TARGET[inputs.severity]}-minute target`;
  const factors: string[] = [];
  switch (inputs.type) {
    case 'Traffic Collision':
      factors.push(`Shortest viable approach: ${distanceKm.toFixed(1)} km from base ${chosenBase.b.name}.`);
      factors.push(`${inputs.traffic} congestion set cruising speed to ~${Math.round(speed)} km/h along the corridor.`);
      factors.push(reroutedNote || 'Road access checked: the approach avoids chokepoints flagged at this hour.');
      break;
    case 'Cardiac Emergency':
      factors.push(`ALS capability required and confirmed — monitor and defibrillator on board.`);
      factors.push(`Golden hour: ${goldenHour}.`);
      factors.push(`${hospitalName} is the nearest cardiac-facility site at ${hospitalDistanceKm.toFixed(1)} km.`);
      break;
    case 'Fire Emergency':
      factors.push('Burn-care supplies and airway management verified on the assigned crew.');
      factors.push(`${hospitalName} holds dedicated burn capacity ${hospitalDistanceKm.toFixed(1)} km out.`);
      factors.push(`${inputs.traffic} conditions${weatherFragment} shaped the fastest approach corridor.`);
      break;
    case 'Respiratory Distress':
      factors.push('Ventilator support and oxygen stock confirmed on board.');
      factors.push(`${hospitalName} staffed for pulmonary intake at ${hospitalDistanceKm.toFixed(1)} km.`);
      factors.push(`${inputs.timeOfDay} response posture: ~${Math.round(speed)} km/h effective corridor speed.`);
      break;
    case 'Multiple Casualty':
      factors.push(`${Math.min(4, 2 + ((seed >>> 8) % 3))} additional units staged toward ${loc.name} in parallel.`);
      factors.push(`Load balanced: ${hospitalName} takes primary intake (${pick.h.capacity}/5 headroom), secondary sites pre-alerted.`);
      factors.push(`Triage staging point set within ${zoneOf(loc.lat, loc.lng)} at ${etaMinutes.toFixed(1)} min from first arrival.`);
      break;
  }
  factors.push(`${zoneOf(loc.lat, loc.lng)} keeps at least one crew covering neighbouring zones.`);

  return {
    unitId,
    unitClass,
    etaMinutes,
    distanceKm,
    hospitalName,
    hospitalReason: reasonByType[inputs.type],
    hospitalDistanceKm,
    zoneName: zoneOf(loc.lat, loc.lng),
    unitsAvailable,
    explanation,
    factors,
  };
}

const BASE_TARGET: Record<Severity, number> = { Critical: 8, High: 11, Medium: 14, Low: 18 };

/** Zone name for a known locality, else null (form hints). */
export function localityZone(name: string): string | null {
  const hit = LOCALITIES.find((l) => l.name.toLowerCase() === name.trim().toLowerCase());
  return hit ? zoneOf(hit.lat, hit.lng) : null;
}
