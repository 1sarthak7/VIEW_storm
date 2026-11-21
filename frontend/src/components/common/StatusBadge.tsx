import React from 'react';
import clsx from 'clsx';
import { SimulationStatus } from '../../types/run';
import { WorkerNodeStatus } from '../../types/worker';

interface StatusBadgeProps {
  status: SimulationStatus | WorkerNodeStatus | string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const normalized = status.toLowerCase();

  let colorClasses = 'bg-slate-800 text-slate-300 border-slate-700';

  if (['running', 'online'].includes(normalized)) {
    colorClasses = 'bg-emerald-950/60 text-emerald-400 border-emerald-800/80';
  } else if (['completed'].includes(normalized)) {
    colorClasses = 'bg-blue-950/60 text-blue-400 border-blue-800/80';
  } else if (['pending', 'waiting_for_workers', 'starting', 'busy'].includes(normalized)) {
    colorClasses = 'bg-amber-950/60 text-amber-400 border-amber-800/80';
  } else if (['degraded', 'stopping', 'stale'].includes(normalized)) {
    colorClasses = 'bg-orange-950/60 text-orange-400 border-orange-800/80';
  } else if (['failed', 'offline', 'incompatible', 'interrupted'].includes(normalized)) {
    colorClasses = 'bg-rose-950/60 text-rose-400 border-rose-800/80';
  } else if (['stopped'].includes(normalized)) {
    colorClasses = 'bg-slate-900 text-slate-400 border-slate-700';
  }

  const isPulse = ['running', 'starting', 'waiting_for_workers', 'stopping'].includes(normalized);

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 font-medium rounded-full border',
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs',
        colorClasses
      )}
    >
      <span
        className={clsx(
          'w-1.5 h-1.5 rounded-full',
          ['running', 'online'].includes(normalized) && 'bg-emerald-400',
          ['completed'].includes(normalized) && 'bg-blue-400',
          ['pending', 'waiting_for_workers', 'starting', 'busy'].includes(normalized) && 'bg-amber-400',
          ['degraded', 'stopping', 'stale'].includes(normalized) && 'bg-orange-400',
          ['failed', 'offline', 'incompatible', 'interrupted'].includes(normalized) && 'bg-rose-400',
          ['stopped'].includes(normalized) && 'bg-slate-400',
          isPulse && 'animate-pulse'
        )}
      />
      <span className="capitalize">{status.replace(/_/g, ' ')}</span>
    </span>
  );
};
