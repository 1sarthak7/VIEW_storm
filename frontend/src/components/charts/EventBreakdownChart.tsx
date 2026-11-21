import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from 'recharts';

interface EventBreakdownChartProps {
  eventsByType: Record<string, number>;
  title?: string;
  height?: number;
}

const COLORS = ['#3B82F6', '#10B981', '#8B5CF6', '#F59E0B', '#EC4899'];

export const EventBreakdownChart: React.FC<EventBreakdownChartProps> = ({
  eventsByType,
  title = 'Playback Event Distribution',
  height = 250,
}) => {
  const data = Object.entries(eventsByType || {}).map(([key, value]) => ({
    name: key.replace('playback_', ''),
    count: value,
  }));

  if (data.length === 0 || data.every((d) => d.count === 0)) {
    return (
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5">
        <h3 className="text-sm font-semibold text-white mb-4">{title}</h3>
        <div className="h-40 flex items-center justify-center text-slate-500 text-sm">
          No playback events received yet
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-white">{title}</h3>
        <span className="text-xs text-slate-400 font-mono">Events Count</span>
      </div>

      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
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
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {data.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
