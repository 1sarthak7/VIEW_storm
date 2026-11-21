import { request } from './client';
import { HealthResponse } from '../types/health';

export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/api/v1/health');
}
