import React from 'react';

export const TableSkeleton: React.FC<{ rows?: number; cols?: number }> = ({
  rows = 5,
  cols = 5,
}) => {
  return (
    <div className="w-full animate-pulse">
      <div className="h-10 bg-surface-elevated rounded-t-lg mb-2" />
      {Array.from({ length: rows }).map((_, r) => (
        <div key={r} className="flex gap-4 py-3 border-b border-[#1F2937]">
          {Array.from({ length: cols }).map((_, c) => (
            <div
              key={c}
              className="h-4 bg-slate-800 rounded"
              style={{ width: `${Math.max(15, 100 / cols - 5)}%` }}
            />
          ))}
        </div>
      ))}
    </div>
  );
};

export const CardSkeleton: React.FC = () => {
  return (
    <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-5 animate-pulse">
      <div className="h-3 w-28 bg-slate-800 rounded mb-3" />
      <div className="h-7 w-20 bg-slate-800 rounded mb-2" />
      <div className="h-3 w-36 bg-slate-900 rounded" />
    </div>
  );
};
