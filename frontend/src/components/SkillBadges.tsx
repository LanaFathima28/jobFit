'use client';

import React from 'react';
import { Check, X } from 'lucide-react';

interface SkillBadgesProps {
  matchedSkills?: string[];
  missingSkills?: string[];
  allSkills?: string[];
  compact?: boolean;
}

export default function SkillBadges({
  matchedSkills = [],
  missingSkills = [],
  allSkills = [],
  compact = false,
}: SkillBadgesProps) {
  if (compact) {
    const topMatched = matchedSkills.slice(0, 3);
    const topMissing = missingSkills.length > 0 ? missingSkills[0] : null;

    return (
      <div className="flex flex-wrap items-center gap-1.5 text-xs">
        {topMatched.map((sk, idx) => (
          <span
            key={idx}
            className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 flex items-center gap-1"
          >
            <Check className="w-3 h-3 text-emerald-400" />
            {sk}
          </span>
        ))}

        {topMissing && (
          <span className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-rose-500/10 text-rose-300 border border-rose-500/20 flex items-center gap-1">
            <X className="w-3 h-3 text-rose-400" />
            Missing: {topMissing}
          </span>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Matched Skills */}
      {matchedSkills.length > 0 && (
        <div className="space-y-1.5">
          <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider block">
            Matched Skills ({matchedSkills.length})
          </span>
          <div className="flex flex-wrap gap-1.5">
            {matchedSkills.map((sk, idx) => (
              <span
                key={idx}
                className="px-2.5 py-1 rounded-lg text-xs font-medium bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 flex items-center gap-1"
              >
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                {sk}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Missing Skills */}
      {missingSkills.length > 0 && (
        <div className="space-y-1.5">
          <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider block">
            Skill Gaps ({missingSkills.length})
          </span>
          <div className="flex flex-wrap gap-1.5">
            {missingSkills.map((sk, idx) => (
              <span
                key={idx}
                className="px-2.5 py-1 rounded-lg text-xs font-medium bg-rose-500/10 text-rose-300 border border-rose-500/20 flex items-center gap-1"
              >
                <X className="w-3.5 h-3.5 text-rose-400" />
                {sk}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* All Skills fallback if no match breakdown available */}
      {matchedSkills.length === 0 && missingSkills.length === 0 && allSkills.length > 0 && (
        <div className="space-y-1.5">
          <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider block">
            Extracted Skills ({allSkills.length})
          </span>
          <div className="flex flex-wrap gap-1.5">
            {allSkills.map((sk, idx) => (
              <span
                key={idx}
                className="px-2.5 py-1 rounded-lg text-xs font-medium bg-slate-800 text-slate-300 border border-slate-700"
              >
                {sk}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
