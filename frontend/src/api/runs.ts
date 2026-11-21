import { request } from './client';
import { SimulationRun, SimulationRunCreate } from '../types/run';
import { SimulationWorker } from '../types/worker';

export async function listRuns(): Promise<SimulationRun[]> {
  return request<SimulationRun[]>('/api/v1/runs');
}

export async function getRun(runId: string): Promise<SimulationRun> {
  return request<SimulationRun>(`/api/v1/runs/${runId}`);
}

export async function createRun(payload: SimulationRunCreate): Promise<SimulationRun> {
  return request<SimulationRun>('/api/v1/runs', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function startRun(runId: string): Promise<SimulationRun> {
  return request<SimulationRun>(`/api/v1/runs/${runId}/start`, {
    method: 'POST',
  });
}

export async function stopRun(runId: string): Promise<SimulationRun> {
  return request<SimulationRun>(`/api/v1/runs/${runId}/stop`, {
    method: 'POST',
  });
}

export async function getRunWorkers(runId: string): Promise<SimulationWorker[]> {
  return request<SimulationWorker[]>(`/api/v1/runs/${runId}/workers`);
}
