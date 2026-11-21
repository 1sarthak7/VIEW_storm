import React from 'react';
import { AlertCircle } from 'lucide-react';

interface ErrorBannerProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({
  title = 'Error',
  message,
  onRetry,
}) => {
  return (
    <div className="bg-rose-950/40 border border-rose-800/80 rounded-xl p-4 flex items-start gap-3 my-3">
      <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
      <div className="flex-1">
        <h4 className="text-sm font-semibold text-rose-300">{title}</h4>
        <p className="text-xs text-rose-200/80 mt-0.5 leading-relaxed">{message}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-3 py-1 bg-rose-900/60 hover:bg-rose-800 text-rose-200 text-xs font-medium rounded border border-rose-700 transition-colors"
        >
          Retry
        </button>
      )}
    </div>
  );
};
