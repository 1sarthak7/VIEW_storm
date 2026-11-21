import React, { useState, useEffect } from 'react';
import { CheckSquare, Square } from 'lucide-react';
import { useRuns } from '../hooks/useRuns';
import { getRunReport } from '../api/stats';
import { SimulationReport } from '../types/stats';
import { StatusBadge } from '../components/common/StatusBadge';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';

export const AnalyticsPage: React.FC = () => {
  const { data: runs, isLoading: runsLoading } = useRuns();
  const [selectedRunIds, setSelectedRunIds] = useState<string[]>([]);
  const [reports, setReports] = useState<Record<string, SimulationReport>>({});
  const [loadingReports, setLoadingReports] = useState(false);

  // Auto-select latest 2 completed runs by default
  useEffect(() => {
    if (runs && runs.length > 0 && selectedRunIds.length === 0) {
      const completed = runs.filter((r) => r.status === 'completed' || r.status === 'stopped');
      if (completed.length >= 2) {
        setSelectedRunIds([completed[0].id, completed[1].id]);
      } else if (completed.length === 1) {
        setSelectedRunIds([completed[0].id]);
      }
    }
  }, [runs]);

  // Fetch reports for selected runs
  useEffect(() => {
    async function loadReports() {
      if (selectedRunIds.length === 0) return;
      setLoadingReports(true);
      const newReports: Record<string, SimulationReport> = { ...reports };

      await Promise.all(
        selectedRunIds.map(async (id) => {
          if (!newReports[id]) {
            try {
              const rep = await getRunReport(id);
              newReports[id] = rep;
            } catch (err) {
              console.error(`Failed to load report for ${id}:`, err);
            }
          }
        })
      );

      setReports(newReports);
      setLoadingReports(false);
    }

    loadReports();
  }, [selectedRunIds]);

  const toggleSelect = (runId: string) => {
    setSelectedRunIds((prev) =>
      prev.includes(runId) ? prev.filter((id) => id !== runId) : [...prev, runId]
    );
  };

  const selectedReportsList = selectedRunIds
    .map((id) => reports[id])
    .filter(Boolean) as SimulationReport[];

  // Comparison Bar Chart Data
  const throughputComparisonData = selectedReportsList.map((r) => ({
    name: r.name.length > 15 ? `${r.name.substring(0, 15)}...` : r.name,
    rps: Number(r.requests_per_second.toFixed(1)),
    users: r.configured_users,
    acceptedEvents: r.accepted_events,
  }));

  const latencyComparisonData = selectedReportsList.map((r) => ({
    name: r.name.length > 15 ? `${r.name.substring(0, 15)}...` : r.name,
    avg: Number(r.avg_latency_ms.toFixed(2)),
    p95: Number(r.p95_latency_ms.toFixed(2)),
    p99: Number(r.p99_latency_ms.toFixed(2)),
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">Performance Analytics</h2>
        <p className="text-xs text-slate-400 mt-1">
          Compare multi-run simulation measurements, throughput scaling, and latency profiles
        </p>
      </div>

      {/* Run Selection Panel */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-white">Select Simulations to Compare</h3>
          <span className="text-xs text-slate-400 font-mono">
            {selectedRunIds.length} selected
          </span>
        </div>

        {runsLoading ? (
          <div className="h-16 flex items-center justify-center text-slate-500 text-xs">
            Loading simulations...
          </div>
        ) : !runs || runs.length === 0 ? (
          <p className="text-xs text-slate-400 py-3">No simulation runs available for analysis.</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 max-h-48 overflow-y-auto pr-1">
            {runs.map((r) => {
              const isSelected = selectedRunIds.includes(r.id);
              return (
                <div
                  key={r.id}
                  onClick={() => toggleSelect(r.id)}
                  className={`flex items-center justify-between p-2.5 rounded-lg border cursor-pointer text-xs transition-colors ${
                    isSelected
                      ? 'bg-blue-950/40 border-blue-500/80 text-white'
                      : 'bg-[#0E131F] border-[#1F2937] text-slate-400 hover:border-slate-600'
                  }`}
                >
                  <div className="flex items-center gap-2 overflow-hidden">
                    {isSelected ? (
                      <CheckSquare className="w-4 h-4 text-blue-400 flex-shrink-0" />
                    ) : (
                      <Square className="w-4 h-4 text-slate-600 flex-shrink-0" />
                    )}
                    <span className="font-medium truncate">{r.name}</span>
                  </div>
                  <span className="font-mono text-[11px] text-slate-500 ml-2">
                    {r.virtual_users}u
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {loadingReports && (
        <div className="p-4 text-center text-xs text-slate-400 animate-pulse">
          Retrieving real-time performance summaries and CSV metrics...
        </div>
      )}

      {selectedReportsList.length === 0 ? (
        <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-12 text-center text-slate-400 text-sm">
          Select two or more simulation runs above to compare performance metrics.
        </div>
      ) : (
        <>
          {/* Comparative Metrics Table */}
          <div className="bg-[#111827] border border-[#1F2937] rounded-xl overflow-hidden shadow-sm">
            <div className="p-5 border-b border-[#1F2937]">
              <h3 className="text-sm font-semibold text-white">Side-by-Side Comparison</h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Detailed telemetry and response latency measurements
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#0E131F] text-slate-400 uppercase tracking-wider font-semibold border-b border-[#1F2937]">
                  <tr>
                    <th className="py-3 px-4">Metric</th>
                    {selectedReportsList.map((r) => (
                      <th key={r.run_id} className="py-3 px-4 font-mono">
                        {r.name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1F2937] text-slate-300">
                  <tr>
                    <td className="py-2.5 px-4 font-semibold text-white">Status</td>
                    {selectedReportsList.map((r) => (
                      <td key={r.run_id} className="py-2.5 px-4">
                        <StatusBadge status={r.status} size="sm" />
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-2.5 px-4 font-semibold text-white">Virtual Users</td>
                    {selectedReportsList.map((r) => (
                      <td key={r.run_id} className="py-2.5 px-4 font-mono">
                        {r.configured_users.toLocaleString()} users
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-2.5 px-4 font-semibold text-white">Throughput (RPS)</td>
                    {selectedReportsList.map((r) => (
                      <td key={r.run_id} className="py-2.5 px-4 font-mono text-emerald-400 font-bold">
                        {r.requests_per_second.toFixed(1)} req/s
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-2.5 px-4 font-semibold text-white">Total HTTP Requests</td>
                    {selectedReportsList.map((r) => (
                      <td key={r.run_id} className="py-2.5 px-4 font-mono">
                        {r.total_http_requests.toLocaleString()}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-2.5 px-4 font-semibold text-white">Accepted Playback Events</td>
                    {selectedReportsList.map((r) => (
                      <td key={r.run_id} className="py-2.5 px-4 font-mono text-blue-400">
                        {r.accepted_events.toLocaleString()}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-2.5 px-4 font-semibold text-white">Average Latency</td>
                    {selectedReportsList.map((r) => (
                      <td key={r.run_id} className="py-2.5 px-4 font-mono">
                        {r.avg_latency_ms.toFixed(2)} ms
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-2.5 px-4 font-semibold text-white">P95 Latency</td>
                    {selectedReportsList.map((r) => (
                      <td key={r.run_id} className="py-2.5 px-4 font-mono text-purple-400">
                        {r.p95_latency_ms.toFixed(2)} ms
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-2.5 px-4 font-semibold text-white">P99 Latency</td>
                    {selectedReportsList.map((r) => (
                      <td key={r.run_id} className="py-2.5 px-4 font-mono text-amber-400">
                        {r.p99_latency_ms.toFixed(2)} ms
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <td className="py-2.5 px-4 font-semibold text-white">Failure Rate</td>
                    {selectedReportsList.map((r) => {
                      const total = r.successful_http_requests + r.failed_http_requests;
                      const failRate = total > 0 ? (r.failed_http_requests / total) * 100 : 0;
                      return (
                        <td
                          key={r.run_id}
                          className={`py-2.5 px-4 font-mono font-semibold ${
                            failRate > 0 ? 'text-rose-400' : 'text-slate-400'
                          }`}
                        >
                          {failRate.toFixed(2)}% ({r.failed_http_requests} failed)
                        </td>
                      );
                    })}
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Comparative Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5">
              <h3 className="text-sm font-semibold text-white mb-4">Throughput Comparison (RPS)</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={throughputComparisonData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" vertical={false} />
                    <XAxis dataKey="name" stroke="#6B7280" fontSize={11} tickLine={false} />
                    <YAxis stroke="#6B7280" fontSize={11} tickLine={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1F2937',
                        borderColor: '#374151',
                        borderRadius: '8px',
                        color: '#F9FAFB',
                        fontSize: '12px',
                      }}
                    />
                    <Bar dataKey="rps" name="Requests/sec" fill="#3B82F6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5">
              <h3 className="text-sm font-semibold text-white mb-4">Latency Percentiles (ms)</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={latencyComparisonData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" vertical={false} />
                    <XAxis dataKey="name" stroke="#6B7280" fontSize={11} tickLine={false} />
                    <YAxis stroke="#6B7280" fontSize={11} tickLine={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1F2937',
                        borderColor: '#374151',
                        borderRadius: '8px',
                        color: '#F9FAFB',
                        fontSize: '12px',
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                    <Bar dataKey="avg" name="Avg ms" fill="#3B82F6" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="p95" name="P95 ms" fill="#8B5CF6" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="p99" name="P99 ms" fill="#F59E0B" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
