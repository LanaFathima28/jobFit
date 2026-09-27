'use client';

import React from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { fetchJobs, deleteJob, Job } from '@/lib/api';
import Navbar from '@/components/Navbar';
import { Briefcase, Plus, Sparkles, ArrowRight, Trash2, Users, FileText } from 'lucide-react';

export default function Home() {
  const { data: jobs = [], isLoading, isError, refetch } = useQuery({
    queryKey: ['jobs'],
    queryFn: fetchJobs,
  });

  const handleDeleteJob = async (e: React.MouseEvent, jobId: string) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this job posting?')) return;
    try {
      await deleteJob(jobId);
      refetch();
    } catch (err) {
      alert('Failed to delete job');
    }
  };

  return (
    <main className="min-h-screen pb-20">
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 space-y-10">
        
        {/* Landing Hero */}
        <div className="p-8 rounded-3xl bg-slate-900 border border-slate-800 space-y-6 relative overflow-hidden">
          <div className="max-w-2xl space-y-4 relative z-10">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-xs font-semibold">
              <Sparkles className="w-3.5 h-3.5" />
              AI Resume Ranking & Interview Kit Generator
            </div>

            <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight leading-tight">
              Rank candidates with vector similarity & generate tailored interview kits
            </h1>

            <p className="text-sm text-slate-400 leading-relaxed">
              JobFit AI combines pgvector semantic similarity with rule-based criteria (skills overlap, experience years, education level) to score candidates transparently and generate interview kits.
            </p>

            <div className="pt-2 flex items-center gap-4">
              <Link
                href="/jobs/new"
                className="flex items-center gap-2 px-5 py-3 text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl transition-all shadow-lg shadow-indigo-600/20"
              >
                <Plus className="w-4 h-4" />
                Post New Job Description
              </Link>
            </div>
          </div>
        </div>

        {/* Active Job Postings List */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <Briefcase className="w-5 h-5 text-indigo-400" />
                Job Descriptions ({jobs.length})
              </h2>
              <p className="text-xs text-slate-400">Select a position to view candidate rankings or process new resumes</p>
            </div>

            <Link
              href="/jobs/new"
              className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-indigo-400 hover:text-indigo-300 bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/20 rounded-xl transition-colors"
            >
              <Plus className="w-4 h-4" />
              New Job
            </Link>
          </div>

          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-44 bg-slate-900 border border-slate-800 rounded-2xl animate-pulse" />
              ))}
            </div>
          ) : isError ? (
            <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs text-center space-y-2">
              <p>Failed to load job postings from backend API.</p>
              <button onClick={() => refetch()} className="px-3 py-1.5 bg-rose-500/20 rounded-lg font-semibold">
                Retry Loading
              </button>
            </div>
          ) : jobs.length === 0 ? (
            <div className="p-12 text-center rounded-2xl bg-slate-900 border border-slate-800 space-y-3">
              <FileText className="w-10 h-10 text-slate-600 mx-auto" />
              <h3 className="text-base font-bold text-white">No Job Descriptions Created Yet</h3>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                Upload your first job description (file or text input) to start processing candidate resumes.
              </p>
              <Link
                href="/jobs/new"
                className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl"
              >
                <Plus className="w-4 h-4" />
                Post Your First Job
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {jobs.map((job) => (
                <Link
                  key={job.id}
                  href={`/jobs/${job.id}`}
                  className="p-5 rounded-2xl bg-slate-900 border border-slate-800 hover:border-indigo-500/50 transition-all space-y-4 group flex flex-col justify-between"
                >
                  <div className="space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-bold text-base text-white group-hover:text-indigo-400 transition-colors line-clamp-1">
                        {job.title}
                      </h3>
                      <button
                        onClick={(e) => handleDeleteJob(e, job.id)}
                        className="text-slate-500 hover:text-rose-400 p-1 rounded hover:bg-slate-800 transition-colors"
                        title="Delete Job"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>

                    <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                      {job.description_text || 'No description text specified.'}
                    </p>
                  </div>

                  {/* Criteria summary */}
                  <div className="pt-3 border-t border-slate-800/60 space-y-2 text-xs">
                    <div className="flex flex-wrap gap-1">
                      {job.structured_data?.required_skills?.slice(0, 4).map((sk, idx) => (
                        <span key={idx} className="px-2 py-0.5 rounded text-[11px] bg-slate-800 text-slate-300">
                          {sk}
                        </span>
                      ))}
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
                      <span>Min Exp: {job.structured_data?.min_experience_years || 0} yrs</span>
                      <span className="text-indigo-400 font-semibold flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">
                        View Job & Candidates <ArrowRight className="w-3 h-3" />
                      </span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}

        </div>

      </div>
    </main>
  );
}
