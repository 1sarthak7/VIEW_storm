import React from 'react';
import clsx from 'clsx';
import { LucideIcon } from 'lucide-react';

interface KpiCardProps {
  title: string;
  value: string | number;
  unit?: string;
  icon?: LucideIcon;
  subtitle?: string;
  status?: 'success' | 'warning' | 'danger' | 'neutral';
  loading?: boolean;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  title,
  value,
  unit,
  icon: Icon,
  subtitle,
  status = 'neutral',
  loading = false,
}) => {
  return (
    <div className="bg-[#111827] border border-[#1F2937] hover:border-[#2D3748] transition-colors rounded-xl p-5 shadow-sm">
      <div className="flex items-center justify-between text-slate-400 mb-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          {title}
        </span>
        {Icon && (
          <div className="p-2 rounded-lg bg-surface-elevated text-slate-300">
            <Icon className="w-4 h-4" />
          </div>
        )}
      </div>

      <div className="flex items-baseline gap-2">
        {loading ? (
          <div className="h-8 w-24 bg-slate-800 animate-pulse rounded my-1" />
        ) : (
          <span
            className={clsx(
              'text-2xl font-bold font-mono tracking-tight',
              status === 'success' && 'text-emerald-400',
              status === 'warning' && 'text-amber-400',
              status === 'danger' && 'text-rose-400',
              status === 'neutral' && 'text-white'
            )}
          >
            {value}
          </span>
        )}
        {unit && !loading && (
          <span className="text-xs text-slate-500 font-medium">{unit}</span>
        )}
      </div>

      {subtitle && (
        <p className="text-xs text-slate-400 mt-2 font-medium">{subtitle}</p>
      )}
    </div>
  );
};
