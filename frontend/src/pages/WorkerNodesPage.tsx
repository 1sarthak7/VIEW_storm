import React, { useState, useMemo } from 'react';
import {
  Server,
  Filter,
  Clock,
  X,
} from 'lucide-react';
import { useWorkers } from '../hooks/useWorkers';
import { StatusBadge } from '../components/common/StatusBadge';
import { TableSkeleton } from '../components/common/Skeleton';
import { ErrorBanner } from '../components/common/ErrorBanner';
import { WorkerNode } from '../types/worker';

export const WorkerNodesPage: React.FC = () => {
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedWorker, setSelectedWorker] = useState<WorkerNode | null>(null);

  const { data: workers, isLoading, isError, error, refetch } = useWorkers(undefined, 5000);

  const filteredWorkers = useMemo(() => {
    if (!workers) return [];
    if (statusFilter === 'all') return workers;
    return workers.filter((w) => w.status === statusFilter);
  }, [workers, statusFilter]);

  const formatBytes = (bytes: number): string => {
    if (!bytes || bytes === 0) return '0 GB';
    const gb = bytes / (1024 * 1024 * 1024);
    return `${gb.toFixed(1)} GB`;
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Worker Nodes</h2>
          <p className="text-xs text-slate-400 mt-1">
            Registered distributed load-generation nodes and machine telemetry
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-slate-400 bg-[#111827] px-3 py-1.5 rounded-lg border border-[#1F2937]">
            <Filter className="w-3.5 h-3.5" />
            <span>Filter Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-[#0E131F] border border-[#1F2937] text-white rounded px-2 py-0.5 text-xs focus:outline-none focus:border-blue-500"
            >
              <option value="all">All Workers</option>
              <option value="online">Online</option>
              <option value="busy">Busy</option>
              <option value="stale">Stale</option>
              <option value="incompatible">Incompatible</option>
            </select>
          </div>
        </div>
      </div>

      {isError && (
        <ErrorBanner
          title="Failed to Load Worker Nodes"
          message={error?.message || 'Could not fetch worker cluster state'}
          onRetry={refetch}
        />
      )}

      {/* Workers Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <TableSkeleton rows={4} cols={4} />
        </div>
      ) : filteredWorkers.length === 0 ? (
        <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-12 text-center">
          <Server className="w-10 h-10 text-slate-500 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-white mb-1">No Worker Nodes Found</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto mb-4">
            Launch WorkerAgent instances on load-generator instances to connect to this cluster.
          </p>
          <code className="text-[11px] bg-[#0E131F] text-blue-300 px-3 py-1.5 rounded border border-[#1F2937] inline-block font-mono">
            python -m viewstorm_agent.main --server-url http://127.0.0.1:8000
          </code>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredWorkers.map((worker) => (
            <div
              key={worker.id}
              onClick={() => setSelectedWorker(worker)}
              className="bg-[#111827] border border-[#1F2937] hover:border-blue-500/50 rounded-xl p-5 cursor-pointer transition-all shadow-sm group"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-lg bg-surface-elevated text-blue-400 group-hover:bg-blue-950/60 transition-colors">
                    <Server className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white group-hover:text-blue-400 transition-colors">
                      {worker.worker_name}
                    </h3>
                    <span className="font-mono text-[11px] text-slate-500">
                      {worker.hostname}
                    </span>
                  </div>
                </div>
                <StatusBadge status={worker.status} size="sm" />
              </div>

              {/* Hardware stats */}
              <div className="grid grid-cols-3 gap-2 py-3 border-y border-[#1F2937] my-3 text-center">
                <div>
                  <span className="text-[10px] text-slate-500 uppercase font-semibold block mb-0.5">
                    CPU Cores
                  </span>
                  <span className="text-sm font-mono font-bold text-slate-200">
                    {worker.cpu_cores}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 uppercase font-semibold block mb-0.5">
                    Total RAM
                  </span>
                  <span className="text-sm font-mono font-bold text-slate-200">
                    {formatBytes(worker.total_memory_bytes)}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 uppercase font-semibold block mb-0.5">
                    Capacity
                  </span>
                  <span className="text-sm font-mono font-bold text-blue-400">
                    {worker.capacity}
                  </span>
                </div>
              </div>

              {/* Footer info */}
              <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
                <span className="font-mono">Locust v{worker.locust_version}</span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3 text-slate-500" />
                  {new Date(worker.last_heartbeat).toLocaleTimeString()}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Worker Detail Drawer / Modal */}
      {selectedWorker && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="bg-[#111827] border border-[#1F2937] rounded-xl max-w-lg w-full p-6 shadow-2xl relative">
            <button
              onClick={() => setSelectedWorker(null)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 mb-5">
              <div className="p-3 bg-blue-950/60 text-blue-400 rounded-xl border border-blue-800">
                <Server className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">{selectedWorker.worker_name}</h3>
                <span className="font-mono text-xs text-slate-400">ID: {selectedWorker.id}</span>
              </div>
            </div>

            <div className="space-y-4 text-xs">
              <div className="p-3 bg-[#0E131F] border border-[#1F2937] rounded-lg space-y-2">
                <div className="flex justify-between">
                  <span className="text-slate-400">Hardware Identifier:</span>
                  <span className="text-white font-mono">{selectedWorker.worker_identifier}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Network Hostname:</span>
                  <span className="text-white font-mono">{selectedWorker.hostname}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Operating System:</span>
                  <span className="text-white">{selectedWorker.platform}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Locust Version:</span>
                  <span className="text-emerald-400 font-mono font-semibold">
                    {selectedWorker.locust_version}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Software Build:</span>
                  <span className="text-slate-300 font-mono">
                    {selectedWorker.software_version} ({selectedWorker.status})
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-surface-elevated border border-[#2A364F] rounded-lg">
                  <span className="text-slate-400 block mb-1">Total System Memory</span>
                  <span className="text-base font-bold font-mono text-white">
                    {formatBytes(selectedWorker.total_memory_bytes)}
                  </span>
                </div>
                <div className="p-3 bg-surface-elevated border border-[#2A364F] rounded-lg">
                  <span className="text-slate-400 block mb-1">Available Free RAM</span>
                  <span className="text-base font-bold font-mono text-emerald-400">
                    {formatBytes(selectedWorker.available_memory_bytes)}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-surface-elevated border border-[#2A364F] rounded-lg">
                  <span className="text-slate-400 block mb-1">Virtual User Capacity</span>
                  <span className="text-base font-bold font-mono text-blue-400">
                    {selectedWorker.capacity.toLocaleString()} users
                  </span>
                </div>
                <div className="p-3 bg-surface-elevated border border-[#2A364F] rounded-lg">
                  <span className="text-slate-400 block mb-1">Registered Since</span>
                  <span className="text-xs font-mono text-slate-300">
                    {new Date(selectedWorker.registered_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setSelectedWorker(null)}
                className="px-4 py-2 bg-surface-elevated hover:bg-surface-subtle text-slate-300 text-xs font-medium rounded-lg transition-colors border border-[#2D3748]"
              >
                Close Drawer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
