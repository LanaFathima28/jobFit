'use client';

import React from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { fetchHealthStatus } from '../lib/api';
import { Sparkles, Briefcase, Plus, AlertCircle, CheckCircle2 } from 'lucide-react';

export default function Navbar() {
  const { data: health, isError, isLoading } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealthStatus,
    refetchInterval: 15000,
  });

  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        
        {/* Brand */}
        <Link href="/" className="flex items-center gap-2 group">
          <div className="p-2 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 text-white shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <span className="font-bold text-lg text-white tracking-tight">JobFit<span className="text-sky-400">.AI</span></span>
            <span className="text-[10px] uppercase font-semibold text-slate-400 block -mt-1 tracking-wider">Recruiter MVP</span>
          </div>
        </Link>

        {/* Navigation & Actions */}
        <div className="flex items-center gap-4">
          {/* Health Badge */}
          <div className="hidden md:flex items-center gap-2 px-3 py-1 rounded-full bg-slate-800/80 border border-slate-700/60 text-xs">
            <span className="text-slate-400 font-medium">Backend:</span>
            {isLoading ? (
              <span className="text-slate-400 animate-pulse">Checking...</span>
            ) : isError ? (
              <span className="flex items-center gap-1 text-rose-400 font-medium">
                <AlertCircle className="w-3 h-3" /> Offline
              </span>
            ) : (
              <span className="flex items-center gap-1 text-emerald-400 font-medium">
                <CheckCircle2 className="w-3 h-3" /> Ready
              </span>
            )}
          </div>

          <Link
            href="/jobs/new"
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4" />
            New Job
          </Link>
        </div>

      </div>
    </header>
  );
}
