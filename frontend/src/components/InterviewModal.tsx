'use client';

import React from 'react';
import { X, Sparkles, Target, CheckCircle2, AlertTriangle, HelpCircle, Layers } from 'lucide-react';
import { InterviewKitResponse } from '../lib/api';

interface InterviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  data: InterviewKitResponse | null;
  isLoading: boolean;
}

export default function InterviewModal({ isOpen, onClose, data, isLoading }: InterviewModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-3xl glass-panel rounded-2xl p-6 shadow-2xl border border-slate-700/60 max-h-[85vh] overflow-y-auto">
        
        {/* Header */}
        <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-800 sticky top-0 bg-slate-950/90 backdrop-blur-md z-10 pt-1">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">AI Interview Assessment Kit</h3>
              <p className="text-xs text-slate-400">
                Tailored for <span className="text-sky-400 font-medium">{data?.candidate_name}</span> &bull; Position: <span className="text-purple-400 font-medium">{data?.job_title}</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {isLoading || !data ? (
          <div className="py-16 text-center space-y-3">
            <Sparkles className="w-10 h-10 text-purple-400 animate-spin mx-auto" />
            <p className="text-sm font-medium text-slate-300">Analyzing Candidate-Job Gaps & Generating Rubrics...</p>
            <p className="text-xs text-slate-500">Claude AI is preparing custom technical probes</p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Overview & Gaps */}
            <div className="grid md:grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
                <div className="flex items-center gap-2 text-xs font-semibold text-purple-400 mb-2 uppercase tracking-wider">
                  <Target className="w-4 h-4" />
                  Overall Executive Assessment
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {data?.interview_kit?.overall_assessment}
                </p>
              </div>

              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
                <div className="flex items-center gap-2 text-xs font-semibold text-amber-400 mb-2 uppercase tracking-wider">
                  <AlertTriangle className="w-4 h-4" />
                  Primary Skill Gaps to Probe
                </div>
                <div className="flex flex-wrap gap-1.5 mt-1">
                  {data?.interview_kit?.skill_gaps_to_probe?.map((gap, i) => (
                    <span
                      key={i}
                      className="px-2.5 py-1 rounded-md text-xs bg-amber-500/10 border border-amber-500/20 text-amber-300 font-medium"
                    >
                      {gap}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Questions List */}
            <div className="space-y-4">
              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                <Layers className="w-4 h-4 text-sky-400" />
                Tailored Interview Questions ({data?.interview_kit?.questions?.length || 0})
              </h4>

              {data?.interview_kit?.questions?.map((q, idx) => (
                <div key={idx} className="p-5 rounded-xl glass-card space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <span className="w-6 h-6 rounded-full bg-sky-500/20 text-sky-400 border border-sky-500/30 flex items-center justify-center text-xs font-bold shrink-0">
                        {idx + 1}
                      </span>
                      <span className="text-xs font-semibold text-sky-400 px-2 py-0.5 rounded bg-sky-500/10 border border-sky-500/20">
                        {q.category}
                      </span>
                    </div>
                  </div>

                  <p className="text-sm font-semibold text-white leading-snug">
                    "{q.question}"
                  </p>

                  <p className="text-xs text-slate-400 italic">
                    <span className="font-semibold not-italic text-slate-300">Purpose:</span> {q.purpose}
                  </p>

                  {/* Ideal Answer Points */}
                  <div className="pt-2 border-t border-slate-800/80">
                    <span className="text-xs font-medium text-emerald-400 flex items-center gap-1.5 mb-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Key Answer Points to Look For:
                    </span>
                    <ul className="list-disc list-inside text-xs text-slate-300 space-y-1 pl-1">
                      {q.ideal_answer_points?.map((pt, pIdx) => (
                        <li key={pIdx}>{pt}</li>
                      ))}
                    </ul>
                  </div>

                  {/* Rubric */}
                  {q.evaluation_rubric && (
                    <div className="mt-3 grid md:grid-cols-3 gap-2 pt-3 border-t border-slate-800/60 text-xs">
                      <div className="p-2.5 rounded-lg bg-emerald-950/30 border border-emerald-800/40">
                        <span className="font-bold text-emerald-400 block mb-0.5">Excellent (5/5)</span>
                        <p className="text-slate-300 text-[11px]">{q.evaluation_rubric.excellent}</p>
                      </div>
                      <div className="p-2.5 rounded-lg bg-slate-900/40 border border-slate-800">
                        <span className="font-bold text-sky-400 block mb-0.5">Acceptable (3/5)</span>
                        <p className="text-slate-300 text-[11px]">{q.evaluation_rubric.acceptable}</p>
                      </div>
                      <div className="p-2.5 rounded-lg bg-rose-950/30 border border-rose-800/40">
                        <span className="font-bold text-rose-400 block mb-0.5">Red Flags (1/5)</span>
                        <p className="text-slate-300 text-[11px]">{q.evaluation_rubric.red_flags}</p>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
