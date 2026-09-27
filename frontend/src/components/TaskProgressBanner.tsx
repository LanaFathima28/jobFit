'use client';

import React, { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchTaskStatus, TaskStatusResponse } from '../lib/api';
import { Loader2, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';

interface TaskProgressBannerProps {
  taskId: string;
  title?: string;
  onSuccess?: (data: TaskStatusResponse) => void;
}

export default function TaskProgressBanner({ taskId, title = 'Pipeline Processing', onSuccess }: TaskProgressBannerProps) {
  const { data: task, isError, error, refetch } = useQuery({
    queryKey: ['taskStatus', taskId],
    queryFn: () => fetchTaskStatus(taskId),
    enabled: !!taskId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 1500;
      if (data.status === 'success' || data.status === 'failed') {
        return false;
      }
      return 1500;
    },
  });

  useEffect(() => {
    if (task?.status === 'success' && onSuccess) {
      onSuccess(task);
    }
  }, [task?.status]);

  if (!taskId) return null;

  const isCompleted = task?.status === 'success';
  const isFailed = task?.status === 'failed' || isError;
  const progress = task?.progress ?? 0;
  const stepLabel = task?.step || 'Initializing workflow...';

  return (
    <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 shadow-md space-y-3">
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-2 font-semibold">
          {isCompleted ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          ) : isFailed ? (
            <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
          ) : (
            <Loader2 className="w-5 h-5 text-sky-400 animate-spin shrink-0" />
          )}
          <span className="text-white">{title}</span>
        </div>

        <div className="flex items-center gap-3 text-xs text-slate-400">
          <span>Task ID: <code className="text-slate-300 font-mono">{taskId.slice(0, 8)}</code></span>
          <span className="font-semibold text-sky-400">{progress}%</span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${
            isCompleted
              ? 'bg-emerald-500'
              : isFailed
              ? 'bg-rose-500'
              : 'bg-gradient-to-r from-sky-500 to-indigo-500'
          }`}
          style={{ width: `${Math.min(100, Math.max(5, progress))}%` }}
        />
      </div>

      <div className="flex items-center justify-between text-xs text-slate-400">
        <span className="capitalize">{stepLabel}</span>

        {isFailed && (
          <button
            onClick={() => refetch()}
            className="flex items-center gap-1 text-slate-300 hover:text-white underline"
          >
            <RefreshCw className="w-3 h-3" /> Retry Check
          </button>
        )}
      </div>

      {isFailed && (
        <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs font-mono break-all">
          Error: {task?.error || (error as Error)?.message || 'Processing failed.'}
        </div>
      )}
    </div>
  );
}
