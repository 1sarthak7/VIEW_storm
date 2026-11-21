import React, { useState } from 'react';
import { Download, Eye, X } from 'lucide-react';
import { useRuns } from '../hooks/useRuns';
import { getRunReport } from '../api/stats';
import { SimulationReport } from '../types/stats';
import { StatusBadge } from '../components/common/StatusBadge';
import { TableSkeleton } from '../components/common/Skeleton';
import { ErrorBanner } from '../components/common/ErrorBanner';

export const ReportsPage: React.FC = () => {
  const { data: runs, isLoading, isError, error, refetch } = useRuns();
  const [activeReport, setActiveReport] = useState<SimulationReport | null>(null);
  const [loadingReportId, setLoadingReportId] = useState<string | null>(null);

  const handleOpenReport = async (runId: string) => {
    setLoadingReportId(runId);
    try {
      const rep = await getRunReport(runId);
      setActiveReport(rep);
    } catch (err: any) {
      alert(`Failed to load report: ${err.message || 'Unknown error'}`);
    } finally {
      setLoadingReportId(null);
    }
  };

  const exportJson = (report: SimulationReport) => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(report, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `${report.run_id}-report.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const exportCsv = (report: SimulationReport) => {
    const headers = [
      'run_id',
      'name',
      'target_environment',
      'status',
      'configured_users',
      'duration_seconds',
      'actual_duration_seconds',
      'total_submissions',
      'accepted_events',
      'rejected_events',
      'duplicate_events',
      'unique_viewers',
      'total_http_requests',
      'successful_http_requests',
      'failed_http_requests',
      'requests_per_second',
      'avg_latency_ms',
      'p50_latency_ms',
      'p95_latency_ms',
      'p99_latency_ms',
    ];

    const values = [
      report.run_id,
      `"${report.name.replace(/"/g, '""')}"`,
      report.target_environment,
      report.status,
      report.configured_users,
      report.duration_seconds,
      report.actual_duration_seconds,
      report.total_submissions,
      report.accepted_events,
      report.rejected_events,
      report.duplicate_events,
      report.unique_viewers,
      report.total_http_requests,
      report.successful_http_requests,
      report.failed_http_requests,
      report.requests_per_second,
      report.avg_latency_ms,
      report.p50_latency_ms,
      report.p95_latency_ms,
      report.p99_latency_ms,
    ];

    const csvContent = 'data:text/csv;charset=utf-8,' + headers.join(',') + '\n' + values.join(',');
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', encodeURI(csvContent));
    downloadAnchor.setAttribute('download', `${report.run_id}-report.csv`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">Simulation Reports</h2>
        <p className="text-xs text-slate-400 mt-1">
          Historical test summaries, performance audits, and raw metrics export
        </p>
      </div>

      {isError && (
        <ErrorBanner
          title="Failed to Load Simulations"
          message={error?.message || 'Could not fetch simulation records'}
          onRetry={refetch}
        />
      )}

      {/* Reports Table */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl overflow-hidden shadow-sm">
        {isLoading ? (
          <div className="p-4">
            <TableSkeleton rows={5} cols={6} />
          </div>
        ) : !runs || runs.length === 0 ? (
          <div className="p-12 text-center text-slate-400 text-sm">
            No simulations recorded yet.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#0E131F] text-slate-400 uppercase tracking-wider font-semibold border-b border-[#1F2937]">
                <tr>
                  <th className="py-3 px-4">Simulation Name / ID</th>
                  <th className="py-3 px-4">Mode</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Configured Load</th>
                  <th className="py-3 px-4">Created Date</th>
                  <th className="py-3 px-4 text-right">Report Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1F2937] text-slate-300">
                {runs.map((r) => (
                  <tr key={r.id} className="hover:bg-surface-elevated/50 transition-colors">
                    <td className="py-3 px-4">
                      <span className="font-semibold text-white block">{r.name}</span>
                      <span className="font-mono text-[11px] text-slate-500">{r.id}</span>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`font-mono text-[11px] px-2 py-0.5 rounded uppercase ${
                          r.execution_mode === 'distributed'
                            ? 'bg-purple-950/60 text-purple-400 border border-purple-800'
                            : 'bg-slate-800 text-slate-300'
                        }`}
                      >
                        {r.execution_mode}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={r.status} size="sm" />
                    </td>
                    <td className="py-3 px-4 font-mono">
                      {r.virtual_users.toLocaleString()} users ({r.duration_seconds}s)
                    </td>
                    <td className="py-3 px-4 text-slate-400">
                      {new Date(r.created_at).toLocaleDateString()}{' '}
                      {new Date(r.created_at).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => handleOpenReport(r.id)}
                        disabled={loadingReportId === r.id}
                        className="px-3 py-1 bg-surface-elevated hover:bg-surface-subtle text-blue-400 hover:text-blue-300 rounded border border-[#2D3748] font-medium transition-colors inline-flex items-center gap-1.5"
                      >
                        {loadingReportId === r.id ? (
                          <span className="w-3 h-3 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
                        ) : (
                          <Eye className="w-3.5 h-3.5" />
                        )}
                        <span>View Report</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Detailed Report Modal */}
      {activeReport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in overflow-y-auto">
          <div className="bg-[#111827] border border-[#1F2937] rounded-xl max-w-2xl w-full p-6 shadow-2xl relative my-8">
            <button
              onClick={() => setActiveReport(null)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>

            {/* Header */}
            <div className="flex items-center justify-between pb-4 border-b border-[#1F2937] mb-4">
              <div>
                <h3 className="text-lg font-bold text-white">{activeReport.name}</h3>
                <span className="font-mono text-xs text-slate-400">
                  Run ID: {activeReport.run_id} | Status:{' '}
                  <strong className="text-white capitalize">{activeReport.status}</strong>
                </span>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => exportJson(activeReport)}
                  className="px-3 py-1.5 bg-surface-elevated hover:bg-surface-subtle text-slate-200 text-xs font-medium rounded border border-[#2D3748] flex items-center gap-1 transition-colors"
                >
                  <Download className="w-3.5 h-3.5 text-blue-400" />
                  <span>JSON</span>
                </button>
                <button
                  onClick={() => exportCsv(activeReport)}
                  className="px-3 py-1.5 bg-surface-elevated hover:bg-surface-subtle text-slate-200 text-xs font-medium rounded border border-[#2D3748] flex items-center gap-1 transition-colors"
                >
                  <Download className="w-3.5 h-3.5 text-emerald-400" />
                  <span>CSV</span>
                </button>
              </div>
            </div>

            {/* Metrics Breakdown Grid */}
            <div className="space-y-4 text-xs">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 bg-[#0E131F] border border-[#1F2937] rounded-lg">
                  <span className="text-slate-400 block mb-1">Configured Load</span>
                  <span className="text-sm font-bold font-mono text-white">
                    {activeReport.configured_users.toLocaleString()} users
                  </span>
                </div>
                <div className="p-3 bg-[#0E131F] border border-[#1F2937] rounded-lg">
                  <span className="text-slate-400 block mb-1">Throughput</span>
                  <span className="text-sm font-bold font-mono text-emerald-400">
                    {activeReport.requests_per_second.toFixed(1)} RPS
                  </span>
                </div>
                <div className="p-3 bg-[#0E131F] border border-[#1F2937] rounded-lg">
                  <span className="text-slate-400 block mb-1">Accepted Events</span>
                  <span className="text-sm font-bold font-mono text-blue-400">
                    {activeReport.accepted_events.toLocaleString()}
                  </span>
                </div>
                <div className="p-3 bg-[#0E131F] border border-[#1F2937] rounded-lg">
                  <span className="text-slate-400 block mb-1">Unique Viewers</span>
                  <span className="text-sm font-bold font-mono text-purple-400">
                    {activeReport.unique_viewers.toLocaleString()}
                  </span>
                </div>
              </div>

              {/* Real Latency Measurements */}
              <div className="p-4 bg-[#0E131F] border border-[#1F2937] rounded-lg">
                <h4 className="font-semibold text-slate-200 mb-2">Locust Latency Measurements</h4>
                <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 text-center">
                  <div>
                    <span className="text-[10px] text-slate-500 uppercase block">Min</span>
                    <span className="font-mono text-slate-200 font-semibold">{activeReport.min_latency_ms.toFixed(1)} ms</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-500 uppercase block">Avg</span>
                    <span className="font-mono text-blue-400 font-semibold">{activeReport.avg_latency_ms.toFixed(1)} ms</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-500 uppercase block">P50</span>
                    <span className="font-mono text-slate-200 font-semibold">{activeReport.p50_latency_ms.toFixed(1)} ms</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-500 uppercase block">P95</span>
                    <span className="font-mono text-purple-400 font-semibold">{activeReport.p95_latency_ms.toFixed(1)} ms</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-500 uppercase block">P99</span>
                    <span className="font-mono text-amber-400 font-semibold">{activeReport.p99_latency_ms.toFixed(1)} ms</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-500 uppercase block">Max</span>
                    <span className="font-mono text-rose-400 font-semibold">{activeReport.max_latency_ms.toFixed(1)} ms</span>
                  </div>
                </div>
              </div>

              {/* Event Distribution Summary */}
              <div className="p-4 bg-[#0E131F] border border-[#1F2937] rounded-lg">
                <h4 className="font-semibold text-slate-200 mb-2">Ingestion Telemetry Breakdown</h4>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
                  <div>
                    <span className="text-[10px] text-slate-500 block">Submissions</span>
                    <span className="font-mono text-slate-200">{activeReport.total_submissions}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-500 block">Accepted</span>
                    <span className="font-mono text-emerald-400">{activeReport.accepted_events}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-500 block">Duplicates (Idempotent)</span>
                    <span className="font-mono text-amber-400">{activeReport.duplicate_events}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-500 block">Rejected</span>
                    <span className="font-mono text-rose-400">{activeReport.rejected_events}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setActiveReport(null)}
                className="px-4 py-2 bg-surface-elevated hover:bg-surface-subtle text-slate-300 text-xs font-medium rounded-lg border border-[#2D3748]"
              >
                Close Report
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
