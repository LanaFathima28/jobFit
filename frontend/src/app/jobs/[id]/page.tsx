'use client';

import React, { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import Navbar from '@/components/Navbar';
import TaskProgressBanner from '@/components/TaskProgressBanner';
import ScoreBreakdownCard from '@/components/ScoreBreakdownCard';
import SkillBadges from '@/components/SkillBadges';
import CandidateFilterBar from '@/components/CandidateFilterBar';
import {
  fetchJob,
  fetchJobMatches,
  processJobPipeline,
  CandidateMatchResponse,
} from '@/lib/api';
import {
  Briefcase,
  Upload,
  Sparkles,
  ArrowLeft,
  Users,
  ChevronRight,
  RefreshCw,
  AlertCircle,
  FileText,
} from 'lucide-react';

export default function JobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.id as string;

  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  // Filters state
  const [minScore, setMinScore] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sortBy, setSortBy] = useState<'score' | 'name' | 'semantic'>('score');

  // Fetch job info
  const { data: job, isLoading: isLoadingJob, isError: isJobError } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => fetchJob(jobId),
    enabled: !!jobId,
  });

  // Fetch ranked candidate matches
  const {
    data: matches = [],
    isLoading: isLoadingMatches,
    isError: isMatchesError,
    refetch: refetchMatches,
  } = useQuery({
    queryKey: ['jobMatches', jobId],
    queryFn: () => fetchJobMatches(jobId, 100),
    enabled: !!jobId,
  });

  // Trigger full pipeline processing
  const handleProcessJob = async () => {
    setIsProcessing(true);
    try {
      const resp = await processJobPipeline(jobId);
      setActiveTaskId(resp.task_id);
    } catch (err: any) {
      alert(err.message || 'Failed to initiate job pipeline processing');
      setIsProcessing(false);
    }
  };

  const handlePipelineCompleted = () => {
    setIsProcessing(false);
    refetchMatches();
  };

  // Filter & sort matches
  const filteredMatches = matches
    .filter((m) => {
      if (m.final_score < minScore) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const nameMatch = m.name.toLowerCase().includes(q);
        const skillMatch =
          m.structured_data?.skills?.some((s: string) => s.toLowerCase().includes(q)) || false;
        return nameMatch || skillMatch;
      }
      return true;
    })
    .sort((a, b) => {
      if (sortBy === 'name') return a.name.localeCompare(b.name);
      if (sortBy === 'semantic') return (b.semantic_score || 0) - (a.semantic_score || 0);
      return b.final_score - a.final_score;
    });

  if (isLoadingJob) {
    return (
      <main className="min-h-screen">
        <Navbar />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-10 text-slate-400 text-xs text-center">
          Loading job description criteria...
        </div>
      </main>
    );
  }

  if (isJobError || !job) {
    return (
      <main className="min-h-screen">
        <Navbar />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-10 text-center space-y-3">
          <AlertCircle className="w-8 h-8 text-rose-400 mx-auto" />
          <h2 className="text-base font-bold text-white">Job Position Not Found</h2>
          <Link href="/" className="text-xs text-indigo-400 underline">
            Return to Dashboard
          </Link>
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
          href="/"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to All Jobs
        </Link>

        {/* Job Specs Header Card */}
        <div className="p-6 rounded-3xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <Briefcase className="w-5 h-5 text-indigo-400" />
                <h1 className="text-2xl font-black text-white tracking-tight">{job.title}</h1>
              </div>
              <p className="text-xs text-slate-400 mt-1 line-clamp-2">{job.description_text}</p>
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-3 shrink-0">
              <Link
                href={`/jobs/${jobId}/candidates/upload`}
                className="flex items-center gap-2 px-4 py-2.5 text-xs font-semibold text-sky-400 bg-sky-500/10 hover:bg-sky-500/20 border border-sky-500/20 rounded-xl transition-all"
              >
                <Upload className="w-4 h-4" />
                Upload Resumes
              </Link>

              <button
                onClick={handleProcessJob}
                disabled={isProcessing}
                className="flex items-center gap-2 px-5 py-2.5 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-xl shadow-lg shadow-indigo-600/20 transition-all"
              >
                <Sparkles className={`w-4 h-4 ${isProcessing ? 'animate-spin' : ''}`} />
                {isProcessing ? 'Initiating Pipeline...' : 'Run Pipeline & Ranking'}
              </button>
            </div>
          </div>

          {/* Job Requirements Badges */}
          <div className="pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-2 text-xs">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-slate-400 font-semibold mr-1">Required Skills:</span>
              {job.structured_data?.required_skills?.map((sk, idx) => (
                <span key={idx} className="px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                  {sk}
                </span>
              ))}
            </div>

            <div className="text-slate-400 font-medium">
              Min Experience: <strong className="text-slate-200">{job.structured_data?.min_experience_years || 0} years</strong>
            </div>
          </div>
        </div>

        {/* Polling Banner if Task Active */}
        {activeTaskId && (
          <TaskProgressBanner
            taskId={activeTaskId}
            title="Processing Job & Candidate Pipeline (Extraction -> Embedding -> Hybrid Scoring -> AI Explanations)"
            onSuccess={handlePipelineCompleted}
          />
        )}

        {/* Candidate Leaderboard Section */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Users className="w-5 h-5 text-indigo-400" />
              Ranked Candidate Leaderboard ({matches.length})
            </h2>

            <button
              onClick={() => refetchMatches()}
              className="flex items-center gap-1 text-xs text-slate-400 hover:text-white"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Refresh List
            </button>
          </div>

          {/* Filter Bar */}
          <CandidateFilterBar
            minScore={minScore}
            setMinScore={setMinScore}
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
            sortBy={sortBy}
            setSortBy={setSortBy}
            totalCount={matches.length}
            filteredCount={filteredMatches.length}
          />

          {/* Candidate List */}
          {isLoadingMatches ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-28 bg-slate-900 border border-slate-800 rounded-2xl animate-pulse" />
              ))}
            </div>
          ) : filteredMatches.length === 0 ? (
            <div className="p-12 text-center rounded-2xl bg-slate-900 border border-slate-800 space-y-3">
              <FileText className="w-8 h-8 text-slate-600 mx-auto" />
              <p className="text-sm font-bold text-white">No candidates match the specified filter threshold.</p>
              <p className="text-xs text-slate-400">
                {matches.length === 0
                  ? 'Upload resumes or run the matching pipeline to rank candidate profiles.'
                  : 'Try lowering the score threshold slider to view all candidates.'}
              </p>
              {matches.length === 0 && (
                <Link
                  href={`/jobs/${jobId}/candidates/upload`}
                  className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-indigo-600 rounded-xl"
                >
                  <Upload className="w-4 h-4" /> Bulk Upload Candidate Resumes
                </Link>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              {filteredMatches.map((cand, index) => {
                const matchedSkills = cand.score_breakdown?.breakdown?.skills?.matched_required_skills || [];
                const missingSkills = cand.score_breakdown?.breakdown?.skills?.missing_required_skills || [];

                return (
                  <Link
                    key={cand.id}
                    href={`/jobs/${jobId}/matches/${cand.id}`}
                    className="p-5 rounded-2xl bg-slate-900 border border-slate-800 hover:border-indigo-500/50 transition-all block group"
                  >
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                      
                      {/* Left: Rank badge & Candidate info */}
                      <div className="flex items-start gap-3.5">
                        <div className="w-8 h-8 rounded-xl bg-slate-800 text-slate-300 font-bold text-xs flex items-center justify-center shrink-0 border border-slate-700">
                          #{index + 1}
                        </div>

                        <div className="space-y-1.5">
                          <div className="flex items-center gap-2">
                            <h3 className="font-bold text-base text-white group-hover:text-indigo-400 transition-colors">
                              {cand.name}
                            </h3>
                            {cand.file_type && (
                              <span className="px-2 py-0.5 rounded text-[10px] uppercase font-mono bg-slate-800 text-slate-400">
                                {cand.file_type}
                              </span>
                            )}
                          </div>

                          {/* Skill badges */}
                          <SkillBadges
                            matchedSkills={matchedSkills}
                            missingSkills={missingSkills}
                            allSkills={cand.structured_data?.skills}
                            compact
                          />
                        </div>
                      </div>

                      {/* Right: Score breakdown & Arrow */}
                      <div className="flex items-center gap-4 self-end md:self-center shrink-0">
                        <ScoreBreakdownCard
                          finalScore={cand.final_score}
                          semanticScore={cand.semantic_score}
                          skillScore={cand.skill_overlap_score}
                          experienceScore={cand.experience_score}
                          educationScore={cand.education_score}
                          weightsUsed={cand.weights_used}
                          compact
                        />

                        <ChevronRight className="w-5 h-5 text-slate-500 group-hover:text-indigo-400 group-hover:translate-x-1 transition-all" />
                      </div>

                    </div>
                  </Link>
                );
              })}
            </div>
          )}

        </div>

      </div>
    </main>
  );
}
