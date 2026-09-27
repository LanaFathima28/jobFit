'use client';

import React from 'react';
import { Award, Brain, Code, Briefcase, GraduationCap } from 'lucide-react';

interface ScoreBreakdownCardProps {
  finalScore: number;
  semanticScore?: number;
  skillScore?: number;
  experienceScore?: number;
  educationScore?: number;
  weightsUsed?: Record<string, number>;
  compact?: boolean;
}

export default function ScoreBreakdownCard({
  finalScore,
  semanticScore = 0,
  skillScore = 0,
  experienceScore = 0,
  educationScore = 0,
  weightsUsed,
  compact = false,
}: ScoreBreakdownCardProps) {
  // Default weights from backend config if not provided
  const weights = {
    skills: weightsUsed?.skills_weight ?? 0.35,
    semantic: weightsUsed?.semantic_weight ?? 0.40,
    experience: weightsUsed?.experience_weight ?? 0.15,
    education: weightsUsed?.education_weight ?? 0.10,
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
    if (score >= 60) return 'text-sky-400 bg-sky-500/10 border-sky-500/20';
    if (score >= 40) return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
    return 'text-rose-400 bg-rose-500/10 border-rose-500/20';
  };

  const getBarColor = (score: number) => {
    if (score >= 80) return 'bg-emerald-500';
    if (score >= 60) return 'bg-sky-500';
    if (score >= 40) return 'bg-amber-500';
    return 'bg-rose-500';
  };

  if (compact) {
    return (
      <div className="flex items-center gap-2 text-xs">
        <span className={`font-bold px-2 py-0.5 rounded-md border ${getScoreColor(finalScore)}`}>
          {Math.round(finalScore)} pts
        </span>
        <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span title="Semantic Similarity">Sem: <strong className="text-slate-200">{Math.round(semanticScore)}%</strong></span>
          <span>&bull;</span>
          <span title="Skill Overlap">Skills: <strong className="text-slate-200">{Math.round(skillScore)}%</strong></span>
          <span>&bull;</span>
          <span title="Experience Match">Exp: <strong className="text-slate-200">{Math.round(experienceScore)}%</strong></span>
        </div>
      </div>
    );
  }

  const scoreItems = [
    {
      label: 'Semantic Similarity',
      score: semanticScore,
      weight: weights.semantic,
      icon: Brain,
      desc: 'Dense vector embedding match against job requirements',
    },
    {
      label: 'Skill Overlap',
      score: skillScore,
      weight: weights.skills,
      icon: Code,
      desc: 'Direct match ratio of required and preferred skills',
    },
    {
      label: 'Experience Match',
      score: experienceScore,
      weight: weights.experience,
      icon: Briefcase,
      desc: 'Candidate total years vs required minimum years',
    },
    {
      label: 'Education Match',
      score: educationScore,
      weight: weights.education,
      icon: GraduationCap,
      desc: 'Degree level alignment with required criteria',
    },
  ];

  return (
    <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Award className="w-5 h-5 text-indigo-400" />
            Hybrid Score Breakdown
          </h3>
          <p className="text-xs text-slate-400">Transparent multi-criteria weighted scoring breakdown</p>
        </div>

        <div className="text-right">
          <div className="text-2xl font-black text-white tracking-tight">
            {finalScore.toFixed(1)} <span className="text-sm font-medium text-slate-400">/ 100</span>
          </div>
          <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-md border ${getScoreColor(finalScore)} inline-block mt-0.5`}>
            Overall Match
          </span>
        </div>
      </div>

      {/* Sub-scores list */}
      <div className="space-y-4">
        {scoreItems.map((item, idx) => {
          const Icon = item.icon;
          return (
            <div key={idx} className="space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-200 flex items-center gap-1.5">
                  <Icon className="w-4 h-4 text-sky-400" />
                  {item.label}
                  <span className="text-[10px] font-mono text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded">
                    Weight: {(item.weight * 100).toFixed(0)}%
                  </span>
                </span>
                <span className="font-bold text-slate-100">{Math.round(item.score)} / 100</span>
              </div>

              <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${getBarColor(item.score)}`}
                  style={{ width: `${Math.min(100, Math.max(0, item.score))}%` }}
                />
              </div>

              <p className="text-[11px] text-slate-400">{item.desc}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
