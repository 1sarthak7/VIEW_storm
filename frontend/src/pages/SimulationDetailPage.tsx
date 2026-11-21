import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Play,
  Square,
  FileText,
  Zap,
  Users,
  CheckCircle,
  Activity,
  Server,
  ArrowLeft,
} from 'lucide-react';
import { useRunDetails } from '../hooks/useRunDetails';
import { useRunStats } from '../hooks/useRunStats';
import { useRunMutations } from '../hooks/useRuns';
import { KpiCard } from '../components/common/KpiCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { ConfirmModal } from '../components/common/ConfirmModal';
import { ErrorBanner } from '../components/common/ErrorBanner';
import { ThroughputChart } from '../components/charts/ThroughputChart';
import { LatencyChart } from '../components/charts/LatencyChart';
import { VirtualUsersChart } from '../components/charts/VirtualUsersChart';
import { EventBreakdownChart } from '../components/charts/EventBreakdownChart';

export const SimulationDetailPage: React.FC = () => {
  const { runId } = useParams<{ runId: string }>();
  const { run, isLoadingRun, errorRun, workers } = useRunDetails(runId);

  const isActiveRun = Boolean(
    run && ['running', 'starting', 'waiting_for_workers', 'stopping'].includes(run.status)
  );

  const { stats, metrics, isLoadingStats } = useRunStats(runId, isActiveRun);
  const { startRun, stopRun } = useRunMutations();

  const [isStopModalOpen, setIsStopModalOpen] = useState(false);

  if (isLoadingRun) {
    return (
      <div className="py-24 text-center">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-sm text-slate-400">Loading simulation telemetry and details...</p>
      </div>
    );
  }

  if (errorRun || !run) {
    return (
      <div className="space-y-4">
        <Link to="/simulations" className="inline-flex items-center gap-2 text-xs text-blue-400 hover:text-blue-300">
          <ArrowLeft className="w-4 h-4" /> Back to Simulations
        </Link>
        <ErrorBanner
          title="Simulation Not Found"
          message={errorRun?.message || `Run '${runId}' could not be located.`}
        />
      </div>
    );
  }

  const isPending = run.status === 'pending';
  const isRunning = ['running', 'starting', 'waiting_for_workers', 'stopping'].includes(run.status);

  // Latest snapshot metrics
  const latestMetric = metrics && metrics.length > 0 ? metrics[metrics.length - 1] : null;

  const currentRps = stats?.current_rps ?? latestMetric?.requests_per_second ?? 0;
  const totalHttpRequests = latestMetric ? latestMetric.successful_requests + latestMetric.failed_requests : stats?.total_events || 0;
  const successfulRequests = latestMetric?.successful_requests ?? stats?.accepted_events ?? 0;
  const failedRequests = latestMetric?.failed_requests ?? stats?.rejected_events ?? 0;

  return (
    <div className="space-y-6">
      {/* Back button & Breadcrumb */}
      <div className="flex items-center justify-between">
        <Link to="/simulations" className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Simulations
        </Link>
        <span className="font-mono text-xs text-slate-500">ID: {run.id}</span>
      </div>

      {/* Header Banner */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1.5">
            <h1 className="text-xl font-bold text-white tracking-tight">{run.name}</h1>
            <StatusBadge status={run.status} />
            <span
              className={`font-mono text-xs px-2 py-0.5 rounded uppercase font-semibold ${
                run.execution_mode === 'distributed'
                  ? 'bg-purple-950/60 text-purple-400 border border-purple-800'
                  : 'bg-slate-800 text-slate-300'
              }`}
            >
              {run.execution_mode}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-x-6 gap-y-1 text-xs text-slate-400">
            <span>Target: <strong className="text-slate-300 font-mono">{run.target_environment}</strong></span>
            <span>Created: <strong className="text-slate-300">{new Date(run.created_at).toLocaleTimeString()}</strong></span>
            {run.started_at && (
              <span>Started: <strong className="text-slate-300">{new Date(run.started_at).toLocaleTimeString()}</strong></span>
            )}
            {stats?.elapsed_seconds !== undefined && stats.elapsed_seconds > 0 && (
              <span>Elapsed: <strong className="text-blue-400 font-mono">{stats.elapsed_seconds.toFixed(1)}s</strong></span>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-3">
          {isPending && (
            <button
              onClick={() => startRun.mutate(run.id)}
              disabled={startRun.isPending}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg flex items-center gap-2 transition-colors disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Launch Simulation</span>
            </button>
          )}

          {isRunning && (
            <button
              onClick={() => setIsStopModalOpen(true)}
              disabled={stopRun.isPending}
              className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold rounded-lg flex items-center gap-2 transition-colors disabled:opacity-50"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
              <span>Stop Simulation</span>
            </button>
          )}

          <Link
            to="/reports"
            className="px-3.5 py-2 bg-surface-elevated hover:bg-surface-subtle text-slate-300 hover:text-white text-xs font-medium rounded-lg border border-[#2D3748] flex items-center gap-1.5 transition-colors"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Reports</span>
          </Link>
        </div>
      </div>

      {run.error_message && (
        <ErrorBanner title="Simulation Execution Error" message={run.error_message} />
      )}

      {/* Main KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          title="Configured Load"
          value={run.virtual_users.toLocaleString()}
          unit="users"
          icon={Users}
          subtitle={`Spawn rate: ${run.spawn_rate}/s`}
        />
        <KpiCard
          title="Throughput (RPS)"
          value={currentRps.toFixed(1)}
          unit="req/s"
          icon={Zap}
          status={currentRps > 0 ? 'success' : 'neutral'}
          subtitle="Real-time Locust request rate"
          loading={isLoadingStats}
        />
        <KpiCard
          title="Accepted Ingestion Events"
          value={stats?.accepted_events ?? 0}
          unit="events"
          icon={CheckCircle}
          status="success"
          subtitle={`Total HTTP: ${totalHttpRequests} | Duplicates: ${stats?.duplicate_events || 0}`}
          loading={isLoadingStats}
        />
        <KpiCard
          title="Unique Viewers"
          value={stats?.unique_viewers_count ?? 0}
          unit="viewers"
          icon={Activity}
          subtitle={`Success: ${successfulRequests} | Failed: ${failedRequests}`}
          loading={isLoadingStats}
        />
      </div>

      {/* Performance Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ThroughputChart metrics={metrics} />
        <LatencyChart metrics={metrics} />
        <VirtualUsersChart metrics={metrics} />
        <EventBreakdownChart eventsByType={stats?.events_by_type || {}} />
      </div>

      {/* Worker Allocations Section */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl overflow-hidden shadow-sm">
        <div className="p-5 border-b border-[#1F2937] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Server className="w-4 h-4 text-purple-400" />
            <h3 className="text-sm font-semibold text-white">
              {run.execution_mode === 'distributed'
                ? 'Distributed Worker Assignments'
                : 'Local Subprocess Execution'}
            </h3>
          </div>
          <span className="text-xs text-slate-400">
            {run.execution_mode === 'distributed'
              ? `${workers.length} nodes assigned`
              : 'Single-machine runner'}
          </span>
        </div>

        {run.execution_mode === 'distributed' ? (
          workers.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-400">
              {isRunning
                ? 'Coordinating and provisioning worker nodes over ZeroMQ...'
                : 'No distributed workers assigned to this simulation run.'}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#0E131F] text-slate-400 uppercase tracking-wider font-semibold border-b border-[#1F2937]">
                  <tr>
                    <th className="py-3 px-4">Worker Identifier</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Assigned Users</th>
                    <th className="py-3 px-4">Active Users</th>
                    <th className="py-3 px-4">Process Count</th>
                    <th className="py-3 px-4">Last Check-in</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1F2937] text-slate-300">
                  {workers.map((w) => (
                    <tr key={w.id} className="hover:bg-surface-elevated/50">
                      <td className="py-3 px-4 font-mono text-slate-200">
                        {w.worker_identifier}
                      </td>
                      <td className="py-3 px-4">
                        <StatusBadge status={w.status} size="sm" />
                      </td>
                      <td className="py-3 px-4 font-mono">{w.assigned_users}</td>
                      <td className="py-3 px-4 font-mono">{w.active_users}</td>
                      <td className="py-3 px-4 font-mono">{w.worker_process_count}</td>
                      <td className="py-3 px-4 text-slate-400">
                        {new Date(w.last_heartbeat).toLocaleTimeString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        ) : (
          <div className="p-5 flex items-center gap-4 text-xs">
            <div className="p-3 bg-slate-800 rounded-lg text-slate-300">
              <Zap className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <p className="font-semibold text-white">Local Standalone Runner Subprocess</p>
              <p className="text-slate-400 mt-0.5">
                Targeting local allowlisted host with isolated CSV artifacts under{' '}
                <code className="text-blue-300 bg-slate-900 px-1 py-0.5 rounded">
                  artifacts/runs/{run.id}
                </code>
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Stop Run Confirmation Modal */}
      <ConfirmModal
        isOpen={isStopModalOpen}
        title="Stop Active Simulation"
        message={`Are you sure you want to stop simulation '${run.id}'? All worker subprocesses will be terminated.`}
        confirmLabel="Stop Run"
        isDestructive={true}
        isLoading={stopRun.isPending}
        onConfirm={async () => {
          await stopRun.mutateAsync(run.id);
          setIsStopModalOpen(false);
        }}
        onCancel={() => setIsStopModalOpen(false)}
      />
    </div>
  );
};
