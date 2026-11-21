import React from 'react';

export const PageSkeleton: React.FC = () => {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <div className="h-7 w-48 bg-[#1F2937] rounded-md" />
          <div className="h-4 w-72 bg-[#161F2E] rounded-md" />
        </div>
        <div className="h-9 w-32 bg-[#1F2937] rounded-lg" />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-28 bg-[#111827] rounded-xl border border-[#1F2937] p-5 space-y-3">
            <div className="h-4 w-24 bg-[#1F2937] rounded" />
            <div className="h-8 w-20 bg-[#1F2937] rounded" />
          </div>
        ))}
      </div>

      <div className="h-80 bg-[#111827] rounded-xl border border-[#1F2937] p-5">
        <div className="h-5 w-40 bg-[#1F2937] rounded mb-4" />
        <div className="h-60 bg-[#161F2E] rounded-lg" />
      </div>
    </div>
  );
};
