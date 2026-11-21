import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { MetricPoint } from '../../types/stats';

interface ThroughputChartProps {
  metrics: MetricPoint[];
  title?: string;
  height?: number;
}

export const ThroughputChart: React.FC<ThroughputChartProps> = ({
  metrics,
  title = 'Throughput & HTTP Request Rates',
  height = 300,
}) => {
  if (!metrics || metrics.length === 0) {
    return (
      <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5">
        <h3 className="text-sm font-semibold text-white mb-4">{title}</h3>
        <div className="h-48 flex items-center justify-center text-slate-500 text-sm">
          No time-series throughput data available yet
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
      rps: m.requests_per_second,
      success: m.successful_requests,
      failed: m.failed_requests,
    };
  });

  return (
    <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-white">{title}</h3>
        <span className="text-xs text-slate-400 font-mono">Requests / Second</span>
      </div>

      <div style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
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
            <Legend
              wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }}
              iconType="circle"
            />
            <Line
              type="monotone"
              dataKey="rps"
              name="Requests/sec (RPS)"
              stroke="#3B82F6"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
            <Line
              type="monotone"
              dataKey="success"
              name="Successful Requests"
              stroke="#10B981"
              strokeWidth={1.5}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="failed"
              name="Failed Requests"
              stroke="#EF4444"
              strokeWidth={1.5}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
