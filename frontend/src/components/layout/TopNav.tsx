import React, { useState } from 'react';
import { useLocation, Link } from 'react-router-dom';
import clsx from 'clsx';
import { useHealth } from '../../hooks/useHealth';
import { useAuth } from '../../context/AuthContext';
import { request } from '../../api/client';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Database,
  Radio,
  Activity,
  AlertOctagon,
  LogOut,
  LogIn,
} from 'lucide-react';

interface TopNavProps {
  onToggleSidebarMobile?: () => void;
}

export const TopNav: React.FC<TopNavProps> = () => {
  const location = useLocation();
  const queryClient = useQueryClient();
  const { data: health, isLoading } = useHealth();
  const { user, isAuthenticated, logout, hasRole } = useAuth();
  const [showStopModal, setShowStopModal] = useState(false);
  const [stopReason, setStopReason] = useState('Manual emergency stop triggered via console');

  const stopMutation = useMutation({
    mutationFn: () =>
      request('/api/v1/admin/emergency-stop', {
        method: 'POST',
        body: JSON.stringify({ reason: stopReason }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emergencyStopStatus'] });
      queryClient.invalidateQueries({ queryKey: ['simulations'] });
      setShowStopModal(false);
    },
  });

  const getPageTitle = (path: string) => {
    if (path === '/') return 'Cluster Overview';
    if (path.startsWith('/simulations/')) return 'Simulation Details';
    if (path === '/simulations') return 'Simulation Management';
    if (path === '/workers') return 'Worker Nodes';
    if (path === '/benchmarks') return 'Benchmark Management';
    if (path === '/analytics') return 'Performance Analytics';
    if (path === '/reports') return 'Historical Reports';
    if (path === '/settings') return 'Cluster Settings';
    if (path === '/login') return 'Operator Authentication';
    return 'Dashboard';
  };

  const isHealthy = health?.status === 'healthy';
  const isRedisOk = health?.redis_status === 'healthy';
  const isDbOk = health?.database_status === 'healthy';

  return (
    <>
      <header className="h-16 bg-[#0E131F] border-b border-[#1F2937] px-6 flex items-center justify-between sticky top-0 z-20">
        <div>
          <h1 className="text-lg font-bold text-white tracking-tight">
            {getPageTitle(location.pathname)}
          </h1>
          <p className="text-xs text-slate-400 hidden sm:block">
            Distributed Virtual-Viewer Simulation Platform
          </p>
        </div>

        {/* Action Controls & Health */}
        <div className="flex items-center gap-3">
          {/* Emergency Stop Button (Admin/Operator) */}
          {hasRole(['admin', 'operator']) && (
            <button
              onClick={() => setShowStopModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-400 hover:bg-rose-500/25 hover:text-rose-300 text-xs font-semibold transition"
              title="Engage system-wide emergency halt"
            >
              <AlertOctagon className="w-3.5 h-3.5" />
              <span className="hidden md:inline">Emergency Halt</span>
            </button>
          )}

          {/* System Health Indicators */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#111827] border border-[#1F2937] text-xs">
            <div className="flex items-center gap-1.5" title="API Status">
              <span
                className={clsx(
                  'w-2 h-2 rounded-full',
                  isLoading ? 'bg-slate-500 animate-pulse' : isHealthy ? 'bg-emerald-400' : 'bg-rose-400'
                )}
              />
              <span className="text-slate-300 font-medium hidden md:inline">API</span>
            </div>

            <span className="text-slate-600">|</span>

            <div className="flex items-center gap-1.5" title="Redis Connectivity">
              <Radio className={clsx('w-3.5 h-3.5', isRedisOk ? 'text-emerald-400' : 'text-rose-400')} />
              <span className="text-slate-300 font-medium hidden lg:inline">Redis</span>
            </div>

            <span className="text-slate-600">|</span>

            <div className="flex items-center gap-1.5" title="PostgreSQL Connectivity">
              <Database className={clsx('w-3.5 h-3.5', isDbOk ? 'text-emerald-400' : 'text-rose-400')} />
              <span className="text-slate-300 font-medium hidden lg:inline">PostgreSQL</span>
            </div>
          </div>

          {/* Operator Auth Profile */}
          {isAuthenticated && user ? (
            <div className="flex items-center gap-2 bg-[#111827] px-3 py-1 rounded-lg border border-[#1F2937]">
              <div className="text-right">
                <div className="text-xs font-semibold text-slate-200">{user.username}</div>
                <div className="text-[10px] uppercase font-mono tracking-wider text-indigo-400">
                  {user.role}
                </div>
              </div>
              <button
                onClick={logout}
                className="text-slate-400 hover:text-rose-400 p-1 rounded transition"
                title="Sign Out"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <Link
              to="/login"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600/20 border border-indigo-500/30 text-indigo-300 hover:bg-indigo-600/30 text-xs font-medium transition"
            >
              <LogIn className="w-3.5 h-3.5" />
              <span>Sign In</span>
            </Link>
          )}

          <div className="hidden sm:flex items-center gap-1 text-[11px] font-mono text-slate-500 bg-[#111827] px-2.5 py-1 rounded border border-[#1F2937]">
            <Activity className="w-3 h-3 text-slate-400" />
            <span>v1.0.0</span>
          </div>
        </div>
      </header>

      {/* Emergency Stop Confirmation Modal */}
      {showStopModal && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="max-w-md w-full bg-[#111827] border border-rose-500/50 rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="w-12 h-12 rounded-xl bg-rose-500/20 border border-rose-500/40 flex items-center justify-center text-rose-400">
              <AlertOctagon className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">Engage Global Emergency Stop?</h3>
              <p className="text-xs text-slate-400 mt-1">
                This immediately aborts all running local and distributed Locust load generators,
                locks all new simulation creation, and transitions active runs to INTERRUPTED state.
              </p>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Audit Reason
              </label>
              <input
                type="text"
                value={stopReason}
                onChange={(e) => setStopReason(e.target.value)}
                className="w-full bg-[#0E131F] border border-[#1F2937] rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-rose-500"
                placeholder="Reason for emergency halt"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setShowStopModal(false)}
                className="px-3.5 py-2 text-xs font-medium text-slate-300 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={() => stopMutation.mutate()}
                disabled={stopMutation.isPending}
                className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white font-semibold text-xs rounded-lg shadow-lg shadow-rose-600/30 transition disabled:opacity-50"
              >
                {stopMutation.isPending ? 'Engaging Halt...' : 'Confirm Emergency Halt'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
