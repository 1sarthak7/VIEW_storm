import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertOctagon, RotateCcw } from 'lucide-react';
import { request } from '../../api/client';
import { EmergencyStopStatus } from '../../types/auth';
import { useAuth } from '../../context/AuthContext';

export const EmergencyStopBanner: React.FC = () => {
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();
  const [clearing, setClearing] = useState(false);

  const { data: status } = useQuery<EmergencyStopStatus>({
    queryKey: ['emergencyStopStatus'],
    queryFn: () => request<EmergencyStopStatus>('/api/v1/admin/emergency-stop/status'),
    refetchInterval: 3000,
  });

  const clearMutation = useMutation({
    mutationFn: () => request('/api/v1/admin/emergency-stop/clear', { method: 'POST' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['emergencyStopStatus'] });
      queryClient.invalidateQueries({ queryKey: ['simulations'] });
      setClearing(false);
    },
    onError: () => {
      setClearing(false);
    },
  });

  if (!status?.active) {
    return null;
  }

  const handleClear = () => {
    setClearing(true);
    clearMutation.mutate();
  };

  const isAdmin = hasRole(['admin']);

  return (
    <div className="bg-rose-950/80 border-b border-rose-500/50 px-6 py-2.5 flex items-center justify-between text-rose-200 text-sm animate-pulse shadow-lg shadow-rose-950/30">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-rose-500/20 border border-rose-500/40 flex items-center justify-center shrink-0">
          <AlertOctagon className="w-5 h-5 text-rose-400" />
        </div>
        <div>
          <span className="font-bold tracking-wide text-rose-100 uppercase text-xs mr-2 px-1.5 py-0.5 rounded bg-rose-500/30 border border-rose-400/40">
            EMERGENCY HALT ENGAGED
          </span>
          <span className="font-medium text-rose-200">
            {status.reason || 'All traffic generation locked by administrator.'}
          </span>
          {status.operator && (
            <span className="text-xs text-rose-300/70 ml-2">
              (Triggered by <span className="font-mono text-rose-200">{status.operator}</span>)
            </span>
          )}
        </div>
      </div>

      {isAdmin && (
        <button
          onClick={handleClear}
          disabled={clearing}
          className="flex items-center gap-1.5 px-3 py-1 bg-rose-600 hover:bg-rose-500 text-white font-medium text-xs rounded-md transition shadow hover:shadow-rose-500/20 disabled:opacity-50 shrink-0"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>{clearing ? 'Clearing...' : 'Clear Emergency Stop'}</span>
        </button>
      )}
    </div>
  );
};
