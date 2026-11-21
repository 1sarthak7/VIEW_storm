import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Gauge,
  Play,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ShieldCheck,
  TrendingUp,
  Download,
  Activity,
  FileCheck,
} from 'lucide-react';
import { request } from '../api/client';
import {
  BenchmarkProfile,
  BenchmarkResult,
  BenchmarkComparison,
  PreflightCheckResponse,
} from '../types/auth';
import { useAuth } from '../context/AuthContext';

export const BenchmarksPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();

  const [selectedProfileName, setSelectedProfileName] = useState<string>('smoke');
  const [approvalConfirmed, setApprovalConfirmed] = useState<boolean>(false);
  const [compareBaselineId, setCompareBaselineId] = useState<string>('');
  const [compareCandidateId, setCompareCandidateId] = useState<string>('');
  const [showComparisonModal, setShowComparisonModal] = useState<boolean>(false);

  // 1. Fetch available profiles
  const { data: profiles = [] } = useQuery<BenchmarkProfile[]>({
    queryKey: ['benchmarkProfiles'],
    queryFn: () => request<BenchmarkProfile[]>('/api/v1/benchmarks/profiles'),
  });

  const selectedProfile = profiles.find((p) => p.name === selectedProfileName) || profiles[0];

  // 2. Fetch preflight readiness check
  const {
    data: preflight,
    refetch: refetchPreflight,
    isLoading: isCheckingPreflight,
  } = useQuery<PreflightCheckResponse>({
    queryKey: ['benchmarkPreflight', selectedProfileName],
    queryFn: () =>
      request<PreflightCheckResponse>('/api/v1/benchmarks/preflight', {
        method: 'POST',
        body: JSON.stringify({ profile_name: selectedProfileName }),
      }),
    enabled: !!selectedProfileName,
  });

  // 3. Fetch historical results
  const { data: results = [] } = useQuery<BenchmarkResult[]>({
    queryKey: ['benchmarkResults'],
    queryFn: () => request<BenchmarkResult[]>('/api/v1/benchmarks/results?limit=25'),
    refetchInterval: 5000,
  });

  // 4. Comparison Query
  const { data: comparison } = useQuery<BenchmarkComparison>({
    queryKey: ['benchmarkCompare', compareBaselineId, compareCandidateId],
    queryFn: () =>
      request<BenchmarkComparison>(
        `/api/v1/benchmarks/compare?baseline_id=${compareBaselineId}&candidate_id=${compareCandidateId}`
      ),
    enabled: !!compareBaselineId && !!compareCandidateId && showComparisonModal,
  });

  // 5. Run Mutation
  const runMutation = useMutation({
    mutationFn: () =>
      request<BenchmarkResult>('/api/v1/benchmarks/run', {
        method: 'POST',
        body: JSON.stringify({
          profile_name: selectedProfileName,
          execution_mode: selectedProfile?.recommended_mode,
          target_environment: 'local',
          approval_confirmed: approvalConfirmed,
          notes: `Launched via Benchmarks Console at ${new Date().toISOString()}`,
        }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['benchmarkResults'] });
      queryClient.invalidateQueries({ queryKey: ['simulations'] });
    },
  });

  const isOperator = hasRole(['admin', 'operator']);

  const handleExportJson = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(results, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `viewstorm-benchmarks-${Date.now()}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const handleOpenCompare = (baseId: string) => {
    setCompareBaselineId(baseId);
    if (results.length > 1) {
      const candidate = results.find((r) => r.id !== baseId);
      if (candidate) {
        setCompareCandidateId(candidate.id);
      }
    }
    setShowComparisonModal(true);
  };

  return (
    <div className="space-y-8 animate-fade-in pb-12">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <Gauge className="w-7 h-7 text-indigo-400" />
            Large-Scale Benchmark Management
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Progressive capacity validation from 10 to 200,000 synthetic virtual users with strict SLA guardrails
          </p>
        </div>

        <button
          onClick={handleExportJson}
          className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-[#111827] border border-[#1F2937] text-slate-300 hover:text-white text-xs font-medium transition"
        >
          <Download className="w-4 h-4 text-slate-400" />
          <span>Export Benchmarks (JSON)</span>
        </button>
      </div>

      {/* Profile Selector Carousel */}
      <div className="space-y-3">
        <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Standardized Benchmark Profiles (Milestone 7)
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-9 gap-2">
          {profiles.map((p) => {
            const isSelected = p.name === selectedProfileName;
            return (
              <button
                key={p.name}
                onClick={() => {
                  setSelectedProfileName(p.name);
                  setApprovalConfirmed(false);
                }}
                className={`p-3 rounded-xl border text-left transition flex flex-col justify-between h-24 ${
                  isSelected
                    ? 'bg-indigo-600/20 border-indigo-500 text-white shadow-lg shadow-indigo-950/50'
                    : 'bg-[#111827] border-[#1F2937] text-slate-400 hover:text-slate-200 hover:border-slate-700'
                }`}
              >
                <div className="font-semibold text-xs capitalize text-white flex items-center justify-between">
                  <span>{p.name.replace('_', ' ')}</span>
                  {p.requires_explicit_approval && (
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400" title="Requires Approval" />
                  )}
                </div>
                <div>
                  <div className="text-lg font-bold font-mono text-indigo-300">
                    {p.virtual_users.toLocaleString()}
                  </div>
                  <div className="text-[10px] text-slate-500">{p.duration_seconds}s • {p.recommended_mode}</div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Selected Profile Execution Panel */}
      {selectedProfile && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Profile Details & SLA Targets */}
          <div className="lg:col-span-2 bg-[#111827] border border-[#1F2937] rounded-2xl p-6 space-y-6">
            <div className="flex items-center justify-between border-b border-[#1F2937] pb-4">
              <div>
                <h3 className="text-lg font-bold text-white capitalize">
                  Profile: {selectedProfile.name.replace('_', ' ')}
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">{selectedProfile.description}</p>
              </div>
              <span className="px-2.5 py-1 rounded-md text-xs font-mono font-medium bg-[#0E131F] border border-[#1F2937] text-indigo-400 uppercase">
                {selectedProfile.recommended_mode} Mode
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="p-3.5 bg-[#0E131F] rounded-xl border border-[#1F2937]">
                <div className="text-xs text-slate-500">Virtual Users</div>
                <div className="text-xl font-bold font-mono text-white mt-1">
                  {selectedProfile.virtual_users.toLocaleString()}
                </div>
              </div>
              <div className="p-3.5 bg-[#0E131F] rounded-xl border border-[#1F2937]">
                <div className="text-xs text-slate-500">Spawn Rate</div>
                <div className="text-xl font-bold font-mono text-white mt-1">
                  {selectedProfile.spawn_rate}/s
                </div>
              </div>
              <div className="p-3.5 bg-[#0E131F] rounded-xl border border-[#1F2937]">
                <div className="text-xs text-slate-500">Max Error Rate (SLA)</div>
                <div className="text-xl font-bold font-mono text-amber-400 mt-1">
                  ≤ {selectedProfile.max_error_rate_pct}%
                </div>
              </div>
              <div className="p-3.5 bg-[#0E131F] rounded-xl border border-[#1F2937]">
                <div className="text-xs text-slate-500">Max p95 Latency (SLA)</div>
                <div className="text-xl font-bold font-mono text-amber-400 mt-1">
                  ≤ {selectedProfile.max_p95_latency_ms} ms
                </div>
              </div>
            </div>

            {/* Preflight Readiness Card */}
            <div className="p-4 bg-[#0E131F] rounded-xl border border-[#1F2937] space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                  <FileCheck className="w-4 h-4 text-indigo-400" />
                  Cluster Preflight Verification
                </span>
                <button
                  onClick={() => refetchPreflight()}
                  disabled={isCheckingPreflight}
                  className="text-[11px] text-indigo-400 hover:underline"
                >
                  {isCheckingPreflight ? 'Checking...' : 'Re-verify'}
                </button>
              </div>

              {preflight ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    {preflight.ready ? (
                      <span className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 text-xs font-semibold">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        PREFLIGHT PASSED
                      </span>
                    ) : (
                      <span className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-rose-500/15 border border-rose-500/30 text-rose-400 text-xs font-semibold">
                        <XCircle className="w-3.5 h-3.5" />
                        PREFLIGHT BLOCKED
                      </span>
                    )}
                    <span className="text-xs text-slate-400">
                      {preflight.available_worker_nodes ?? 0} worker nodes online • Capacity:{' '}
                      <span className="text-white font-mono">{(preflight.total_worker_capacity ?? 0).toLocaleString()}</span> users
                    </span>
                  </div>

                  <ul className="text-xs text-slate-400 space-y-1 pl-1">
                    {(preflight.messages || []).map((m, idx) => (
                      <li key={idx} className="flex items-start gap-1.5">
                        <span className="text-slate-600">•</span>
                        <span>{m}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <div className="text-xs text-slate-500">Evaluating readiness...</div>
              )}
            </div>

            {/* Explicit Authorization Check for High Tier Profiles */}
            {selectedProfile.requires_explicit_approval && (
              <div className="p-4 bg-amber-500/10 border border-amber-500/30 rounded-xl space-y-2">
                <div className="flex items-center gap-2 text-amber-300 text-xs font-semibold">
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                  HIGH-CAPACITY BENCHMARK AUTHORIZATION
                </div>
                <p className="text-xs text-slate-400">
                  This profile generates heavy traffic ({selectedProfile.virtual_users.toLocaleString()} users).
                  Explicit operator authorization is required to prevent accidental saturation.
                </p>
                <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer pt-1">
                  <input
                    type="checkbox"
                    checked={approvalConfirmed}
                    onChange={(e) => setApprovalConfirmed(e.target.checked)}
                    className="rounded border-slate-700 text-indigo-600 focus:ring-indigo-500"
                  />
                  <span>I authorize this large-scale load experiment against authorized test infrastructure.</span>
                </label>
              </div>
            )}

            {/* Launch Control */}
            <div className="flex items-center justify-between pt-2">
              <span className="text-xs text-slate-500">
                All experiments target authorized local/private test environments.
              </span>
              <button
                onClick={() => runMutation.mutate()}
                disabled={
                  !isOperator ||
                  !preflight?.ready ||
                  (selectedProfile.requires_explicit_approval && !approvalConfirmed) ||
                  runMutation.isPending
                }
                className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm rounded-lg shadow-lg shadow-indigo-600/30 disabled:opacity-50 transition"
              >
                <Play className="w-4 h-4 fill-current" />
                <span>{runMutation.isPending ? 'Initiating Benchmark...' : 'Launch Benchmark'}</span>
              </button>
            </div>
          </div>

          {/* Quick Metrics / Guidelines */}
          <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-6 space-y-5">
            <h4 className="text-sm font-bold text-white flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              SLA Safety Safeguards
            </h4>

            <div className="space-y-3 text-xs text-slate-400">
              <div className="p-3 bg-[#0E131F] rounded-xl border border-[#1F2937]">
                <div className="font-semibold text-slate-300 mb-1">Automatic Error Abort</div>
                If error rate exceeds <span className="text-amber-400">2.5× SLA limit</span> (or &gt;12%), the benchmark is aborted immediately.
              </div>
              <div className="p-3 bg-[#0E131F] rounded-xl border border-[#1F2937]">
                <div className="font-semibold text-slate-300 mb-1">Memory Exhaustion Abort</div>
                If host available RAM drops below <span className="text-amber-400">300 MB</span>, execution halts to protect infrastructure.
              </div>
              <div className="p-3 bg-[#0E131F] rounded-xl border border-[#1F2937]">
                <div className="font-semibold text-slate-300 mb-1">Emergency Kill Switch</div>
                Global Emergency Stop locks all runs instantly and terminates worker subprocesses.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Historical Benchmark Runs Table */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Activity className="w-5 h-5 text-indigo-400" />
              Historical Benchmark Experiments
            </h3>
            <p className="text-xs text-slate-400">Verified reproducible benchmarks and SLA compliance records</p>
          </div>
        </div>

        {results.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-sm">
            No benchmarks executed yet. Select a profile above and launch your first experiment.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-[#1F2937] text-slate-400">
                  <th className="pb-3 font-semibold">Profile</th>
                  <th className="pb-3 font-semibold">Configured Users</th>
                  <th className="pb-3 font-semibold">Achieved RPS</th>
                  <th className="pb-3 font-semibold">p95 Latency</th>
                  <th className="pb-3 font-semibold">Error Rate</th>
                  <th className="pb-3 font-semibold">SLA Status</th>
                  <th className="pb-3 font-semibold">Executed At</th>
                  <th className="pb-3 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1F2937]">
                {results.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-800/20">
                    <td className="py-3 font-medium text-white capitalize flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-indigo-400" />
                      {r.profile_name}
                    </td>
                    <td className="py-3 font-mono text-slate-300">{r.virtual_users.toLocaleString()}</td>
                    <td className="py-3 font-mono text-white font-semibold">{r.requests_per_second.toFixed(1)} RPS</td>
                    <td className="py-3 font-mono text-slate-300">{r.p95_latency_ms.toFixed(1)} ms</td>
                    <td className="py-3 font-mono text-slate-300">{r.error_rate_pct.toFixed(2)}%</td>
                    <td className="py-3">
                      {r.abort_reason ? (
                        <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-rose-500/15 border border-rose-500/30 text-rose-400">
                          Aborted
                        </span>
                      ) : r.passed_thresholds ? (
                        <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-500/15 border border-emerald-500/30 text-emerald-400">
                          SLA Passed
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-amber-500/15 border border-amber-500/30 text-amber-400">
                          SLA Breached
                        </span>
                      )}
                    </td>
                    <td className="py-3 text-slate-500">
                      {new Date(r.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </td>
                    <td className="py-3 text-right">
                      <button
                        onClick={() => handleOpenCompare(r.id)}
                        className="text-indigo-400 hover:text-indigo-300 font-medium text-xs hover:underline"
                      >
                        Compare
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Comparison Modal */}
      {showComparisonModal && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="max-w-2xl w-full bg-[#111827] border border-[#1F2937] rounded-2xl p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-[#1F2937] pb-4">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-indigo-400" />
                  Benchmark Regression Comparison
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">Automated delta analysis between baseline and candidate</p>
              </div>
              <button
                onClick={() => setShowComparisonModal(false)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            {/* Selectors */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Baseline Run</label>
                <select
                  value={compareBaselineId}
                  onChange={(e) => setCompareBaselineId(e.target.value)}
                  className="w-full bg-[#0E131F] border border-[#1F2937] rounded-lg px-3 py-2 text-xs text-white"
                >
                  {results.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.profile_name} ({r.virtual_users}u) - {r.requests_per_second.toFixed(1)} RPS
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Candidate Run</label>
                <select
                  value={compareCandidateId}
                  onChange={(e) => setCompareCandidateId(e.target.value)}
                  className="w-full bg-[#0E131F] border border-[#1F2937] rounded-lg px-3 py-2 text-xs text-white"
                >
                  {results.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.profile_name} ({r.virtual_users}u) - {r.requests_per_second.toFixed(1)} RPS
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Comparison Outcome */}
            {comparison && (
              <div className="space-y-4 pt-2">
                <div className="p-4 bg-[#0E131F] rounded-xl border border-[#1F2937] flex items-center justify-between">
                  <div>
                    <span className="text-xs text-slate-500 uppercase">Performance Verdict</span>
                    <div className="text-xl font-bold mt-0.5 flex items-center gap-2">
                      <span
                        className={`px-3 py-1 rounded-md text-sm font-bold tracking-wider ${
                          comparison.performance_verdict === 'IMPROVEMENT'
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                            : comparison.performance_verdict === 'REGRESSION'
                            ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                            : comparison.performance_verdict === 'INCOMPARABLE'
                            ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                            : 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30'
                        }`}
                      >
                        {comparison.performance_verdict}
                      </span>
                    </div>
                  </div>

                  {comparison.incomparable_reason && (
                    <div className="text-xs text-amber-300 max-w-xs text-right">
                      {comparison.incomparable_reason}
                    </div>
                  )}
                </div>

                <div className="grid grid-cols-4 gap-3 text-center">
                  <div className="p-3 bg-[#0E131F] rounded-xl border border-[#1F2937]">
                    <div className="text-xs text-slate-500">Δ Throughput (RPS)</div>
                    <div
                      className={`text-base font-bold font-mono mt-1 ${
                        comparison.rps_delta_pct > 0
                          ? 'text-emerald-400'
                          : comparison.rps_delta_pct < 0
                          ? 'text-rose-400'
                          : 'text-slate-300'
                      }`}
                    >
                      {comparison.rps_delta_pct > 0 ? '+' : ''}
                      {comparison.rps_delta_pct}%
                    </div>
                  </div>

                  <div className="p-3 bg-[#0E131F] rounded-xl border border-[#1F2937]">
                    <div className="text-xs text-slate-500">Δ p95 Latency</div>
                    <div
                      className={`text-base font-bold font-mono mt-1 ${
                        comparison.p95_latency_delta_pct < 0
                          ? 'text-emerald-400'
                          : comparison.p95_latency_delta_pct > 0
                          ? 'text-rose-400'
                          : 'text-slate-300'
                      }`}
                    >
                      {comparison.p95_latency_delta_pct > 0 ? '+' : ''}
                      {comparison.p95_latency_delta_pct}%
                    </div>
                  </div>

                  <div className="p-3 bg-[#0E131F] rounded-xl border border-[#1F2937]">
                    <div className="text-xs text-slate-500">Δ Avg Latency</div>
                    <div
                      className={`text-base font-bold font-mono mt-1 ${
                        comparison.avg_latency_delta_pct < 0
                          ? 'text-emerald-400'
                          : comparison.avg_latency_delta_pct > 0
                          ? 'text-rose-400'
                          : 'text-slate-300'
                      }`}
                    >
                      {comparison.avg_latency_delta_pct > 0 ? '+' : ''}
                      {comparison.avg_latency_delta_pct}%
                    </div>
                  </div>

                  <div className="p-3 bg-[#0E131F] rounded-xl border border-[#1F2937]">
                    <div className="text-xs text-slate-500">Δ Error Rate</div>
                    <div
                      className={`text-base font-bold font-mono mt-1 ${
                        comparison.error_rate_delta_pct <= 0 ? 'text-emerald-400' : 'text-rose-400'
                      }`}
                    >
                      {comparison.error_rate_delta_pct > 0 ? '+' : ''}
                      {comparison.error_rate_delta_pct}%
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
