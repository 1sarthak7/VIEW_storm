import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createRun, listRuns, startRun, stopRun } from '../api/runs';
import { SimulationRun, SimulationRunCreate } from '../types/run';

export function useRuns(pollIntervalMs = 5000) {
  return useQuery<SimulationRun[], Error>({
    queryKey: ['runs'],
    queryFn: listRuns,
    refetchInterval: pollIntervalMs,
    staleTime: 3000,
  });
}

export function useRunMutations() {
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: (payload: SimulationRunCreate) => createRun(payload),
    onSuccess: (newRun) => {
      queryClient.invalidateQueries({ queryKey: ['runs'] });
      queryClient.setQueryData(['run', newRun.id], newRun);
    },
  });

  const startMutation = useMutation({
    mutationFn: (runId: string) => startRun(runId),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ['runs'] });
      queryClient.invalidateQueries({ queryKey: ['run', updated.id] });
      queryClient.invalidateQueries({ queryKey: ['run-stats', updated.id] });
      queryClient.invalidateQueries({ queryKey: ['workers'] });
    },
  });

  const stopMutation = useMutation({
    mutationFn: (runId: string) => stopRun(runId),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: ['runs'] });
      queryClient.invalidateQueries({ queryKey: ['run', updated.id] });
      queryClient.invalidateQueries({ queryKey: ['run-stats', updated.id] });
      queryClient.invalidateQueries({ queryKey: ['workers'] });
    },
  });

  return {
    createRun: createMutation,
    startRun: startMutation,
    stopRun: stopMutation,
  };
}
