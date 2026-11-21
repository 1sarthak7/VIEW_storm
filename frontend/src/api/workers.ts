import { request } from './client';
import { WorkerNode } from '../types/worker';

export async function listWorkerNodes(status?: string): Promise<WorkerNode[]> {
  const query = status ? `?status=${encodeURIComponent(status)}` : '';
  return request<WorkerNode[]>(`/api/v1/worker-nodes${query}`);
}

export async function getWorkerNode(workerId: string): Promise<WorkerNode> {
  return request<WorkerNode>(`/api/v1/worker-nodes/${workerId}`);
}
