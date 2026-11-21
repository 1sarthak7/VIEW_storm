import { useQuery } from '@tanstack/react-query';
import { getRunMetrics, getRunReport, getRunStats } from '../api/stats';
import { SimulationMetrics, SimulationReport, SimulationStats } from '../types/stats';

export function useRunStats(runId: string | undefined, isActiveRun = false) {
  const statsQuery = useQuery<SimulationStats, Error>({
    queryKey: ['run-stats', runId],
    queryFn: () => getRunStats(runId!),
    enabled: Boolean(runId),
    refetchInterval: isActiveRun ? 2000 : false,
    staleTime: isActiveRun ? 1500 : 30000,
  });

  const metricsQuery = useQuery<SimulationMetrics, Error>({
    queryKey: ['run-metrics', runId],
    queryFn: () => getRunMetrics(runId!),
    enabled: Boolean(runId),
    refetchInterval: isActiveRun ? 2000 : false,
    staleTime: isActiveRun ? 1500 : 30000,
  });

  return {
    stats: statsQuery.data,
    isLoadingStats: statsQuery.isLoading,
    isErrorStats: statsQuery.isError,
    metrics: metricsQuery.data?.metrics || [],
    isLoadingMetrics: metricsQuery.isLoading,
    refetch: () => {
      statsQuery.refetch();
      metricsQuery.refetch();
    },
  };
}

export function useRunReport(runId: string | undefined) {
  return useQuery<SimulationReport, Error>({
    queryKey: ['run-report', runId],
    queryFn: () => getRunReport(runId!),
    enabled: Boolean(runId),
    staleTime: 60000,
  });
}
