import React from 'react';
import { NavLink } from 'react-router-dom';
import clsx from 'clsx';
import {
  Activity,
  Layers,
  Server,
  BarChart3,
  FileText,
  Settings,
  Zap,
  Gauge,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

interface SidebarProps {
  collapsed: boolean;
  onToggleCollapse: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  collapsed,
  onToggleCollapse,
}) => {
  const navItems = [
    { to: '/', label: 'Overview', icon: Activity },
    { to: '/simulations', label: 'Simulations', icon: Layers },
    { to: '/workers', label: 'Worker Nodes', icon: Server },
    { to: '/benchmarks', label: 'Benchmarks', icon: Gauge },
    { to: '/analytics', label: 'Analytics', icon: BarChart3 },
    { to: '/reports', label: 'Reports', icon: FileText },
    { to: '/settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside
      className={clsx(
        'h-screen bg-[#0E131F] border-r border-[#1F2937] flex flex-col justify-between transition-all duration-300 z-30 sticky top-0',
        collapsed ? 'w-20' : 'w-64'
      )}
    >
      <div>
        {/* Brand / Logo */}
        <div className="h-16 flex items-center justify-between px-5 border-b border-[#1F2937]">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white shadow-md flex-shrink-0">
              <Zap className="w-5 h-5 fill-current" />
            </div>
            {!collapsed && (
              <div className="flex flex-col">
                <span className="font-bold text-white text-base tracking-tight">
                  ViewStorm
                </span>
                <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">
                  v1.0 Distributed
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="p-3 space-y-1.5 mt-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  clsx(
                    'flex items-center gap-3.5 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all group relative',
                    isActive
                      ? 'bg-blue-600/15 text-blue-400 border border-blue-500/20'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-surface-elevated'
                  )
                }
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                {!collapsed ? (
                  <span>{item.label}</span>
                ) : (
                  <div className="absolute left-full ml-3 px-2 py-1 bg-surface-elevated border border-[#2D3748] text-white text-xs rounded shadow-lg opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50 whitespace-nowrap">
                    {item.label}
                  </div>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Footer / Collapse Button */}
      <div className="p-3 border-t border-[#1F2937]">
        <button
          onClick={onToggleCollapse}
          className="w-full flex items-center justify-center p-2 rounded-lg text-slate-400 hover:text-white hover:bg-surface-elevated transition-colors"
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
        </button>
      </div>
    </aside>
  );
};
