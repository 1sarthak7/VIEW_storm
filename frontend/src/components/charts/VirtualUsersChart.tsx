import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import { MetricPoint } from '../../types/stats';

interface VirtualUsersChartProps {
  metrics: MetricPoint[];
  title?: string;
  height?: number;
}

export const VirtualUsersChart: React.FC<VirtualUsersChartProps> = ({
  metrics,
  title = 'Active Virtual Users Over Time',
  height = 250,
}) => {
  if (!metrics || metrics.length === 0) {
    return (
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5">
        <h3 className="text-sm font-semibold text-white mb-4">{title}</h3>
        <div className="h-40 flex items-center justify-center text-slate-500 text-sm">
          No virtual user ramp metrics recorded
        </div>
      </div>
    );
  }

  const chartData = metrics.map((m) => {
    const timeStr = new Date(m.timestamp).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
    return {
      time: timeStr,
      users: m.active_users,
    };
  });

  return (
    <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-white">{title}</h3>
        <span className="text-xs text-slate-400 font-mono">Concurrent Viewers</span>
      </div>

      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" vertical={false} />
            <XAxis dataKey="time" stroke="#6B7280" fontSize={11} tickLine={false} />
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
            <Area
              type="stepAfter"
              dataKey="users"
              name="Active Viewers"
              stroke="#6366F1"
              fill="#6366F1"
              fillOpacity={0.2}
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
