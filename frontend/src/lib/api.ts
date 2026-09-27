const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface HealthStatus {
  status: string;
  version?: string;
  timestamp?: string;
}

export interface Job {
  id: string;
  title: string;
  description_text?: string;
  structured_data?: {
    job_title?: string;
    required_skills?: string[];
    preferred_skills?: string[];
    min_experience_years?: number;
    required_education?: string;
    summary?: string;
  };
  original_filename?: string;
  file_type?: string;
  file_path?: string;
  file_size?: number;
  extraction_status?: string;
  extraction_error?: string;
  structured_extraction_status?: string;
  created_at: string;
}

export interface Candidate {
  id: string;
  name: string;
  raw_text?: string;
  structured_data?: {
    full_name?: string;
    skills?: string[];
    total_years_experience?: number;
    work_history?: any[];
    education?: any[];
    summary?: string;
  };
  original_filename?: string;
  file_type?: string;
  file_path?: string;
  file_size?: number;
  extraction_status?: string;
  structured_extraction_status?: string;
  created_at: string;
}

export interface TechnicalQuestion {
  question: string;
  target_skill?: string;
  context_reference?: string;
}

export interface BehavioralQuestion {
  question: string;
  focus_area?: string;
}

export interface GapProbingQuestion {
  question: string;
  target_gap?: string;
  probing_strategy?: string;
}

export interface CategorizedInterviewQuestions {
  technical_questions?: TechnicalQuestion[];
  behavioral_questions?: BehavioralQuestion[];
  gap_probing_questions?: GapProbingQuestion[];
}

export interface MatchExplanationObject {
  summary?: string;
  key_strengths?: string[];
  potential_gaps?: string[];
  verdict?: string;
}

export interface ScoreBreakdown {
  skills?: {
    candidate_skills?: string[];
    required_skills?: string[];
    matched_required_skills?: string[];
    missing_required_skills?: string[];
    skill_overlap_ratio?: number;
  };
  experience?: {
    candidate_years?: number;
    required_years?: number;
    delta?: number;
    status?: string;
  };
  education?: {
    candidate_degree?: string;
    required_degree?: string;
    status?: string;
  };
}

export interface CandidateMatchResponse {
  id: string; // Candidate UUID
  name: string;
  final_score: number;
  similarity_score: number;
  semantic_score?: number;
  skill_overlap_score?: number;
  experience_score?: number;
  education_score?: number;
  weights_used?: Record<string, number>;
  score_breakdown?: {
    semantic_score?: number;
    rule_score?: number;
    skill_overlap_score?: number;
    experience_score?: number;
    education_score?: number;
    final_score?: number;
    weights_used?: Record<string, number>;
    breakdown?: ScoreBreakdown;
    explanation_object?: MatchExplanationObject;
  };
  explanation?: any; // object or string
  interview_questions?: CategorizedInterviewQuestions;
  raw_text?: string;
  structured_data?: any;
  original_filename?: string;
  file_type?: string;
  extraction_status?: string;
  created_at: string;
}

export interface SingleMatchResponse {
  id: string; // Match UUID
  candidate_id: string;
  job_id: string;
  semantic_score?: number;
  rule_score?: number;
  skill_overlap_score?: number;
  experience_score?: number;
  education_score?: number;
  final_score?: number;
  score_breakdown?: any;
  explanation?: string;
  interview_questions?: CategorizedInterviewQuestions;
  created_at: string;
  candidate?: Candidate;
}

export interface TaskStatusResponse {
  task_id: string;
  status: 'pending' | 'processing' | 'success' | 'failed' | string;
  step?: string;
  progress: number;
  details?: any;
  result?: any;
  error?: string;
}

export interface MatchLeaderboardItem {
  id: string;
  candidate_id: string;
  candidate_name: string;
  candidate_skills: string[];
  candidate_experience_years: number;
  job_id: string;
  semantic_score: number;
  rule_score: number;
  final_score: number;
  explanation?: string;
  created_at: string;
}

export interface InterviewKitResponse {
  candidate_id: string;
  candidate_name: string;
  job_id: string;
  job_title: string;
  interview_kit?: {
    overall_assessment?: string;
    skill_gaps_to_probe?: string[];
    questions?: Array<{
      id: number;
      category: string;
      question: string;
      purpose?: string;
      ideal_answer_points?: string[];
      evaluation_rubric?: {
        excellent?: string;
        acceptable?: string;
        red_flags?: string;
      };
    }>;
  };
}

export async function rankCandidatesForJob(jobId: string): Promise<MatchLeaderboardItem[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/matches/rank`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_id: jobId }),
  });
  if (!res.ok) throw new Error('Failed to rank candidates');
  return res.json();
}

export async function fetchJobLeaderboard(jobId: string): Promise<MatchLeaderboardItem[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/matches/job/${jobId}`);
  if (!res.ok) throw new Error('Failed to fetch match leaderboard');
  return res.json();
}

export async function generateInterviewKit(candidateId: string, jobId: string): Promise<InterviewKitResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/interviews/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ candidate_id: candidateId, job_id: jobId }),
  });
  if (!res.ok) throw new Error('Failed to generate interview kit');
  return res.json();
}

export interface CandidateTaskItem {
  candidate_id: string;
  original_filename: string;
  task_id: string;
}

export interface BulkUploadProcessResponse {
  message: string;
  candidate_tasks: CandidateTaskItem[];
}

export interface JobProcessResponse {
  task_id: string;
  job_id: string;
  status: string;
  message: string;
}

// API Methods

export async function fetchHealthStatus(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE_URL}/health`);
  if (!res.ok) throw new Error('Health endpoint unavailable');
  return res.json();
}

export async function createJob(data: {
  title: string;
  description_text: string;
  skills: string[];
  min_experience_years: number;
}): Promise<Job> {
  const res = await fetch(`${API_BASE_URL}/api/v1/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to create job posting');
  }
  return res.json();
}

export async function uploadJob(formData: FormData): Promise<Job> {
  const res = await fetch(`${API_BASE_URL}/api/v1/jobs/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to upload job description');
  }
  return res.json();
}

export async function fetchJobs(): Promise<Job[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/jobs`);
  if (!res.ok) throw new Error('Failed to fetch jobs');
  return res.json();
}

export async function fetchJob(jobId: string): Promise<Job> {
  const res = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}`);
  if (!res.ok) throw new Error('Failed to fetch job details');
  return res.json();
}

export async function deleteJob(jobId: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete job');
}

export async function processJobPipeline(
  jobId: string,
  topNExplain: number = 10,
  topNQuestions: number = 5
): Promise<JobProcessResponse> {
  const params = new URLSearchParams({
    top_n_explain: topNExplain.toString(),
    top_n_questions: topNQuestions.toString(),
  });
  const res = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}/process?${params.toString()}`, {
    method: 'POST',
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to initiate job pipeline processing');
  }
  return res.json();
}

export async function uploadCandidateResume(file: File): Promise<Candidate> {
  const formData = new FormData();
  formData.append('files', file);

  const res = await fetch(`${API_BASE_URL}/api/v1/candidates/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to upload resume');
  }

  const list = await res.json();
  return Array.isArray(list) ? list[0] : list;
}

export async function uploadAndProcessResumes(formData: FormData): Promise<BulkUploadProcessResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/candidates/upload-and-process`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to upload and process candidate resumes');
  }
  return res.json();
}

export async function fetchTaskStatus(taskId: string): Promise<TaskStatusResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/tasks/${taskId}/status`);
  if (!res.ok) throw new Error(`Failed to fetch status for task ${taskId}`);
  return res.json();
}

export async function fetchJobMatches(jobId: string, topN: number = 50): Promise<CandidateMatchResponse[]> {
  const res = await fetch(`${API_BASE_URL}/api/v1/jobs/${jobId}/matches?top_n=${topN}`);
  if (!res.ok) throw new Error('Failed to fetch ranked candidate matches');
  return res.json();
}

export async function fetchSingleMatch(matchId: string): Promise<SingleMatchResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/matches/${matchId}`);
  if (!res.ok) throw new Error('Failed to fetch match record');
  return res.json();
}

export async function fetchCandidate(candidateId: string): Promise<Candidate> {
  const res = await fetch(`${API_BASE_URL}/api/v1/candidates/${candidateId}`);
  if (!res.ok) throw new Error('Failed to fetch candidate details');
  return res.json();
}

export async function generateSingleMatchQuestions(matchId: string, regenerate: boolean = false): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/v1/matches/${matchId}/generate-questions?regenerate=${regenerate}`, {
    method: 'POST',
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to generate interview questions');
  }
  return res.json();
}

export async function generateSingleMatchExplanation(matchId: string): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/v1/matches/${matchId}/explain`, {
    method: 'POST',
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to generate explanation');
  }
  return res.json();
}
