import { useQuery } from '@tanstack/react-query';
import { getWorkerNode, listWorkerNodes } from '../api/workers';
import { WorkerNode } from '../types/worker';

export function useWorkers(status?: string, pollIntervalMs = 5000) {
  return useQuery<WorkerNode[], Error>({
    queryKey: ['workers', status],
    queryFn: () => listWorkerNodes(status),
    refetchInterval: pollIntervalMs,
    staleTime: 4000,
  });
}

export function useWorkerDetails(workerId: string | undefined) {
  return useQuery<WorkerNode, Error>({
    queryKey: ['worker', workerId],
    queryFn: () => getWorkerNode(workerId!),
    enabled: Boolean(workerId),
    staleTime: 5000,
  });
}
