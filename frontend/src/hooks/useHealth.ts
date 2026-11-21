import { useQuery } from '@tanstack/react-query';
import { getHealth } from '../api/health';
import { HealthResponse } from '../types/health';

export function useHealth(pollIntervalMs = 5000) {
  return useQuery<HealthResponse, Error>({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: pollIntervalMs,
    staleTime: 4000,
    retry: 2,
  });
}
