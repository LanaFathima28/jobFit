'use client';

import React from 'react';
import { CategorizedInterviewQuestions } from '../lib/api';
import { HelpCircle, Code, Users, Target, Sparkles, RefreshCw } from 'lucide-react';

interface InterviewQuestionsSectionProps {
  questions?: CategorizedInterviewQuestions;
  onRegenerate?: () => void;
  isGenerating?: boolean;
}

export default function InterviewQuestionsSection({
  questions,
  onRegenerate,
  isGenerating = false,
}: InterviewQuestionsSectionProps) {
  const technical = questions?.technical_questions || [];
  const behavioral = questions?.behavioral_questions || [];
  const gapProbing = questions?.gap_probing_questions || [];

  const totalQuestions = technical.length + behavioral.length + gapProbing.length;

  return (
    <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <HelpCircle className="w-5 h-5 text-indigo-400" />
            Tailored Interview Kit ({totalQuestions} Questions)
          </h3>
          <p className="text-xs text-slate-400">LLM-generated candidate-specific interview questions grounded in profile match</p>
        </div>

        {onRegenerate && (
          <button
            onClick={onRegenerate}
            disabled={isGenerating}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-sky-400 bg-sky-500/10 hover:bg-sky-500/20 border border-sky-500/20 rounded-xl transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isGenerating ? 'animate-spin' : ''}`} />
            {isGenerating ? 'Generating...' : 'Regenerate Kit'}
          </button>
        )}
      </div>

      {totalQuestions === 0 ? (
        <div className="text-center py-8 text-slate-400 text-xs space-y-2">
          <p>No interview questions generated yet for this candidate.</p>
          {onRegenerate && (
            <button
              onClick={onRegenerate}
              className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl"
            >
              Generate Interview Questions
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-6">
          {/* Technical Deep Dive Questions */}
          {technical.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-sky-400 uppercase tracking-wider flex items-center gap-1.5">
                <Code className="w-4 h-4" /> Technical & Architectural Deep-Dives
              </h4>
              <div className="space-y-2.5">
                {technical.map((q, idx) => (
                  <div key={idx} className="p-3.5 rounded-xl bg-slate-950 border border-slate-800/80 space-y-2 text-xs">
                    <p className="text-slate-100 font-medium leading-relaxed">&ldquo;{q.question}&rdquo;</p>
                    <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-400">
                      {q.target_skill && (
                        <span className="px-2 py-0.5 rounded bg-sky-500/10 text-sky-300 border border-sky-500/20 font-mono">
                          Target Skill: {q.target_skill}
                        </span>
                      )}
                      {q.context_reference && (
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                          Ref: {q.context_reference}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Gap Probing Questions */}
          {gapProbing.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
                <Target className="w-4 h-4" /> Gap Probing & Skill Verification
              </h4>
              <div className="space-y-2.5">
                {gapProbing.map((q, idx) => (
                  <div key={idx} className="p-3.5 rounded-xl bg-slate-950 border border-slate-800/80 space-y-2 text-xs">
                    <p className="text-slate-100 font-medium leading-relaxed">&ldquo;{q.question}&rdquo;</p>
                    <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-400">
                      {q.target_gap && (
                        <span className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20 font-mono">
                          Target Gap: {q.target_gap}
                        </span>
                      )}
                      {q.probing_strategy && (
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                          Strategy: {q.probing_strategy}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Behavioral & Trajectory Questions */}
          {behavioral.length > 0 && (
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                <Users className="w-4 h-4" /> Behavioral & Experience Trajectory
              </h4>
              <div className="space-y-2.5">
                {behavioral.map((q, idx) => (
                  <div key={idx} className="p-3.5 rounded-xl bg-slate-950 border border-slate-800/80 space-y-2 text-xs">
                    <p className="text-slate-100 font-medium leading-relaxed">&ldquo;{q.question}&rdquo;</p>
                    {q.focus_area && (
                      <div className="text-[11px] text-slate-400">
                        <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-mono">
                          Focus: {q.focus_area}
                        </span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
