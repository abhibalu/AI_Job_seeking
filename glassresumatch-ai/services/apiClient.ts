/**
 * API Client for TailorAI Backend
 * Base configuration for all API calls
 */

const API_BASE_URL = 'http://localhost:8000';

interface ApiResponse<T> {
    data: T;
    error?: string;
}

class ApiClient {
    private baseUrl: string;

    constructor(baseUrl: string = API_BASE_URL) {
        this.baseUrl = baseUrl;
    }

    private async request<T>(
        endpoint: string,
        options: RequestInit = {}
    ): Promise<T> {
        const url = `${this.baseUrl}${endpoint}`;

        const headers = { ...options.headers } as Record<string, string>;

        // Set Content-Type to application/json only if not FormData and not already set
        if (!(options.body instanceof FormData) && !headers['Content-Type']) {
            headers['Content-Type'] = 'application/json';
        }

        const response = await fetch(url, {
            ...options,
            headers,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return response.json();
    }

    // Jobs endpoints
    async getJobs(skip: number = 0, limit: number = 20) {
        return this.request<Job[]>(`/api/jobs?skip=${skip}&limit=${limit}`);
    }

    async getJob(jobId: string) {
        return this.request<JobDetail>(`/api/jobs/${jobId}`);
    }

    async getJobStats() {
        return this.request<JobStats>(`/api/jobs/stats`);
    }

    // Evaluations endpoints
    async getEvaluations(skip: number = 0, limit: number = 20, action?: string) {
        let url = `/api/evaluations?skip=${skip}&limit=${limit}`;
        if (action) url += `&action=${action}`;
        return this.request<Evaluation[]>(url);
    }

    async getEvaluation(jobId: string) {
        return this.request<Evaluation>(`/api/evaluations/${jobId}`);
    }

    async evaluateJob(jobId: string, force: boolean = false) {
        return this.request<MessageResponse>(`/api/evaluations/${jobId}?force=${force}`, {
            method: 'POST',
        });
    }

    async getEvaluationStats() {
        return this.request<EvaluationStats>(`/api/evaluations/stats`);
    }

    async batchEvaluate(maxJobs: number, onlyUnevaluated: boolean, companyFilter?: string) {
        return this.request<MessageResponse>(`/api/evaluations/batch`, {
            method: 'POST',
            body: JSON.stringify({
                max_jobs: maxJobs,
                only_unevaluated: onlyUnevaluated,
                company_filter: companyFilter,
            }),
        });
    }

    // Parse endpoints
    async getParsedJD(jobId: string) {
        return this.request<ParseResult>(`/api/parse/${jobId}`);
    }

    async parseJD(jobId: string, force: boolean = false) {
        return this.request<MessageResponse>(`/api/parse/${jobId}?force=${force}`, {
            method: 'POST',
        });
    }

    // Tasks endpoints
    async getTaskStatus(taskId: string) {
        return this.request<TaskStatus>(`/api/tasks/${taskId}`);
    }

    // Resume endpoints
    async getMasterResume() {
        return this.request<any>('/api/resumes/master');
    }

    async uploadResume(file: File) {
        const formData = new FormData();
        formData.append('file', file);
        return this.request<any>('/api/resumes/upload', {
            method: 'POST',
            body: formData,
        });
    }

    async generatePdf(data: any, template: string) {
        const response = await fetch(`${this.baseUrl}/api/pdf/generate?template=${template}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        });

        if (!response.ok) {
            throw new Error(`PDF generation failed: ${response.statusText}`);
        }

        return response.blob();
    }
}

// Types matching backend schemas
export interface Job {
    id: string;
    title: string | null;
    company_name: string | null;
    location: string | null;
    posted_at: string | null;
    applicants_count: number | null;
}

export interface JobDetail extends Job {
    description_text: string | null;
    seniority_level: string | null;
    employment_type: string | null;
    link: string | null;
    company_website: string | null;
}

export interface JobStats {
    total_jobs: number;
    unique_companies: number;
    top_companies: Array<{ company_name: string; count: number }>;
}

export interface Gaps {
    technical: string[];
    domain: string[];
    soft_skills: string[];
}

export interface ImprovementSuggestions {
    resume_edits: Array<{
        area: string;
        suggestion: string;
        approved_reference: string;
    }>;
    interview_prep: string[];
}

export interface InterviewTips {
    high_priority_topics: Array<{
        topic: string;
        why: string;
        prep: string;
    }>;
    your_strengths_to_highlight: string[];
    questions_to_ask: string[];
}

export interface Evaluation {
    job_id: string;
    job_url: string | null;
    company_name: string | null;
    title_role: string | null;
    verdict: 'Strong Match' | 'Moderate Match' | 'Weak Match' | null;
    job_match_score: number | null;
    summary: string | null;
    required_exp: string | null;
    recommended_action: 'apply' | 'tailor' | 'skip' | null;
    gaps: Gaps | null;
    improvement_suggestions: ImprovementSuggestions | null;
    interview_tips: InterviewTips | null;
    jd_keywords: string[] | null;
    matched_keywords: string[] | null;
    missing_keywords: string[] | null;
    evaluated_at: string | null;
}

export interface EvaluationStats {
    total_evaluated: number;
    average_score: number;
    by_action: Record<string, number>;
    by_verdict: Record<string, number>;
}

export interface ParseResult {
    job_id: string;
    must_haves: string[] | null;
    nice_to_haves: string[] | null;
    domain: string | null;
    seniority: string | null;
    ats_keywords: string[] | null;
    normalized_skills: Record<string, unknown> | null;
    parsed_at: string | null;
}

export interface TaskStatus {
    task_id: string;
    status: 'queued' | 'running' | 'completed' | 'failed';
    progress: { completed: number; total: number } | null;
    created_at: string | null;
    completed_at: string | null;
    error: string | null;
}

export interface MessageResponse {
    message: string;
    job_id?: string;
    task_id?: string;
}

// Export singleton instance
export const apiClient = new ApiClient();
export default apiClient;
