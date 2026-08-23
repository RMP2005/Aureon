import { API_BASE_URL } from './constants';

export interface ApiResponse<T> {
  status: string;
  data: T;
  error: string | null;
  timestamp: string;
}

export interface HealthData {
  status: string;
  service: string;
  version: string;
}

export interface SimulationState {
  ambulances: Array<{
    id: string;
    status: string;
    current_node?: string;
    hospital_id?: string;
  }>;
  hospitals: Array<{
    id: string;
    name: string;
    available_beds: number;
    total_beds: number;
  }>;
  active_incidents: unknown[];
  tick: number;
}

export interface SimulationRunResult {
  run_id: string;
  strategy: string;
  parameters: {
    duration_minutes: number;
    incident_rate_per_hour: number;
    seed: number;
  };
  metrics: SimulationMetrics;
  dispatch_log_sample?: DispatchLogEntry[];
  executed_at: string;
}

/** Nested metrics contract — mirrors SimulationMetrics.to_dict() (city_engine.py) */
export interface SimulationMetrics {
  total_incidents_reported: number;
  total_incidents_dispatched: number;
  total_incidents_completed: number;
  unserviced_incidents_count: number;
  response_times_minutes: ResponseTimeStats;
  critical_cases: CriticalCaseStats;
  clinical_quality: ClinicalQualityStats;
  operations: OperationsStats;
}

export interface ResponseTimeStats {
  mean: number;
  median: number;
  p90: number;
  p95: number;
  min: number;
  max: number;
}

export interface CriticalCaseStats {
  count: number;
  mean_response_time_min: number;
  target_compliance_percent: number;
}

export interface ClinicalQualityStats {
  capability_match_percent: number;
  mean_hospital_suitability_score: number;
}

export interface OperationsStats {
  total_fleet_distance_km: number;
  fleet_utilization_percent: number;
  avg_missions_per_ambulance: number;
}

export interface DispatchLogEntry {
  tick: number;
  sim_time_sec: number;
  incident_id: string;
  category: string;
  severity: string;
  ambulance_id: string;
  callsign: string;
  capability: string;
  matched: boolean;
  scene_eta_sec: number;
  hospital_id: string | null;
  rationale: string;
}

/** Live twin snapshot of a running simulation — GET /simulation/{run_id}/state */
export interface RunLiveState {
  run_id: string;
  tick: number;
  sim_time_sec: number;
  sim_time_formatted: string;
  strategy: string;
  ambulances: TwinAmbulance[];
  hospitals: TwinHospitalState[];
  active_incidents: TwinIncident[];
  completed_incidents_count: number;
  pending_queue_count: number;
  run_status?: RunProgress;
}

export interface TwinAmbulance {
  id: string;
  callsign: string;
  capability: string;
  status: string;
  latitude: number;
  longitude: number;
  current_node_id: string;
  active_incident_id: string | null;
  missions_completed: number;
  total_distance_km: number;
}

export interface TwinHospitalState {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  specialties: string[];
  er_occupancy: string;
  icu_occupancy: string;
}

export interface TwinIncident {
  id: string;
  category: string;
  severity: string;
  location_name: string;
  latitude: number;
  longitude: number;
  required_capability: string;
  assigned_ambulance: string | null;
}

export interface RunProgress {
  run_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  progress_percent: number;
  elapsed_seconds: number;
  duration_seconds: number;
  completed_incidents: number;
  reported_incidents: number;
  active_ambulances: number;
  available_ambulances: number;
  error: string | null;
}

export interface ComparisonResult {
  comparison_id: string;
  baseline: Record<string, unknown>;
  aureon_intelligence: Record<string, unknown>;
  improvements: Record<string, number>;
  executed_at: string;
}

export interface RunSummary {
  run_id: string;
  type: string;
  strategy: string;
  status: string;
  executed_at: string;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<ApiResponse<T>> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function getHealth(): Promise<ApiResponse<HealthData>> {
  return apiFetch<HealthData>('/health');
}

export async function getSimulationState(): Promise<ApiResponse<SimulationState>> {
  return apiFetch<SimulationState>('/simulation/state');
}

export async function runSimulation(params: {
  strategy?: string;
  duration_minutes?: number;
  incident_rate_per_hour?: number;
  seed?: number;
}): Promise<ApiResponse<SimulationRunResult>> {
  return apiFetch<SimulationRunResult>('/simulation/run', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function compareStrategies(params: {
  duration_minutes?: number;
  incident_rate_per_hour?: number;
  seed?: number;
}): Promise<ApiResponse<ComparisonResult>> {
  return apiFetch<ComparisonResult>('/simulation/compare', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function listSimulationResults(): Promise<ApiResponse<RunSummary[]>> {
  return apiFetch<RunSummary[]>('/simulation/results');
}

export async function getRunById(runId: string): Promise<ApiResponse<SimulationRunResult>> {
  return apiFetch<SimulationRunResult>(`/simulation/results/${runId}`);
}

export async function getRunStatus(runId: string): Promise<ApiResponse<RunProgress>> {
  return apiFetch<RunProgress>(`/simulation/${runId}/status`);
}

/** Run-scoped live twin snapshot (Phase 10A-BE B1). 404 when no live engine. */
export async function getRunLiveState(runId: string): Promise<ApiResponse<RunLiveState>> {
  return apiFetch<RunLiveState>(
    `/simulation/${encodeURIComponent(runId)}/state`,
  );
}
