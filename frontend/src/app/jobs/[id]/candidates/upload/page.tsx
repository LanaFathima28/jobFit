'use client';

import React, { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import Navbar from '@/components/Navbar';
import BulkUploadProgressTracker from '@/components/BulkUploadProgressTracker';
import { uploadAndProcessResumes, CandidateTaskItem } from '@/lib/api';
import { Upload, ArrowLeft, FileText, Loader2, Sparkles, CheckCircle2, AlertCircle } from 'lucide-react';

export default function BulkUploadCandidatesPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.id as string;

  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [candidateTasks, setCandidateTasks] = useState<CandidateTaskItem[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const filesArr = Array.from(e.target.files);
      setSelectedFiles((prev) => [...prev, ...filesArr]);
    }
  };

  const handleRemoveFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (selectedFiles.length === 0) {
      setErrorMessage('Please select at least one PDF or DOCX resume file.');
      return;
    }

    const formData = new FormData();
    selectedFiles.forEach((file) => {
      formData.append('files', file);
    });

    setIsUploading(true);
    try {
      const resp = await uploadAndProcessResumes(formData);
      setCandidateTasks(resp.candidate_tasks || []);
      setSelectedFiles([]);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to upload resume batch');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <main className="min-h-screen pb-20">
      <Navbar />

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 space-y-6">
        
        {/* Back navigation */}
        <Link
          href={`/jobs/${jobId}`}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Job Leaderboard
        </Link>

        {/* Upload Form Card */}
        <div className="p-6 sm:p-8 rounded-3xl bg-slate-900 border border-slate-800 space-y-6">
          <div>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <Upload className="w-5 h-5 text-sky-400" />
              Bulk Resume Upload & Automated Ingestion
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Select multiple candidate resumes (PDF, DOCX). Background Celery tasks will automatically extract text, parse structured profiles, and compute embeddings.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5 text-xs">
            {/* Drag & Drop Area */}
            <div className="border-2 border-dashed border-slate-800 hover:border-sky-500/50 rounded-2xl p-8 text-center bg-slate-950 transition-colors">
              <input
                type="file"
                id="resume-files"
                multiple
                accept=".pdf,.docx"
                onChange={handleFileChange}
                className="hidden"
              />
              <label htmlFor="resume-files" className="cursor-pointer space-y-3 block">
                <Upload className="w-8 h-8 text-sky-400 mx-auto" />
                <div>
                  <span className="font-bold text-slate-200 block text-sm">Click or Drag & Drop Multiple Resumes</span>
                  <span className="text-[11px] text-slate-400">Supported formats: PDF, DOCX (Max 5MB per file)</span>
                </div>
              </label>
            </div>

            {/* Selected File List */}
            {selectedFiles.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
                  <span>Selected Files ({selectedFiles.length})</span>
                  <button
                    type="button"
                    onClick={() => setSelectedFiles([])}
                    className="text-slate-500 hover:text-rose-400"
                  >
                    Clear All
                  </button>
                </div>

                <div className="max-h-48 overflow-y-auto space-y-1.5 p-2 rounded-xl bg-slate-950 border border-slate-800">
                  {selectedFiles.map((file, idx) => (
                    <div key={idx} className="flex items-center justify-between p-2 rounded-lg bg-slate-900 text-xs">
                      <div className="flex items-center gap-2 truncate">
                        <FileText className="w-4 h-4 text-sky-400 shrink-0" />
                        <span className="text-slate-200 font-medium truncate">{file.name}</span>
                        <span className="text-slate-500 text-[11px]">({(file.size / 1024).toFixed(1)} KB)</span>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRemoveFile(idx)}
                        className="text-slate-500 hover:text-rose-400 px-2"
                      >
                        &times;
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {errorMessage && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 font-mono">
                {errorMessage}
              </div>
            )}

            {/* Upload Button */}
            <div className="flex items-center justify-between pt-2">
              <Link
                href={`/jobs/${jobId}`}
                className="px-4 py-2.5 rounded-xl border border-slate-800 text-slate-300 hover:bg-slate-800 font-medium"
              >
                Cancel & Return
              </Link>

              <button
                type="submit"
                disabled={isUploading || selectedFiles.length === 0}
                className="flex items-center gap-2 px-6 py-2.5 text-xs font-bold text-white bg-sky-600 hover:bg-sky-500 disabled:opacity-40 rounded-xl transition-all shadow-lg shadow-sky-600/20"
              >
                {isUploading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Uploading Batch...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    Upload & Start Ingestion ({selectedFiles.length} Files)
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Real-time Task Progress Tracker for Uploaded Resumes */}
        {candidateTasks.length > 0 && (
          <div className="space-y-4">
            <BulkUploadProgressTracker candidateTasks={candidateTasks} />

            <div className="flex justify-end">
              <Link
                href={`/jobs/${jobId}`}
                className="flex items-center gap-2 px-5 py-2.5 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl shadow-lg shadow-indigo-600/20"
              >
                <CheckCircle2 className="w-4 h-4" />
                Return to Job Ranking Leaderboard
              </Link>
            </div>
          </div>
        )}

      </div>
    </main>
  );
}
