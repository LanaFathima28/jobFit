'use client';

import React from 'react';
import { Award, Sparkles, Brain, CheckCircle2, ChevronRight, User, Trash2 } from 'lucide-react';
import { MatchLeaderboardItem } from '../lib/api';

interface MatchLeaderboardProps {
  matches: MatchLeaderboardItem[];
  onSelectCandidateForInterview: (candidateId: string) => void;
  onDeleteCandidate?: (candidateId: string) => void;
  isRanking: boolean;
}

export default function MatchLeaderboard({
  matches,
  onSelectCandidateForInterview,
  onDeleteCandidate,
  isRanking,
}: MatchLeaderboardProps) {
  if (isRanking) {
    return (
      <div className="py-16 text-center space-y-3 glass-panel rounded-2xl border border-slate-800">
        <Sparkles className="w-10 h-10 text-sky-400 animate-spin mx-auto" />
        <p className="text-sm font-semibold text-white">Computing Hybrid Vectors & Skill Scores...</p>
        <p className="text-xs text-slate-400">Comparing pgvector embeddings & AI match explanations</p>
      </div>
    );
  }

  if (!matches || matches.length === 0) {
    return (
      <div className="py-12 text-center glass-panel rounded-2xl border border-slate-800/80">
        <User className="w-10 h-10 text-slate-500 mx-auto mb-2" />
        <p className="text-sm font-medium text-slate-300">No candidate matches calculated yet.</p>
        <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
          Upload candidate resumes and click "Run AI Match Ranking" to generate real-time fit scores.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between px-1">
        <div className="flex items-center gap-2">
          <Award className="w-5 h-5 text-amber-400" />
          <h3 className="text-base font-semibold text-white">Ranked Candidate Fit Leaderboard</h3>
          <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-sky-500/10 text-sky-400 border border-sky-500/20">
            {matches.length} Candidates
          </span>
        </div>
      </div>

      <div className="space-y-3">
        {matches.map((item, index) => {
          const scoreColor =
            item.final_score >= 80
              ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
              : item.final_score >= 60
              ? 'text-sky-400 border-sky-500/30 bg-sky-500/10'
              : 'text-amber-400 border-amber-500/30 bg-amber-500/10';

          const progressBarColor =
            item.final_score >= 80
              ? 'bg-gradient-to-r from-emerald-500 to-teal-400'
              : item.final_score >= 60
              ? 'bg-gradient-to-r from-sky-500 to-indigo-500'
              : 'bg-gradient-to-r from-amber-500 to-orange-500';

          return (
            <div
              key={item.id || index}
              className="glass-card rounded-2xl p-5 border border-slate-800 transition-all hover:border-slate-700/80 space-y-4"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                
                {/* Rank & Name */}
                <div className="flex items-center gap-3">
                  <div
                    className={`w-9 h-9 rounded-xl flex items-center justify-center font-extrabold text-sm border ${
                      index === 0
                        ? 'bg-amber-500/20 text-amber-400 border-amber-500/40 shadow-lg shadow-amber-500/10'
                        : index === 1
                        ? 'bg-slate-300/20 text-slate-200 border-slate-300/30'
                        : index === 2
                        ? 'bg-amber-700/20 text-amber-500 border-amber-700/30'
                        : 'bg-slate-800 text-slate-400 border-slate-700'
                    }`}
                  >
                    #{index + 1}
                  </div>

                  <div>
                    <h4 className="text-base font-semibold text-white flex items-center gap-2">
                      {item.candidate_name}
                      <span className="text-xs font-normal text-slate-400">
                        &bull; {item.candidate_experience_years || 0} yrs exp
                      </span>
                    </h4>

                    {/* Skill tags */}
                    <div className="flex flex-wrap gap-1.5 mt-1.5">
                      {item.candidate_skills?.slice(0, 6).map((skill, sIdx) => (
                        <span
                          key={sIdx}
                          className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-800/80 text-slate-300 border border-slate-700/60"
                        >
                          {skill}
                        </span>
                      ))}
                      {(item.candidate_skills?.length || 0) > 6 && (
                        <span className="px-2 py-0.5 rounded text-[11px] text-slate-500 bg-slate-900">
                          +{item.candidate_skills.length - 6} more
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Score Pill & Breakdown */}
                <div className="flex items-center gap-4 self-start sm:self-center">
                  <div className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <span className="text-xs text-slate-400 font-medium">Hybrid Score</span>
                      <span className={`px-2.5 py-0.5 rounded-lg text-sm font-extrabold border ${scoreColor}`}>
                        {item.final_score}%
                      </span>
                    </div>
                    {/* Progress Bar */}
                    <div className="w-32 h-1.5 bg-slate-800 rounded-full mt-1.5 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${progressBarColor} transition-all duration-500`}
                        style={{ width: `${Math.min(100, Math.max(0, item.final_score))}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Breakdown metrics (Semantic vs Rule score) */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-3 border-t border-slate-800/70 text-xs">
                <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between">
                  <span className="text-slate-400 flex items-center gap-1.5">
                    <Brain className="w-3.5 h-3.5 text-purple-400" />
                    Semantic Alignment:
                  </span>
                  <span className="font-semibold text-purple-300">{item.semantic_score}%</span>
                </div>

                <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between">
                  <span className="text-slate-400 flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    Skill Rules Match:
                  </span>
                  <span className="font-semibold text-emerald-300">{item.rule_score}%</span>
                </div>

                <div className="col-span-2 sm:col-span-1 flex items-center justify-end gap-2">
                  <button
                    onClick={() => onSelectCandidateForInterview(item.candidate_id)}
                    className="w-full sm:w-auto flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-semibold text-white bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 rounded-xl shadow-md shadow-purple-500/10 transition-all"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    AI Interview Kit
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>

                  {onDeleteCandidate && (
                    <button
                      onClick={() => onDeleteCandidate(item.candidate_id)}
                      title="Delete Candidate"
                      className="p-2 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-xl transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>

              {/* AI Fit Summary */}
              {item.explanation && (
                <div className="p-3 rounded-xl bg-indigo-950/20 border border-indigo-500/10 text-xs text-slate-300 leading-relaxed">
                  <span className="font-bold text-indigo-400 block mb-0.5">AI Recommendation Summary:</span>
                  {item.explanation}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
