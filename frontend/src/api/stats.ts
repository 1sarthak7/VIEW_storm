import { request } from './client';
import { SimulationMetrics, SimulationReport, SimulationStats } from '../types/stats';

export async function getRunStats(runId: string): Promise<SimulationStats> {
  return request<SimulationStats>(`/api/v1/runs/${runId}/stats`);
}

export async function getRunMetrics(runId: string): Promise<SimulationMetrics> {
  return request<SimulationMetrics>(`/api/v1/runs/${runId}/metrics`);
}

export async function getRunReport(runId: string): Promise<SimulationReport> {
  return request<SimulationReport>(`/api/v1/runs/${runId}/report`);
}
