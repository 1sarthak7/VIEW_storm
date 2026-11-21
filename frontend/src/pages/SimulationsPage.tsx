import React, { useState, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Layers,
  Plus,
  Play,
  Square,
  Search,
  Filter,
  AlertCircle,
  X,
  Server,
} from 'lucide-react';
import { useRuns, useRunMutations } from '../hooks/useRuns';
import { useWorkers } from '../hooks/useWorkers';
import { StatusBadge } from '../components/common/StatusBadge';
import { ConfirmModal } from '../components/common/ConfirmModal';
import { TableSkeleton } from '../components/common/Skeleton';
import { ErrorBanner } from '../components/common/ErrorBanner';
import { SimulationRunCreate } from '../types/run';

const createSimulationSchema = z
  .object({
    name: z.string().min(1, 'Simulation name is required').max(100, 'Max 100 characters'),
    target_environment: z.string().default('local'),
    execution_mode: z.enum(['local', 'distributed']),
    virtual_users: z.coerce.number().min(1, 'Minimum 1 virtual user'),
    spawn_rate: z.coerce.number().min(0.1, 'Minimum spawn rate is 0.1').max(500, 'Max spawn rate is 500'),
    duration_seconds: z.coerce.number().min(5, 'Minimum duration is 5 seconds').max(86400, 'Max duration is 24 hours'),
    event_type: z.string().default('playback_start'),
    watch_duration_min: z.coerce.number().min(0, 'Must be positive').default(5),
    watch_duration_max: z.coerce.number().min(0, 'Must be positive').default(60),
  })
  .refine((data) => data.watch_duration_max >= data.watch_duration_min, {
    message: 'Max watch duration must be greater than or equal to min duration',
    path: ['watch_duration_max'],
  })
  .refine(
    (data) => {
      if (data.execution_mode === 'local' && data.virtual_users > 1000) {
        return false;
      }
      return true;
    },
    {
      message: 'Local execution is capped at 1,000 virtual users. Choose distributed for higher load.',
      path: ['virtual_users'],
    }
  );

type SimulationFormData = z.infer<typeof createSimulationSchema>;

export const SimulationsPage: React.FC = () => {
  const navigate = useNavigate();
  const { data: runs, isLoading, isError, error, refetch } = useRuns(4000);
  const { data: workers } = useWorkers('online', 5000);
  const { createRun, startRun, stopRun } = useRunMutations();

  // Filters & Search
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [modeFilter, setModeFilter] = useState('all');

  // Modals
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [stopRunTarget, setStopRunTarget] = useState<string | null>(null);

  // Form setup
  const {
    register,
    handleSubmit,
    watch,
    reset,
    formState: { errors, isValid, isSubmitting },
  } = useForm<SimulationFormData>({
    resolver: zodResolver(createSimulationSchema),
    mode: 'onChange',
    defaultValues: {
      name: '',
      target_environment: 'local',
      execution_mode: 'local',
      virtual_users: 100,
      spawn_rate: 10,
      duration_seconds: 30,
      event_type: 'playback_start',
      watch_duration_min: 5,
      watch_duration_max: 60,
    },
  });

  const selectedMode = watch('execution_mode');
  const totalWorkerCapacity = useMemo(() => {
    return workers?.reduce((sum, w) => sum + w.capacity, 0) || 0;
  }, [workers]);

  const handleCreateSubmit = async (data: SimulationFormData) => {
    try {
      const created = await createRun.mutateAsync(data as SimulationRunCreate);
      setIsCreateModalOpen(false);
      reset();
      navigate(`/simulations/${created.id}`);
    } catch (err) {
      console.error('Failed to create simulation:', err);
    }
  };

  const handleStart = async (runId: string) => {
    try {
      await startRun.mutateAsync(runId);
    } catch (err: any) {
      alert(`Failed to start run: ${err.message || 'Unknown error'}`);
    }
  };

  const handleConfirmStop = async () => {
    if (!stopRunTarget) return;
    try {
      await stopRun.mutateAsync(stopRunTarget);
    } finally {
      setStopRunTarget(null);
    }
  };

  // Filtered runs
  const filteredRuns = useMemo(() => {
    if (!runs) return [];
    return runs.filter((r) => {
      const matchesSearch =
        r.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        r.id.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesStatus = statusFilter === 'all' || r.status === statusFilter;
      const matchesMode = modeFilter === 'all' || r.execution_mode === modeFilter;
      return matchesSearch && matchesStatus && matchesMode;
    });
  }, [runs, searchTerm, statusFilter, modeFilter]);

  return (
    <div className="space-y-6">
      {/* Header & Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Simulations</h2>
          <p className="text-xs text-slate-400 mt-1">
            Configure, launch, and monitor virtual-viewer load tests
          </p>
        </div>

        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-hover text-white text-sm font-semibold rounded-lg shadow-sm transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>New Simulation</span>
        </button>
      </div>

      {isError && (
        <ErrorBanner
          title="Error Fetching Simulations"
          message={error?.message || 'Could not connect to backend'}
          onRetry={refetch}
        />
      )}

      {/* Filter and Search Bar */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-4 flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by name or run ID..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[#0E131F] border border-[#1F2937] rounded-lg pl-9 pr-4 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
          />
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <Filter className="w-3.5 h-3.5" />
            <span>Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-[#0E131F] border border-[#1F2937] text-white rounded px-2.5 py-1 text-xs focus:outline-none focus:border-blue-500"
            >
              <option value="all">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="running">Running</option>
              <option value="completed">Completed</option>
              <option value="stopped">Stopped</option>
              <option value="failed">Failed</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <span>Mode:</span>
            <select
              value={modeFilter}
              onChange={(e) => setModeFilter(e.target.value)}
              className="bg-[#0E131F] border border-[#1F2937] text-white rounded px-2.5 py-1 text-xs focus:outline-none focus:border-blue-500"
            >
              <option value="all">All Modes</option>
              <option value="local">Local</option>
              <option value="distributed">Distributed</option>
            </select>
          </div>
        </div>
      </div>

      {/* Simulations Table */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl overflow-hidden shadow-sm">
        {isLoading ? (
          <div className="p-4">
            <TableSkeleton rows={5} cols={7} />
          </div>
        ) : filteredRuns.length === 0 ? (
          <div className="p-12 text-center text-slate-400 text-sm">
            No simulations found matching current criteria.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#0E131F] text-slate-400 uppercase tracking-wider font-semibold border-b border-[#1F2937]">
                <tr>
                  <th className="py-3 px-4">Simulation</th>
                  <th className="py-3 px-4">Mode</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Target Load</th>
                  <th className="py-3 px-4">Duration</th>
                  <th className="py-3 px-4">Created</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1F2937] text-slate-300">
                {filteredRuns.map((run) => {
                  const isRunning = [
                    'running',
                    'starting',
                    'waiting_for_workers',
                    'stopping',
                  ].includes(run.status);
                  const isPending = run.status === 'pending';

                  return (
                    <tr key={run.id} className="hover:bg-surface-elevated/50 transition-colors">
                      <td className="py-3 px-4">
                        <Link
                          to={`/simulations/${run.id}`}
                          className="font-medium text-white hover:text-blue-400 transition-colors block"
                        >
                          {run.name}
                        </Link>
                        <span className="font-mono text-[11px] text-slate-500">{run.id}</span>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`font-mono text-[11px] px-2 py-0.5 rounded uppercase ${
                            run.execution_mode === 'distributed'
                              ? 'bg-purple-950/60 text-purple-400 border border-purple-800'
                              : 'bg-slate-800 text-slate-300'
                          }`}
                        >
                          {run.execution_mode}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <StatusBadge status={run.status} size="sm" />
                      </td>
                      <td className="py-3 px-4 font-mono">
                        {run.virtual_users.toLocaleString()} users @ {run.spawn_rate}/s
                      </td>
                      <td className="py-3 px-4 font-mono">{run.duration_seconds}s</td>
                      <td className="py-3 px-4 text-slate-400">
                        {new Date(run.created_at).toLocaleDateString()}{' '}
                        {new Date(run.created_at).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {isPending && (
                            <button
                              onClick={() => handleStart(run.id)}
                              disabled={startRun.isPending}
                              className="px-2.5 py-1 bg-emerald-950/70 hover:bg-emerald-900 text-emerald-400 border border-emerald-800 rounded flex items-center gap-1 font-medium transition-colors"
                              title="Start simulation"
                            >
                              <Play className="w-3 h-3 fill-current" />
                              <span>Start</span>
                            </button>
                          )}

                          {isRunning && (
                            <button
                              onClick={() => setStopRunTarget(run.id)}
                              disabled={stopRun.isPending}
                              className="px-2.5 py-1 bg-rose-950/70 hover:bg-rose-900 text-rose-400 border border-rose-800 rounded flex items-center gap-1 font-medium transition-colors"
                              title="Stop simulation"
                            >
                              <Square className="w-3 h-3 fill-current" />
                              <span>Stop</span>
                            </button>
                          )}

                          <Link
                            to={`/simulations/${run.id}`}
                            className="px-2.5 py-1 bg-surface-elevated hover:bg-surface-subtle text-slate-300 hover:text-white rounded border border-[#2D3748] transition-colors"
                          >
                            Details
                          </Link>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create Simulation Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in overflow-y-auto">
          <div className="bg-[#111827] border border-[#1F2937] rounded-xl max-w-xl w-full p-6 shadow-2xl relative my-8">
            <button
              onClick={() => setIsCreateModalOpen(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-2 mb-4">
              <div className="p-2 bg-blue-950/70 text-blue-400 rounded-lg border border-blue-800">
                <Layers className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">New Simulation Configuration</h3>
                <p className="text-xs text-slate-400">Configure synthetic traffic workload parameters</p>
              </div>
            </div>

            {createRun.isError && (
              <ErrorBanner
                title="Creation Error"
                message={(createRun.error as any)?.message || 'Failed to submit simulation configuration'}
              />
            )}

            <form onSubmit={handleSubmit(handleCreateSubmit)} className="space-y-4">
              {/* Simulation Name */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Simulation Name
                </label>
                <input
                  type="text"
                  {...register('name')}
                  placeholder="e.g., Prime Time Playback Ramp Test"
                  className="w-full bg-[#0E131F] border border-[#1F2937] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                />
                {errors.name && <p className="text-xs text-rose-400 mt-1">{errors.name.message}</p>}
              </div>

              {/* Execution Mode Selector */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                  Execution Mode
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <label
                    className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                      selectedMode === 'local'
                        ? 'bg-blue-950/40 border-blue-500/80 text-white'
                        : 'bg-[#0E131F] border-[#1F2937] text-slate-400 hover:border-slate-600'
                    }`}
                  >
                    <input
                      type="radio"
                      value="local"
                      {...register('execution_mode')}
                      className="sr-only"
                    />
                    <div>
                      <span className="text-xs font-bold block">Local Engine</span>
                      <span className="text-[11px] text-slate-400 leading-tight block mt-0.5">
                        Standalone Locust process capped at 1,000 users.
                      </span>
                    </div>
                  </label>

                  <label
                    className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                      selectedMode === 'distributed'
                        ? 'bg-purple-950/40 border-purple-500/80 text-white'
                        : 'bg-[#0E131F] border-[#1F2937] text-slate-400 hover:border-slate-600'
                    }`}
                  >
                    <input
                      type="radio"
                      value="distributed"
                      {...register('execution_mode')}
                      className="sr-only"
                    />
                    <div>
                      <span className="text-xs font-bold block">Distributed Swarm</span>
                      <span className="text-[11px] text-slate-400 leading-tight block mt-0.5">
                        Master-worker ZeroMQ coordination across cluster nodes.
                      </span>
                    </div>
                  </label>
                </div>
              </div>

              {/* Distributed Swarm Info Banner */}
              {selectedMode === 'distributed' && (
                <div className="p-3 bg-purple-950/30 border border-purple-800/80 rounded-lg text-xs space-y-1">
                  <div className="flex items-center gap-2 font-semibold text-purple-300">
                    <Server className="w-4 h-4" />
                    <span>Cluster Capacity Status</span>
                  </div>
                  <p className="text-slate-300">
                    Online Workers: <strong className="text-white">{workers?.length || 0}</strong> | Available Swarm Capacity:{' '}
                    <strong className="text-white">{totalWorkerCapacity.toLocaleString()} viewers</strong>
                  </p>
                  {workers?.length === 0 && (
                    <p className="text-amber-400 flex items-center gap-1 mt-1 font-medium">
                      <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                      Warning: No online workers available. Start worker agent daemons before running.
                    </p>
                  )}
                </div>
              )}

              {/* Virtual Users & Spawn Rate */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    Virtual Users
                  </label>
                  <input
                    type="number"
                    {...register('virtual_users')}
                    className="w-full bg-[#0E131F] border border-[#1F2937] rounded-lg px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-blue-500"
                  />
                  {errors.virtual_users && (
                    <p className="text-xs text-rose-400 mt-1">{errors.virtual_users.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    Spawn Rate (users/s)
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    {...register('spawn_rate')}
                    className="w-full bg-[#0E131F] border border-[#1F2937] rounded-lg px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-blue-500"
                  />
                  {errors.spawn_rate && (
                    <p className="text-xs text-rose-400 mt-1">{errors.spawn_rate.message}</p>
                  )}
                </div>
              </div>

              {/* Duration & Event Type */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    Duration (seconds)
                  </label>
                  <input
                    type="number"
                    {...register('duration_seconds')}
                    className="w-full bg-[#0E131F] border border-[#1F2937] rounded-lg px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-blue-500"
                  />
                  {errors.duration_seconds && (
                    <p className="text-xs text-rose-400 mt-1">{errors.duration_seconds.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    Telemetry Pattern
                  </label>
                  <select
                    {...register('event_type')}
                    className="w-full bg-[#0E131F] border border-[#1F2937] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                  >
                    <option value="playback_start">Playback Start (Default Mix)</option>
                    <option value="playback_progress">Progress Tracking Heavy</option>
                    <option value="playback_complete">Completion Concentrated</option>
                  </select>
                </div>
              </div>

              {/* Watch Duration Range */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    Min Watch Duration (s)
                  </label>
                  <input
                    type="number"
                    {...register('watch_duration_min')}
                    className="w-full bg-[#0E131F] border border-[#1F2937] rounded-lg px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    Max Watch Duration (s)
                  </label>
                  <input
                    type="number"
                    {...register('watch_duration_max')}
                    className="w-full bg-[#0E131F] border border-[#1F2937] rounded-lg px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-blue-500"
                  />
                  {errors.watch_duration_max && (
                    <p className="text-xs text-rose-400 mt-1">{errors.watch_duration_max.message}</p>
                  )}
                </div>
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-3 pt-4 border-t border-[#1F2937]">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="px-4 py-2 bg-surface-elevated hover:bg-surface-subtle text-slate-300 rounded-lg text-xs font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!isValid || isSubmitting || createRun.isPending}
                  className="px-5 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg text-xs font-semibold transition-colors disabled:opacity-50 flex items-center gap-2"
                >
                  {createRun.isPending && (
                    <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  )}
                  Create Simulation
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Stop Run Confirmation Modal */}
      <ConfirmModal
        isOpen={Boolean(stopRunTarget)}
        title="Stop Active Simulation"
        message={`Are you sure you want to stop simulation '${stopRunTarget}'? This will terminate running Locust worker greenlets and finalize database summaries.`}
        confirmLabel="Stop Run"
        isDestructive={true}
        isLoading={stopRun.isPending}
        onConfirm={handleConfirmStop}
        onCancel={() => setStopRunTarget(null)}
      />
    </div>
  );
};
