'use client';

import React, { useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import Navbar from '@/components/Navbar';
import ScoreBreakdownCard from '@/components/ScoreBreakdownCard';
import SkillBadges from '@/components/SkillBadges';
import InterviewQuestionsSection from '@/components/InterviewQuestionsSection';
import {
  fetchSingleMatch,
  fetchCandidate,
  fetchJobMatches,
  generateSingleMatchQuestions,
  generateSingleMatchExplanation,
  CandidateMatchResponse,
} from '@/lib/api';
import {
  ArrowLeft,
  User,
  Brain,
  FileText,
  AlertCircle,
  RefreshCw,
  Sparkles,
  CheckCircle2,
  XCircle,
  Award,
} from 'lucide-react';

export default function CandidateMatchDetailPage() {
  const params = useParams();
  const jobId = params.id as string;
  const matchId = params.matchId as string; // Could be Match UUID or Candidate UUID

  const [showRawTextModal, setShowRawTextModal] = useState(false);
  const [isGeneratingQuestions, setIsGeneratingQuestions] = useState(false);
  const [isGeneratingExplanation, setIsGeneratingExplanation] = useState(false);

  // Attempt to fetch via candidate match list first (contains all nested breakdown fields)
  const { data: matches = [], refetch: refetchJobMatches } = useQuery({
    queryKey: ['jobMatches', jobId],
    queryFn: () => fetchJobMatches(jobId, 100),
    enabled: !!jobId,
  });

  // Match item from job matches list if found (by candidate ID or match ID)
  const matchFromList = matches.find(
    (m) => m.id === matchId || (m as any).match_id === matchId
  );

  // Also query single match directly as fallback
  const {
    data: singleMatch,
    isLoading: isLoadingMatch,
    isError: isMatchError,
    refetch: refetchSingleMatch,
  } = useQuery({
    queryKey: ['singleMatch', matchId],
    queryFn: () => fetchSingleMatch(matchId),
    enabled: !!matchId && !matchFromList,
  });

  // Query candidate details for raw text if missing
  const candidateId = matchFromList?.id || singleMatch?.candidate_id;
  const { data: candidateInfo } = useQuery({
    queryKey: ['candidate', candidateId],
    queryFn: () => fetchCandidate(candidateId!),
    enabled: !!candidateId,
  });

  // Merge match response
  const finalScore = matchFromList?.final_score ?? singleMatch?.final_score ?? 0;
  const semanticScore = matchFromList?.semantic_score ?? singleMatch?.semantic_score ?? 0;
  const skillScore = matchFromList?.skill_overlap_score ?? singleMatch?.skill_overlap_score ?? 0;
  const experienceScore = matchFromList?.experience_score ?? singleMatch?.experience_score ?? 0;
  const educationScore = matchFromList?.education_score ?? singleMatch?.education_score ?? 0;
  const weightsUsed = matchFromList?.weights_used;

  const candidateName = matchFromList?.name || singleMatch?.candidate?.name || candidateInfo?.name || 'Candidate Profile';
  const rawText = matchFromList?.raw_text || singleMatch?.candidate?.raw_text || candidateInfo?.raw_text || '';
  const originalFilename = matchFromList?.original_filename || singleMatch?.candidate?.original_filename || 'resume.pdf';

  const scoreBreakdownObj = matchFromList?.score_breakdown?.breakdown;
  const matchedSkills = scoreBreakdownObj?.skills?.matched_required_skills || [];
  const missingSkills = scoreBreakdownObj?.skills?.missing_required_skills || [];
  const candidateSkills = candidateInfo?.structured_data?.skills || matchFromList?.structured_data?.skills || [];

  // Explanation object
  const explanationObj =
    matchFromList?.score_breakdown?.explanation_object ||
    (typeof matchFromList?.explanation === 'object' ? matchFromList?.explanation : null);
  const textExplanation = typeof matchFromList?.explanation === 'string' ? matchFromList.explanation : singleMatch?.explanation;

  // Interview questions
  const interviewQuestions = matchFromList?.interview_questions || singleMatch?.interview_questions;

  // Regenerate Questions
  const handleRegenerateQuestions = async () => {
    setIsGeneratingQuestions(true);
    try {
      if (singleMatch?.id) {
        await generateSingleMatchQuestions(singleMatch.id, true);
      } else if (matchFromList) {
        // If match ID not explicit, call job level questions or single match
        await generateSingleMatchQuestions(matchFromList.id, true);
      }
      refetchJobMatches();
      refetchSingleMatch();
    } catch (err: any) {
      alert(err.message || 'Failed to generate interview questions');
    } finally {
      setIsGeneratingQuestions(false);
    }
  };

  // Regenerate Explanation
  const handleRegenerateExplanation = async () => {
    setIsGeneratingExplanation(true);
    try {
      const targetMatchId = singleMatch?.id || matchFromList?.id;
      if (targetMatchId) {
        await generateSingleMatchExplanation(targetMatchId);
        refetchJobMatches();
        refetchSingleMatch();
      }
    } catch (err: any) {
      alert(err.message || 'Failed to generate explanation');
    } fontally: {
      setIsGeneratingExplanation(false);
    }
  };

  if (isLoadingMatch && !matchFromList) {
    return (
      <main className="min-h-screen">
        <Navbar />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-10 text-slate-400 text-xs text-center">
          Loading candidate match analysis...
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen pb-20">
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 space-y-6">
        
        {/* Navigation back */}
        <Link
          href={`/jobs/${jobId}`}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Job Leaderboard
        </Link>

        {/* Candidate Title Header */}
        <div className="p-6 rounded-3xl bg-slate-900 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="p-3 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <User className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-black text-white tracking-tight">{candidateName}</h1>
              <p className="text-xs text-slate-400 mt-0.5">
                Original file: <span className="font-mono text-slate-300">{originalFilename}</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowRawTextModal(true)}
              className="flex items-center gap-2 px-4 py-2 text-xs font-semibold text-sky-400 bg-sky-500/10 hover:bg-sky-500/20 border border-sky-500/20 rounded-xl transition-all"
            >
              <FileText className="w-4 h-4" /> View Extracted Resume Text
            </button>
          </div>
        </div>

        {/* Top Grid: Full Score Breakdown vs AI Match Explanation */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* 1. Score Breakdown Card */}
          <ScoreBreakdownCard
            finalScore={finalScore}
            semanticScore={semanticScore}
            skillScore={skillScore}
            experienceScore={experienceScore}
            educationScore={educationScore}
            weightsUsed={weightsUsed}
          />

          {/* 2. LLM Match Explanation Card */}
          <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4 flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Brain className="w-5 h-5 text-indigo-400" />
                  AI Candidate Match Explanation
                </h3>
                {handleRegenerateExplanation && (
                  <button
                    onClick={handleRegenerateExplanation}
                    disabled={isGeneratingExplanation}
                    className="flex items-center gap-1 text-[11px] text-sky-400 hover:underline"
                  >
                    <RefreshCw className={`w-3 h-3 ${isGeneratingExplanation ? 'animate-spin' : ''}`} />
                    Regenerate
                  </button>
                )}
              </div>

              {explanationObj ? (
                <div className="space-y-4 text-xs">
                  {/* Summary / Verdict */}
                  {explanationObj.summary && (
                    <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 leading-relaxed">
                      <span className="font-bold text-indigo-400 block mb-1">Executive Summary:</span>
                      {explanationObj.summary}
                    </div>
                  )}

                  {/* Key Strengths */}
                  {explanationObj.key_strengths && explanationObj.key_strengths.length > 0 && (
                    <div className="space-y-1.5">
                      <span className="font-semibold text-emerald-400 uppercase tracking-wider text-[11px] flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Key Strengths
                      </span>
                      <ul className="space-y-1 list-disc list-inside text-slate-300">
                        {explanationObj.key_strengths.map((str: string, sIdx: number) => (
                          <li key={sIdx}>{str}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Potential Gaps */}
                  {explanationObj.potential_gaps && explanationObj.potential_gaps.length > 0 && (
                    <div className="space-y-1.5">
                      <span className="font-semibold text-rose-400 uppercase tracking-wider text-[11px] flex items-center gap-1">
                        <XCircle className="w-3.5 h-3.5" /> Identified Gaps
                      </span>
                      <ul className="space-y-1 list-disc list-inside text-slate-300">
                        {explanationObj.potential_gaps.map((gap: string, gIdx: number) => (
                          <li key={gIdx}>{gap}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : textExplanation ? (
                <p className="text-xs text-slate-300 leading-relaxed p-3 rounded-xl bg-slate-950 border border-slate-800">
                  {textExplanation}
                </p>
              ) : (
                <div className="text-center py-6 text-slate-400 text-xs space-y-2">
                  <p>No LLM explanation generated yet.</p>
                  <button
                    onClick={handleRegenerateExplanation}
                    disabled={isGeneratingExplanation}
                    className="px-3 py-1.5 bg-indigo-600 text-white rounded-lg font-semibold"
                  >
                    Generate AI Explanation
                  </button>
                </div>
              )}
            </div>

            {/* Skill Breakdown Badges */}
            <div className="pt-3 border-t border-slate-800">
              <SkillBadges
                matchedSkills={matchedSkills}
                missingSkills={missingSkills}
                allSkills={candidateSkills}
              />
            </div>
          </div>

        </div>

        {/* Categorized Interview Kit Section */}
        <InterviewQuestionsSection
          questions={interviewQuestions}
          onRegenerate={handleRegenerateQuestions}
          isGenerating={isGeneratingQuestions}
        />

      </div>

      {/* Raw Text Modal */}
      {showRawTextModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-3xl max-h-[85vh] rounded-3xl bg-slate-900 border border-slate-800 p-6 flex flex-col space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <FileText className="w-5 h-5 text-sky-400" />
                Raw Extracted Resume Text — {candidateName}
              </h3>
              <button
                onClick={() => setShowRawTextModal(false)}
                className="text-slate-400 hover:text-white font-bold px-2 py-1"
              >
                &times;
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 rounded-xl bg-slate-950 border border-slate-800 font-mono text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
              {rawText || 'No raw text available for this candidate.'}
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setShowRawTextModal(false)}
                className="px-4 py-2 text-xs font-semibold text-white bg-slate-800 hover:bg-slate-700 rounded-xl"
              >
                Close View
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
