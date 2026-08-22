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
  metrics: Record<string, number>;
  executed_at: string;
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
