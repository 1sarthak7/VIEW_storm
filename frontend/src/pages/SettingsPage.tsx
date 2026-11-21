import React, { useState } from 'react';
import {
  Server,
  Radio,
  Database,
  CheckCircle,
  RefreshCw,
} from 'lucide-react';
import { useHealth } from '../hooks/useHealth';

export const SettingsPage: React.FC = () => {
  const { data: health, isLoading, refetch } = useHealth();
  const [pollingInterval, setPollingInterval] = useState('5000');
  const [savedNotice, setSavedNotice] = useState(false);

  const handleSavePreferences = () => {
    localStorage.setItem('viewstorm_poll_interval', pollingInterval);
    setSavedNotice(true);
    setTimeout(() => setSavedNotice(false), 3000);
  };

  const isHealthy = health?.status === 'healthy';

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">Cluster Settings & Diagnostics</h2>
        <p className="text-xs text-slate-400 mt-1">
          Infrastructure health audit, version telemetry, and frontend polling configuration
        </p>
      </div>

      {/* Backend Infrastructure Diagnostics */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2.5">
            <Server className="w-5 h-5 text-blue-400" />
            <h3 className="text-sm font-semibold text-white">Core Infrastructure Status</h3>
          </div>
          <button
            onClick={() => refetch()}
            className="flex items-center gap-1.5 px-3 py-1 bg-surface-elevated hover:bg-surface-subtle text-xs text-slate-300 rounded border border-[#2D3748] transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
            <span>Probe Cluster</span>
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 rounded-lg bg-[#0E131F] border border-[#1F2937]">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-slate-400">FastAPI Backend</span>
              <span
                className={`w-2 h-2 rounded-full ${
                  isLoading ? 'bg-slate-500 animate-pulse' : isHealthy ? 'bg-emerald-400' : 'bg-rose-400'
                }`}
              />
            </div>
            <span className="text-sm font-mono font-bold text-white block">
              {health?.version ? `v${health.version}` : 'Connecting...'}
            </span>
            <span className="text-[11px] text-slate-500 mt-1 block">
              Environment: {health?.environment || 'local'}
            </span>
          </div>

          <div className="p-4 rounded-lg bg-[#0E131F] border border-[#1F2937]">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1.5">
                <Radio className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-xs text-slate-400">Redis 7 Ingestion</span>
              </div>
              <span
                className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                  health?.redis_status === 'healthy'
                    ? 'bg-emerald-950/80 text-emerald-400'
                    : 'bg-rose-950/80 text-rose-400'
                }`}
              >
                {health?.redis_status || 'Probing'}
              </span>
            </div>
            <span className="text-sm font-mono font-bold text-white block">Port 6379</span>
            <span className="text-[11px] text-slate-500 mt-1 block">Atomic Lua Ingestion Active</span>
          </div>

          <div className="p-4 rounded-lg bg-[#0E131F] border border-[#1F2937]">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5 text-indigo-400" />
                <span className="text-xs text-slate-400">PostgreSQL 16</span>
              </div>
              <span
                className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                  health?.database_status === 'healthy'
                    ? 'bg-emerald-950/80 text-emerald-400'
                    : 'bg-rose-950/80 text-rose-400'
                }`}
              >
                {health?.database_status || 'Probing'}
              </span>
            </div>
            <span className="text-sm font-mono font-bold text-white block">Port 5432</span>
            <span className="text-[11px] text-slate-500 mt-1 block">Alembic Version Synced</span>
          </div>
        </div>

        <div className="mt-4 p-3 bg-surface-elevated/40 rounded border border-[#2A364F] flex items-center justify-between text-xs text-slate-400">
          <span>Backend Uptime:</span>
          <span className="font-mono text-white">
            {health?.uptime_seconds ? `${Math.floor(health.uptime_seconds / 60)}m ${Math.floor(health.uptime_seconds % 60)}s` : 'Unknown'}
          </span>
        </div>
      </div>

      {/* Software and Engine Versions */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-6 shadow-sm">
        <h3 className="text-sm font-semibold text-white mb-3">Software & Engine Versions</h3>
        <div className="divide-y divide-[#1F2937] text-xs">
          <div className="py-2.5 flex justify-between">
            <span className="text-slate-400">ViewStorm Platform</span>
            <span className="text-white font-mono font-semibold">1.0.0 (Milestone 5)</span>
          </div>
          <div className="py-2.5 flex justify-between">
            <span className="text-slate-400">Locust Load Engine</span>
            <span className="text-emerald-400 font-mono font-semibold">2.47.0 (Pinned)</span>
          </div>
          <div className="py-2.5 flex justify-between">
            <span className="text-slate-400">FastAPI Framework</span>
            <span className="text-white font-mono">0.115.0</span>
          </div>
          <div className="py-2.5 flex justify-between">
            <span className="text-slate-400">Distributed Coordination Bus</span>
            <span className="text-blue-400 font-mono">ZeroMQ (Port 5557)</span>
          </div>
          <div className="py-2.5 flex justify-between">
            <span className="text-slate-400">Frontend Technology</span>
            <span className="text-white font-mono">React 19 + TypeScript + Vite + Tailwind CSS</span>
          </div>
        </div>
      </div>

      {/* Preferences & Polling Control */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-6 shadow-sm">
        <h3 className="text-sm font-semibold text-white mb-1">Frontend Dashboard Preferences</h3>
        <p className="text-xs text-slate-400 mb-4">
          Adjust live metrics polling frequency and display controls
        </p>

        <div className="space-y-4 max-w-md text-xs">
          <div>
            <label className="block text-slate-300 font-semibold mb-1">
              Active Simulation Polling Frequency
            </label>
            <select
              value={pollingInterval}
              onChange={(e) => setPollingInterval(e.target.value)}
              className="w-full bg-[#0E131F] border border-[#1F2937] text-white rounded-lg p-2 focus:outline-none focus:border-blue-500"
            >
              <option value="2000">Fast (Every 2 seconds - Recommended for live tests)</option>
              <option value="5000">Standard (Every 5 seconds)</option>
              <option value="10000">Conservative (Every 10 seconds)</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-300 font-semibold mb-1">API Base URL</label>
            <input
              type="text"
              disabled
              value={import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'}
              className="w-full bg-[#0E131F] border border-[#1F2937] text-slate-400 rounded-lg p-2 font-mono"
            />
            <p className="text-[11px] text-slate-500 mt-1">Configured via VITE_API_BASE_URL environment variable.</p>
          </div>

          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={handleSavePreferences}
              className="px-4 py-2 bg-primary hover:bg-primary-hover text-white text-xs font-semibold rounded-lg transition-colors"
            >
              Save Preferences
            </button>
            {savedNotice && (
              <span className="text-xs text-emerald-400 flex items-center gap-1">
                <CheckCircle className="w-3.5 h-3.5" /> Saved successfully
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
