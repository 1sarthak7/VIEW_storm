import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { MetricPoint } from '../../types/stats';

interface LatencyChartProps {
  metrics: MetricPoint[];
  title?: string;
  height?: number;
}

export const LatencyChart: React.FC<LatencyChartProps> = ({
  metrics,
  title = 'Response Latency Percentiles',
  height = 300,
}) => {
  if (!metrics || metrics.length === 0) {
    return (
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5">
        <h3 className="text-sm font-semibold text-white mb-4">{title}</h3>
        <div className="h-48 flex items-center justify-center text-slate-500 text-sm">
          No latency measurements available yet
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
      avg: Number(m.average_latency_ms.toFixed(2)),
      p50: Number(m.p50_latency_ms.toFixed(2)),
      p95: Number(m.p95_latency_ms.toFixed(2)),
      p99: Number(m.p99_latency_ms.toFixed(2)),
    };
  });

  return (
    <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-white">{title}</h3>
        <span className="text-xs text-slate-400 font-mono">Milliseconds (ms)</span>
      </div>

      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
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
              formatter={(val: number) => [`${val} ms`, '']}
            />
            <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} iconType="circle" />
            <Area
              type="monotone"
              dataKey="p99"
              name="P99 Latency"
              stroke="#F59E0B"
              fill="#F59E0B"
              fillOpacity={0.1}
              strokeWidth={1.5}
            />
            <Area
              type="monotone"
              dataKey="p95"
              name="P95 Latency"
              stroke="#8B5CF6"
              fill="#8B5CF6"
              fillOpacity={0.15}
              strokeWidth={1.5}
            />
            <Area
              type="monotone"
              dataKey="avg"
              name="Average Latency"
              stroke="#3B82F6"
              fill="#3B82F6"
              fillOpacity={0.2}
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
