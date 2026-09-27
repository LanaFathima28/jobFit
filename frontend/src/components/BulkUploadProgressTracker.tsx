'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchTaskStatus, CandidateTaskItem } from '../lib/api';
import { FileText, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';

interface FileTaskRowProps {
  taskItem: CandidateTaskItem;
  onFinished?: () => void;
}

function FileTaskRow({ taskItem, onFinished }: FileTaskRowProps) {
  const { data: task, isError, error } = useQuery({
    queryKey: ['taskStatus', taskItem.task_id],
    queryFn: () => fetchTaskStatus(taskItem.task_id),
    refetchInterval: (query) => {
      const state = query.state.data?.status;
      if (state === 'success' || state === 'failed') return false;
      return 1500;
    },
  });

  const isCompleted = task?.status === 'success';
  const isFailed = task?.status === 'failed' || isError;

  return (
    <tr className="border-b border-slate-800/60 hover:bg-slate-800/30 text-xs">
      <td className="py-2.5 px-3 font-medium text-slate-200 flex items-center gap-2">
        <FileText className="w-4 h-4 text-sky-400 shrink-0" />
        <span className="truncate max-w-xs">{taskItem.original_filename}</span>
      </td>

      <td className="py-2.5 px-3 text-slate-400">
        {isCompleted ? (
          <span className="text-emerald-400 font-medium">Text Extracted & Embedded</span>
        ) : isFailed ? (
          <span className="text-rose-400 font-medium">Extraction Failed</span>
        ) : (
          <span>{task?.step || 'Queued'}</span>
        )}
      </td>

      <td className="py-2.5 px-3">
        <div className="w-24 bg-slate-800 rounded-full h-1.5 overflow-hidden">
          <div
            className={`h-full ${isCompleted ? 'bg-emerald-500' : isFailed ? 'bg-rose-500' : 'bg-sky-500'}`}
            style={{ width: `${task?.progress || 5}%` }}
          />
        </div>
      </td>

      <td className="py-2.5 px-3 text-right font-medium">
        {isCompleted ? (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3 h-3" /> Done
          </span>
        ) : isFailed ? (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <AlertCircle className="w-3 h-3" /> Failed
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/20">
            <Loader2 className="w-3 h-3 animate-spin" /> Processing
          </span>
        )}
      </td>
    </tr>
  );
}

interface BulkUploadProgressTrackerProps {
  candidateTasks: CandidateTaskItem[];
  onAllComplete?: () => void;
}

export default function BulkUploadProgressTracker({ candidateTasks }: BulkUploadProgressTrackerProps) {
  if (!candidateTasks || candidateTasks.length === 0) return null;

  return (
    <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-white">Batch Resume Ingestion ({candidateTasks.length} Files)</h4>
        <span className="text-xs text-slate-400">Processing background pipelines...</span>
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950">
        <table className="w-full text-left">
          <thead className="text-[11px] uppercase tracking-wider text-slate-400 bg-slate-900 border-b border-slate-800">
            <tr>
              <th className="py-2 px-3">Filename</th>
              <th className="py-2 px-3">Stage</th>
              <th className="py-2 px-3">Progress</th>
              <th className="py-2 px-3 text-right">Status</th>
            </tr>
          </thead>
          <tbody>
            {candidateTasks.map((t) => (
              <FileTaskRow key={t.task_id} taskItem={t} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
