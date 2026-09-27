'use client';

import React from 'react';
import { Filter, Search, SlidersHorizontal } from 'lucide-react';

interface CandidateFilterBarProps {
  minScore: number;
  setMinScore: (val: number) => void;
  searchQuery: string;
  setSearchQuery: (val: string) => void;
  sortBy: 'score' | 'name' | 'semantic';
  setSortBy: (val: 'score' | 'name' | 'semantic') => void;
  totalCount: number;
  filteredCount: number;
}

export default function CandidateFilterBar({
  minScore,
  setMinScore,
  searchQuery,
  setSearchQuery,
  sortBy,
  setSortBy,
  totalCount,
  filteredCount,
}: CandidateFilterBarProps) {
  return (
    <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3 md:space-y-0 md:flex md:items-center md:justify-between text-xs">
      
      {/* Search Input */}
      <div className="flex items-center gap-2 flex-1 max-w-xs">
        <div className="relative w-full">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search candidates by name or skill..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Threshold Slider & Sort Controls */}
      <div className="flex flex-wrap items-center gap-4">
        
        {/* Score Threshold Slider */}
        <div className="flex items-center gap-2 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800">
          <SlidersHorizontal className="w-3.5 h-3.5 text-sky-400" />
          <span className="text-slate-300 font-medium whitespace-nowrap">Min Score:</span>
          <input
            type="range"
            min="0"
            max="100"
            step="5"
            value={minScore}
            onChange={(e) => setMinScore(Number(e.target.value))}
            className="w-24 accent-indigo-500 cursor-pointer"
          />
          <span className="font-bold text-sky-400 w-8 text-right font-mono">{minScore}%</span>
        </div>

        {/* Sort selector */}
        <div className="flex items-center gap-2">
          <span className="text-slate-400">Sort by:</span>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="px-2.5 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 font-medium focus:outline-none focus:border-indigo-500"
          >
            <option value="score">Overall Score</option>
            <option value="semantic">Semantic Similarity</option>
            <option value="name">Candidate Name</option>
          </select>
        </div>

        {/* Count Summary */}
        <div className="text-slate-400 text-right">
          Showing <strong className="text-white font-mono">{filteredCount}</strong> / {totalCount} candidates
        </div>

      </div>

    </div>
  );
}
