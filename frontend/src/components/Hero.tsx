"use client";

import { Sparkles, ArrowRight, Zap, Database, Cpu, Search } from "lucide-react";

export default function Hero() {
  return (
    <section className="relative pt-32 pb-20 overflow-hidden">
      {/* Glow Effects */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-gradient-to-tr from-cyan-500/20 via-indigo-500/20 to-purple-500/20 blur-[120px] rounded-full pointer-events-none -z-10 animate-pulse-slow" />
      <div className="absolute top-20 right-10 w-72 h-72 bg-cyan-500/10 blur-[90px] rounded-full pointer-events-none -z-10" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative">
        {/* Top Tagline Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-cyan-950/60 border border-cyan-500/30 text-cyan-300 text-xs font-medium mb-8 shadow-inner shadow-cyan-500/10">
          <Zap className="w-3.5 h-3.5 text-cyan-400 animate-bounce" />
          <span>Next-Gen Talent Matching with PostgreSQL pgvector & LLMs</span>
        </div>

        {/* Main H1 Title */}
        <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight text-white max-w-4xl mx-auto leading-[1.15]">
          Rank Candidates & Generate <br />
          <span className="text-gradient">Interview Questions</span> in Seconds
        </h1>

        {/* Subtitle */}
        <p className="mt-6 text-lg sm:text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed font-light">
          Combine dense vector embeddings with rule-based scoring to evaluate candidate resumes against complex job descriptions and generate targeted technical interviews.
        </p>

        {/* CTA Actions */}
        <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
          <a
            href="#ranker"
            className="px-6 py-3.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-semibold text-sm shadow-lg shadow-cyan-500/25 transition-all flex items-center gap-2 group"
            id="hero-try-ranker-btn"
          >
            <Sparkles className="w-4 h-4 text-cyan-200 group-hover:rotate-12 transition-transform" />
            Try Resume Ranker
            <ArrowRight className="w-4 h-4 text-cyan-200 group-hover:translate-x-1 transition-transform" />
          </a>

          <a
            href="#architecture"
            className="px-6 py-3.5 rounded-xl bg-slate-900/90 border border-slate-800 hover:border-slate-700 text-slate-300 font-semibold text-sm transition-all flex items-center gap-2"
            id="hero-view-arch-btn"
          >
            <Database className="w-4 h-4 text-indigo-400" />
            Explore pgvector Pipeline
          </a>
        </div>

        {/* Feature Highlights Grid */}
        <div className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto text-left">
          <div className="glass-card p-4 rounded-xl">
            <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center mb-3">
              <Search className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="text-lg font-bold text-white">Hybrid Match</div>
            <div className="text-xs text-slate-400 mt-1">Vector embeddings + rigid experience rules</div>
          </div>

          <div className="glass-card p-4 rounded-xl">
            <div className="w-8 h-8 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center mb-3">
              <Cpu className="w-4 h-4 text-purple-400" />
            </div>
            <div className="text-lg font-bold text-white">LLM Insights</div>
            <div className="text-xs text-slate-400 mt-1">Claude & GPT automated gap analysis</div>
          </div>

          <div className="glass-card p-4 rounded-xl">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mb-3">
              <Database className="w-4 h-4 text-indigo-400" />
            </div>
            <div className="text-lg font-bold text-white">pgvector</div>
            <div className="text-xs text-slate-400 mt-1">1536-dim vector indexing in Postgres</div>
          </div>

          <div className="glass-card p-4 rounded-xl">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-3">
              <Zap className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-lg font-bold text-white">Celery Workers</div>
            <div className="text-xs text-slate-400 mt-1">Async queue for batch document ingestion</div>
          </div>
        </div>
      </div>
    </section>
  );
}
