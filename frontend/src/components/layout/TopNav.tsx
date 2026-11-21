import React from 'react';
import { useLocation } from 'react-router-dom';
import clsx from 'clsx';
import { useHealth } from '../../hooks/useHealth';
import { Database, Radio, Activity } from 'lucide-react';

interface TopNavProps {
  onToggleSidebarMobile?: () => void;
}

export const TopNav: React.FC<TopNavProps> = () => {
  const location = useLocation();
  const { data: health, isLoading } = useHealth();

  const getPageTitle = (path: string) => {
    if (path === '/') return 'Cluster Overview';
    if (path.startsWith('/simulations/')) return 'Simulation Details';
    if (path === '/simulations') return 'Simulation Management';
    if (path === '/workers') return 'Worker Nodes';
    if (path === '/analytics') return 'Performance Analytics';
    if (path === '/reports') return 'Historical Reports';
    if (path === '/settings') return 'Cluster Settings';
    return 'Dashboard';
  };

  const isHealthy = health?.status === 'healthy';
  const isRedisOk = health?.redis_status === 'healthy';
  const isDbOk = health?.database_status === 'healthy';

  return (
    <header className="h-16 bg-[#0E131F] border-b border-[#1F2937] px-6 flex items-center justify-between sticky top-0 z-20">
      <div>
        <h1 className="text-lg font-bold text-white tracking-tight">
          {getPageTitle(location.pathname)}
        </h1>
        <p className="text-xs text-slate-400 hidden sm:block">
          Distributed Virtual-Viewer Simulation Platform
        </p>
      </div>

      {/* System Health Indicators */}
      <div className="flex items-center gap-3">
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

        <div className="hidden sm:flex items-center gap-1 text-[11px] font-mono text-slate-500 bg-[#111827] px-2.5 py-1 rounded border border-[#1F2937]">
          <Activity className="w-3 h-3 text-slate-400" />
          <span>v1.0.0</span>
        </div>
      </div>
    </header>
  );
};
