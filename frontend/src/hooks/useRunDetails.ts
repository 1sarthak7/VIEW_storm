import { useQuery } from '@tanstack/react-query';
import { getRun, getRunWorkers } from '../api/runs';
import { SimulationRun } from '../types/run';
import { SimulationWorker } from '../types/worker';

export function useRunDetails(runId: string | undefined) {
  const runQuery = useQuery<SimulationRun, Error>({
    queryKey: ['run', runId],
    queryFn: () => getRun(runId!),
    enabled: Boolean(runId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      const isActive =
        status === 'running' ||
        status === 'starting' ||
        status === 'waiting_for_workers' ||
        status === 'stopping';
      return isActive ? 2000 : false;
    },
  });

  const workersQuery = useQuery<SimulationWorker[], Error>({
    queryKey: ['run-workers', runId],
    queryFn: () => getRunWorkers(runId!),
    enabled: Boolean(runId),
    refetchInterval: () => {
      const runStatus = runQuery.data?.status;
      const isActive =
        runStatus === 'running' ||
        runStatus === 'starting' ||
        runStatus === 'waiting_for_workers';
      return isActive ? 2500 : false;
    },
  });

  return {
    run: runQuery.data,
    isLoadingRun: runQuery.isLoading,
    isErrorRun: runQuery.isError,
    errorRun: runQuery.error,
    refetchRun: runQuery.refetch,
    workers: workersQuery.data || [],
    isLoadingWorkers: workersQuery.isLoading,
  };
}
