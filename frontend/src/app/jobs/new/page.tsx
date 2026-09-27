'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Navbar from '@/components/Navbar';
import { uploadJob } from '@/lib/api';
import { Briefcase, Upload, FileText, ArrowLeft, Loader2, Sparkles } from 'lucide-react';
import Link from 'next/link';

export default function NewJobPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'text' | 'file'>('text');
  const [title, setTitle] = useState('');
  const [rawText, setRawText] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    const formData = new FormData();
    if (title.trim()) formData.append('title', title.trim());

    if (activeTab === 'text') {
      if (!rawText.trim()) {
        setErrorMessage('Please enter the job description text.');
        return;
      }
      formData.append('raw_text', rawText.trim());
    } else {
      if (!selectedFile) {
        setErrorMessage('Please select a job description file (PDF, DOCX, TXT).');
        return;
      }
      formData.append('file', selectedFile);
    }

    setIsSubmitting(true);
    try {
      const createdJob = await uploadJob(formData);
      router.push(`/jobs/${createdJob.id}`);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to create job posting');
      setIsSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen pb-20">
      <Navbar />

      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 space-y-6">
        
        {/* Back navigation */}
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Dashboard
        </Link>

        <div className="p-6 sm:p-8 rounded-3xl bg-slate-900 border border-slate-800 space-y-6">
          <div>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <Briefcase className="w-5 h-5 text-indigo-400" />
              Post New Job Description
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Upload a job spec document or paste text. Our backend will automatically parse criteria and skills.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6 text-xs">
            
            {/* Optional Title Input */}
            <div className="space-y-1.5">
              <label className="font-semibold text-slate-300 block">Job Title (Optional)</label>
              <input
                type="text"
                placeholder="e.g. Senior Backend Engineer"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white placeholder-slate-500 text-sm focus:outline-none focus:border-indigo-500"
              />
              <p className="text-[11px] text-slate-500">If left blank, title will be auto-generated from file stem or first line.</p>
            </div>

            {/* Input Type Selector Tabs */}
            <div className="flex rounded-xl bg-slate-950 p-1 border border-slate-800">
              <button
                type="button"
                onClick={() => setActiveTab('text')}
                className={`flex-1 py-2 rounded-lg font-semibold flex items-center justify-center gap-2 transition-all ${
                  activeTab === 'text'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <FileText className="w-4 h-4" />
                Paste Description Text
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('file')}
                className={`flex-1 py-2 rounded-lg font-semibold flex items-center justify-center gap-2 transition-all ${
                  activeTab === 'file'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Upload className="w-4 h-4" />
                Upload File (PDF/DOCX/TXT)
              </button>
            </div>

            {/* Tab 1: Paste Text */}
            {activeTab === 'text' ? (
              <div className="space-y-1.5">
                <label className="font-semibold text-slate-300 block">Job Description Text</label>
                <textarea
                  rows={10}
                  placeholder="Paste complete job description requirements, qualifications, and role responsibilities here..."
                  value={rawText}
                  onChange={(e) => setRawText(e.target.value)}
                  className="w-full p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 placeholder-slate-500 text-sm focus:outline-none focus:border-indigo-500 leading-relaxed font-mono"
                />
              </div>
            ) : (
              /* Tab 2: File Upload */
              <div className="space-y-2">
                <label className="font-semibold text-slate-300 block">Select Job Spec File</label>
                <div className="border-2 border-dashed border-slate-800 hover:border-indigo-500/50 rounded-2xl p-8 text-center bg-slate-950 transition-colors">
                  <input
                    type="file"
                    id="job-file"
                    accept=".pdf,.docx,.txt,.md"
                    onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                    className="hidden"
                  />
                  <label htmlFor="job-file" className="cursor-pointer space-y-3 block">
                    <Upload className="w-8 h-8 text-indigo-400 mx-auto" />
                    <div>
                      <span className="font-bold text-slate-200 block">Click to upload file</span>
                      <span className="text-[11px] text-slate-400">PDF, DOCX, or TXT up to 5MB</span>
                    </div>
                  </label>

                  {selectedFile && (
                    <div className="mt-4 p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 font-mono text-xs">
                      Selected: {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
                    </div>
                  )}
                </div>
              </div>
            )}

            {errorMessage && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 font-mono">
                {errorMessage}
              </div>
            )}

            {/* Submit button */}
            <div className="flex justify-end pt-2">
              <button
                type="submit"
                disabled={isSubmitting}
                className="flex items-center gap-2 px-6 py-3 text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-xl transition-all shadow-lg shadow-indigo-600/20"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Uploading & Parsing Job...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    Submit Job Description
                  </>
                )}
              </button>
            </div>

          </form>
        </div>

      </div>
    </main>
  );
}
