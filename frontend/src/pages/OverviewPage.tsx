import React from 'react';
import { Link } from 'react-router-dom';
import {
  Activity,
  Layers,
  Server,
  Zap,
  ArrowRight,
  Cpu,
  Radio,
  Database,
} from 'lucide-react';
import { useRuns } from '../hooks/useRuns';
import { useWorkers } from '../hooks/useWorkers';
import { useHealth } from '../hooks/useHealth';
import { KpiCard } from '../components/common/KpiCard';
import { StatusBadge } from '../components/common/StatusBadge';
import { TableSkeleton } from '../components/common/Skeleton';
import { ErrorBanner } from '../components/common/ErrorBanner';

export const OverviewPage: React.FC = () => {
  const { data: runs, isLoading: runsLoading, isError: runsError, refetch: refetchRuns } = useRuns(5000);
  const { data: workers, isLoading: workersLoading } = useWorkers(undefined, 5000);
  const { data: health, isLoading: healthLoading } = useHealth(5000);

  const totalRuns = runs?.length || 0;
  const activeRuns = runs?.filter((r) =>
    ['running', 'starting', 'waiting_for_workers', 'stopping'].includes(r.status)
  ) || [];

  const totalWorkers = workers?.length || 0;
  const onlineWorkers = workers?.filter((w) => w.status === 'online').length || 0;
  const busyWorkers = workers?.filter((w) => w.status === 'busy').length || 0;
  const staleWorkers = workers?.filter((w) => w.status === 'stale').length || 0;

  const totalActiveUsers = activeRuns.reduce((acc, r) => acc + r.virtual_users, 0);

  const recentRuns = runs ? [...runs].slice(0, 6) : [];

  return (
    <div className="space-y-6">
      {/* Infrastructure Alert if Unhealthy */}
      {health && health.status !== 'healthy' && (
        <ErrorBanner
          title="Cluster Infrastructure Warning"
          message={`System status is ${health.status}. Redis: ${health.redis_status}, PostgreSQL: ${health.database_status}.`}
        />
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          title="Total Simulations"
          value={totalRuns}
          icon={Layers}
          subtitle={`${runs?.filter((r) => r.status === 'completed').length || 0} completed`}
          loading={runsLoading}
        />
        <KpiCard
          title="Active Runs"
          value={activeRuns.length}
          icon={Activity}
          status={activeRuns.length > 0 ? 'success' : 'neutral'}
          subtitle={activeRuns.length > 0 ? 'Simulating virtual traffic' : 'Idle cluster'}
          loading={runsLoading}
        />
        <KpiCard
          title="Active Virtual Viewers"
          value={totalActiveUsers.toLocaleString()}
          icon={Zap}
          unit="users"
          status={totalActiveUsers > 0 ? 'warning' : 'neutral'}
          subtitle="Concurrent load across nodes"
          loading={runsLoading}
        />
        <KpiCard
          title="Online Worker Nodes"
          value={`${onlineWorkers + busyWorkers} / ${totalWorkers}`}
          icon={Server}
          status={onlineWorkers > 0 ? 'success' : totalWorkers === 0 ? 'neutral' : 'warning'}
          subtitle={`${busyWorkers} busy, ${staleWorkers} stale`}
          loading={workersLoading}
        />
      </div>

      {/* Cluster Health & Worker Distribution Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* System Component Health */}
        <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-white">System Component Health</h3>
            <span className="text-xs text-slate-400 font-mono">Live Probes</span>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 rounded-lg bg-surface-elevated border border-[#2A364F]">
              <div className="flex items-center gap-2.5">
                <Activity className="w-4 h-4 text-blue-400" />
                <span className="text-sm font-medium text-slate-200">FastAPI Control Plane</span>
              </div>
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800">
                {healthLoading ? 'Probing...' : 'Operational'}
              </span>
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg bg-surface-elevated border border-[#2A364F]">
              <div className="flex items-center gap-2.5">
                <Radio className="w-4 h-4 text-emerald-400" />
                <span className="text-sm font-medium text-slate-200">Redis 7 Ingestion Cache</span>
              </div>
              <span
                className={`text-xs font-semibold px-2 py-0.5 rounded border ${
                  health?.redis_status === 'healthy'
                    ? 'bg-emerald-950/80 text-emerald-400 border-emerald-800'
                    : 'bg-rose-950/80 text-rose-400 border-rose-800'
                }`}
              >
                {health?.redis_status || 'Checking'}
              </span>
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg bg-surface-elevated border border-[#2A364F]">
              <div className="flex items-center gap-2.5">
                <Database className="w-4 h-4 text-indigo-400" />
                <span className="text-sm font-medium text-slate-200">PostgreSQL 16 Persistence</span>
              </div>
              <span
                className={`text-xs font-semibold px-2 py-0.5 rounded border ${
                  health?.database_status === 'healthy'
                    ? 'bg-emerald-950/80 text-emerald-400 border-emerald-800'
                    : 'bg-rose-950/80 text-rose-400 border-rose-800'
                }`}
              >
                {health?.database_status || 'Checking'}
              </span>
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg bg-surface-elevated border border-[#2A364F]">
              <div className="flex items-center gap-2.5">
                <Server className="w-4 h-4 text-amber-400" />
                <span className="text-sm font-medium text-slate-200">ZeroMQ Master-Worker Bus</span>
              </div>
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800">
                Port 5557 Active
              </span>
            </div>
          </div>
        </div>

        {/* Worker Node Fleet Status */}
        <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-white">Load Generator Swarm Status</h3>
              <p className="text-xs text-slate-400 mt-0.5">Distributed Locust Worker Nodes</p>
            </div>
            <Link
              to="/workers"
              className="text-xs font-medium text-blue-400 hover:text-blue-300 flex items-center gap-1"
            >
              Manage Swarm <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
            <div className="p-3 bg-surface-elevated border border-[#2A364F] rounded-lg">
              <span className="text-xs text-slate-400 block mb-1">Online</span>
              <span className="text-xl font-bold font-mono text-emerald-400">{onlineWorkers}</span>
            </div>
            <div className="p-3 bg-surface-elevated border border-[#2A364F] rounded-lg">
              <span className="text-xs text-slate-400 block mb-1">Busy / Running</span>
              <span className="text-xl font-bold font-mono text-amber-400">{busyWorkers}</span>
            </div>
            <div className="p-3 bg-surface-elevated border border-[#2A364F] rounded-lg">
              <span className="text-xs text-slate-400 block mb-1">Stale</span>
              <span className="text-xl font-bold font-mono text-orange-400">{staleWorkers}</span>
            </div>
            <div className="p-3 bg-surface-elevated border border-[#2A364F] rounded-lg">
              <span className="text-xs text-slate-400 block mb-1">Total Capacity</span>
              <span className="text-xl font-bold font-mono text-white">
                {workers?.reduce((acc, w) => acc + w.capacity, 0).toLocaleString() || 0}
              </span>
            </div>
          </div>

          {/* Mini active workers preview */}
          {workers && workers.length > 0 ? (
            <div className="space-y-2">
              {workers.slice(0, 3).map((w) => (
                <div
                  key={w.id}
                  className="flex items-center justify-between p-2.5 rounded bg-surface-subtle/50 text-xs"
                >
                  <div className="flex items-center gap-2">
                    <Cpu className="w-3.5 h-3.5 text-slate-400" />
                    <span className="font-medium text-slate-200">{w.worker_name}</span>
                    <span className="font-mono text-slate-500">({w.hostname})</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-slate-400 font-mono">Cap: {w.capacity}</span>
                    <StatusBadge status={w.status} size="sm" />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-500 py-3 text-center">
              No worker nodes registered. Launch WorkerAgent instances to join swarm.
            </p>
          )}
        </div>
      </div>

      {/* Recent Simulation Runs Table */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl overflow-hidden shadow-sm">
        <div className="p-5 border-b border-[#1F2937] flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-white">Recent Simulations</h3>
            <p className="text-xs text-slate-400 mt-0.5">Latest synthetic traffic simulations</p>
          </div>
          <Link
            to="/simulations"
            className="text-xs font-medium text-blue-400 hover:text-blue-300 flex items-center gap-1"
          >
            All Simulations <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {runsError && (
          <div className="p-4">
            <ErrorBanner message="Failed to load simulation runs" onRetry={refetchRuns} />
          </div>
        )}

        {runsLoading ? (
          <div className="p-4">
            <TableSkeleton rows={4} cols={6} />
          </div>
        ) : recentRuns.length === 0 ? (
          <div className="p-12 text-center text-slate-400 text-sm">
            No simulation runs created yet. Create a simulation to begin testing.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#0E131F] text-slate-400 uppercase tracking-wider font-semibold border-b border-[#1F2937]">
                <tr>
                  <th className="py-3 px-4">Name / ID</th>
                  <th className="py-3 px-4">Mode</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Virtual Users</th>
                  <th className="py-3 px-4">Duration</th>
                  <th className="py-3 px-4">Created At</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1F2937] text-slate-300">
                {recentRuns.map((run) => (
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
                    <td className="py-3 px-4 font-mono">{run.virtual_users.toLocaleString()}</td>
                    <td className="py-3 px-4 font-mono">{run.duration_seconds}s</td>
                    <td className="py-3 px-4 text-slate-400">
                      {new Date(run.created_at).toLocaleDateString()}{' '}
                      {new Date(run.created_at).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Link
                        to={`/simulations/${run.id}`}
                        className="px-2.5 py-1 bg-surface-elevated hover:bg-surface-subtle text-blue-400 hover:text-blue-300 rounded text-xs border border-[#2D3748] transition-colors"
                      >
                        Inspect
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
