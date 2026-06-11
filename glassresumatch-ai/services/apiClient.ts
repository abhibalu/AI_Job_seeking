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

        if (response.status === 204) {
            return {} as T;
        }

        return response.json();
    }

    // Jobs endpoints
    async getJobs(skip: number = 0, limit: number = 20, company?: string, is_evaluated?: boolean) {
        let url = `/api/jobs?skip=${skip}&limit=${limit}`;
        if (company) url += `&company=${encodeURIComponent(company)}`;
        if (is_evaluated !== undefined) url += `&is_evaluated=${is_evaluated}`;
        return this.request<Job[]>(url);
    }

    async getAllJobIds(company?: string) {
        let url = `/api/jobs?skip=0&limit=10000`; // Fetch all (up to 10k)
        if (company) url += `&company=${encodeURIComponent(company)}`;
        const jobs = await this.request<Job[]>(url);
        return jobs.map(j => j.id);
    }

    async getJob(jobId: string) {
        return this.request<JobDetail>(`/api/jobs/${jobId}`);
    }

    async getJobStats(company?: string, is_evaluated?: boolean) {
        let url = `/api/jobs/stats`;
        const params = new URLSearchParams();
        if (company) params.append('company', company);
        if (is_evaluated !== undefined) params.append('is_evaluated', String(is_evaluated));

        if (params.toString()) {
            url += `?${params.toString()}`;
        }
        return this.request<JobStats>(url);
    }

    async importJob(url: string) {
        return this.request<{
            id: string; // First job ID (backwards compat)
            status: string;
            count?: number;
            first_job?: { id: string; title: string; company: string };
            ids?: string[];
        }>(`/api/jobs/import`, {
            method: 'POST',
            body: JSON.stringify({ url })
        });
    }

    // Evaluations endpoints
    async getEvaluations(skip: number = 0, limit: number = 20, action?: string, verdict?: string, search?: string) {
        let url = `/api/evaluations?skip=${skip}&limit=${limit}`;
        if (action) url += `&action=${action}`;
        if (verdict) url += `&verdict=${verdict}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;

        // Manual fetch to access headers
        const response = await fetch(`${this.baseUrl}${url}`, {
            headers: { 'Content-Type': 'application/json' }
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        const data = await response.json();
        const total = parseInt(response.headers.get('X-Total-Count') || '0', 10);
        return { data: data as Evaluation[], total };
    }

    async getEvaluation(jobId: string) {
        return this.request<Evaluation>(`/api/evaluations/${jobId}`);
    }

    async deleteJobs(ids: string[]): Promise<void> {
        return this.request<void>(`/api/jobs`, {
            method: 'DELETE',
            body: JSON.stringify({ ids }),
        });
    }

    async evaluateJob(jobId: string, force: boolean = false) {
        return this.request<MessageResponse>(`/api/evaluations/${jobId}?force=${force}`, {
            method: 'POST',
        });
    }

    async evaluateJobAsync(jobId: string, force: boolean = true): Promise<{ task_id: string; message: string; job_id: string }> {
        return this.request<{ task_id: string; message: string; job_id: string }>(`/api/evaluations/${jobId}/async?force=${force}`, {
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

    async updateMasterResume(data: any) {
        return this.request<any>('/api/resumes/master', {
            method: 'POST',
            body: JSON.stringify(data),
        });
    }

    async importFromGoogleDoc(documentId: string) {
        return this.request<{ status: string; message: string }>('/api/resumes/import-gdoc', {
            method: 'POST',
            body: JSON.stringify({ document_id: documentId }),
        });
    }

    // Tailored Resume endpoints
    async tailorResume(jobId: string): Promise<{ task_id: string; message: string }> {
        return this.request<{ task_id: string; message: string }>(`/api/resumes/tailor/${jobId}`, {
            method: 'POST',
        });
    }

    async getTailoredVersions(jobId: string) {
        return this.request<TailoredResume[]>(`/api/resumes/tailored/${jobId}`);
    }

    async getResumeById(resumeId: string) {
        return this.request<TailoredResume>(`/api/resumes/tailored/record/${resumeId}`);
    }

    async exportToGoogleDocs(jobId: string) {
        return this.request<{
            status: 'success' | 'partial' | 'failed' | 'no_changes';
            url: string;
            path: 'copy_and_fill' | 'plain_text';
            summary?: { total: number; applied: number; skipped: number };
            skipped_fields?: { section: string; reason: string }[];
        }>(`/api/resumes/export-gdoc/${jobId}`, {
            method: 'POST',
        });
    }

    async updateTailoredStatus(recordId: string, status: string) {
        return this.request<any>(`/api/resumes/tailored/${recordId}/status?status=${status}`, {
            method: 'POST',
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

    // OotoCV: Resume change review (ADR-0010)
    async getResumeChanges(resumeId: string) {
        return this.request<ResumeChange[]>(`/api/resumes/${resumeId}/changes`);
    }

    async applyChangeAction(resumeId: string, changeId: string, action: 'accept' | 'reject' | 'keep_original') {
        return this.request<{ ok: boolean }>(`/api/resumes/${resumeId}/changes/${changeId}`, {
            method: 'PATCH',
            body: JSON.stringify({ action }),
        });
    }

    async applyBulkChangeAction(resumeId: string, action: 'accept' | 'reject' | 'keep_original', scope: 'remaining' | 'all' = 'remaining') {
        return this.request<{ updated: number }>(`/api/resumes/${resumeId}/changes/bulk`, {
            method: 'PATCH',
            body: JSON.stringify({ action, scope }),
        });
    }

    // OotoCV: Job apply action — records cv_version chosen and opens job URL
    async patchJobAction(jobId: string, cvVersion: 'base' | 'tailored') {
        return this.request<{ ok: boolean }>(`/api/jobs/${jobId}/action`, {
            method: 'PATCH',
            body: JSON.stringify({ cv_version: cvVersion }),
        });
    }

    // OotoCV: Cover letter (ADR-0011)
    async updateCoverLetter(resumeId: string, coverLetter: string) {
        return this.request<{ ok: boolean }>(`/api/resumes/${resumeId}/cover_letter`, {
            method: 'PATCH',
            body: JSON.stringify({ cover_letter: coverLetter }),
        });
    }

    // OotoCV: Application tracker (phase 5)
    async getApplications() {
        return this.request<Application[]>('/api/applications');
    }

    async createApplication(
        jobId: string,
        cvVersion: 'base' | 'tailored',
        opts?: { jobTitle?: string; companyName?: string; resumeId?: string }
    ) {
        return this.request<Application>('/api/applications', {
            method: 'POST',
            body: JSON.stringify({
                job_id: jobId,
                cv_version: cvVersion,
                job_title: opts?.jobTitle,
                company_name: opts?.companyName,
                resume_id: opts?.resumeId,
            }),
        });
    }

    async updateApplicationStatus(applicationId: string, status: Application['status']) {
        return this.request<Application>(`/api/applications/${applicationId}/status`, {
            method: 'PATCH',
            body: JSON.stringify({ status }),
        });
    }

    async cancelTask(taskId: string): Promise<{ status: string }> {
        return this.request<{ status: string }>(`/api/tasks/${taskId}/cancel`, {
            method: 'POST',
        });
    }

    // Service kill switches
    async getServiceToggles(): Promise<ServiceToggles> {
        return this.request<ServiceToggles>('/api/settings/services');
    }

    async updateServiceToggle(service: string, enabled: boolean): Promise<ServiceToggles> {
        return this.request<ServiceToggles>('/api/settings/services', {
            method: 'PATCH',
            body: JSON.stringify({ [service]: enabled }),
        });
    }

    // Scheduler status
    async getSchedulerStatus() {
        return this.request<SchedulerStatus>('/api/scheduler');
    }

    // ─────────────────────────────────────────────────────────────
    // OotoCV phase 6 — runs, pipeline config, system status, roast,
    // change feedback (ADRs 0023–0025)
    // ─────────────────────────────────────────────────────────────

    /** Recent runs with per-verdict aggregated counts. */
    async getRuns(limit: number = 50) {
        return this.request<Run[]>(`/api/runs?limit=${limit}`);
    }

    /** Single pipeline_runs row by id. */
    async getRun(runId: string) {
        return this.request<{
            id: string;
            run_type: string;
            status: string;
            started_at: string;
            finished_at: string | null;
            jobs_found: number;
            jobs_processed: number;
            jobs_skipped: number;
            error_detail: string | null;
            metadata: Record<string, unknown> | null;
        }>(`/api/runs/${runId}`);
    }

    /** Per-stage pipeline mode (auto/manual) + auto_send_threshold. */
    async getPipelineConfig() {
        return this.request<PipelineConfig>('/api/pipeline/config');
    }

    /** Partial update; pass only the keys you want to change. */
    async updatePipelineConfig(update: Partial<PipelineConfig>) {
        return this.request<PipelineConfig>('/api/pipeline/config', {
            method: 'PATCH',
            body: JSON.stringify(update),
        });
    }

    /** Cron sidebar pulse feed (cron_state + next_run_at + last_error). */
    async getSystemStatus() {
        return this.request<SystemStatus>('/api/system/status');
    }

    /**
     * Record a reject feedback chip on a change and trigger regeneration.
     * Backend caps regeneration_count at 2 (R8); returns 409 at the cap so
     * the caller can fall back to "edit manually". 422 on an unknown chip.
     */
    async submitChangeFeedback(
        resumeId: string,
        changeId: string,
        feedbackType: FeedbackChip,
    ) {
        return this.request<ResumeChange>(
            `/api/resumes/${resumeId}/changes/${changeId}/feedback`,
            {
                method: 'POST',
                body: JSON.stringify({ feedback_type: feedbackType }),
            },
        );
    }

    /**
     * Transient resume roast — LLM-only, no DB writes. Backend defaults to
     * the master resume; `resumeId` is accepted for forward-compat.
     */
    async roastResume(resumeId?: string) {
        return this.request<RoastResponse>('/api/resumes/roast', {
            method: 'POST',
            body: JSON.stringify({ resume_id: resumeId ?? null }),
        });
    }
}

// Types matching backend schemas
export interface Job {
    id: string;
    title: string | null;
    company_name: string | null;
    location: string | null;
    posted_at: string | null;   // UTC ISO-8601 — use formatTimeAgo() at render time
    applicants_count: number | null;
    company_website: string | null;
    job_url?: string | null;
    updated_at?: string | null;
    salary_info?: string | null;
    description_text?: string | null;
    description_html?: string | null;
    // OotoCV: tailoring pipeline state (drives button copy and card verdict)
    tailoring_status?: 'not_started' | 'processing' | 'ready' | 'cancelled' | 'needs_review' | null;
    // OotoCV phase 6: pipeline_runs.id this job belongs to. NULL for legacy
    // jobs imported before run-linking (ADR-0025); UI groups those under a
    // "Pre-runs" bucket in the feed.
    run_id?: string | null;
}

export interface JobDetail extends Job {
    seniority_level: string | null;
    employment_type: string | null;
    // link removed, inherited job_url
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

// 4-way OotoCV verdict (ADR-0023). The legacy 'apply' value is retained so
// historical evaluation rows render correctly until they're re-evaluated;
// new evals emit one of the OotoCV-vocab values below.
export type RecommendedAction =
    | 'apply'         // legacy — historical rows only
    | 'apply_direct'  // strong match, no tailoring required
    | 'tailor'        // solid fit but needs targeted edits
    | 'borderline'    // on the fence; deciding_factor explains why
    | 'skip';         // not a fit

export interface Evaluation {
    job_id: string;
    job_url: string | null;
    company_name: string | null;
    company_website: string | null;
    title_role: string | null;
    verdict: 'Strong Match' | 'Moderate Match' | 'Weak Match' | null;
    job_match_score: number | null;
    summary: string | null;
    required_exp: string | null;
    recommended_action: RecommendedAction | null;
    gaps: Gaps | null;
    improvement_suggestions: ImprovementSuggestions | null;
    interview_tips: InterviewTips | null;
    jd_keywords: string[] | null;
    matched_keywords: string[] | null;
    missing_keywords: string[] | null;
    evaluated_at: string | null;
    recruiter_email?: string | null;
    wit_line?: string | null;
    // OotoCV phase 6 (ADR-0023): pre-computed feed-card lines. Populate
    // exactly one matching the verdict; the others stay NULL.
    top_strength?: string | null;       // TAILOR cards
    deciding_factor?: string | null;    // BORDERLINE cards + detail page hero
    kill_shot?: string | null;          // SKIP cards + detail page red banner
    // Array of "Label — explanation" strings for the SKIP layout. Em-dash
    // separator is load-bearing — splitter is " — " (R6).
    red_flags?: string[] | null;
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

export interface TailoredResume {
    id: string;
    job_id: string;
    version: number;
    content: any;
    status: 'pending' | 'approved' | 'rejected' | 'needs_review';
    tailoring_status: 'not_started' | 'processing' | 'ready' | 'cancelled' | 'needs_review' | null;
    cover_letter: string | null;
    gdoc_url: string | null;
    created_at: string;
}

// OotoCV: per-change review record (ADR-0010)
export type FeedbackChip = 'too_formal' | 'not_accurate' | 'other';

export interface ResumeChange {
    id: string;
    resume_id: string;
    job_id: string;
    location: string;
    action_type: 'rephrase' | 'add' | 'remove';
    original_text: string | null;   // immutable pre-AI text
    tailored_text: string | null;   // AI output
    accepted_text: string | null;   // set by user action; null = not reviewed
    review_action: 'accept' | 'reject' | 'keep_original' | null;
    reason: string | null;
    confidence: number | null;
    approved_source: string | null;
    created_at: string;
    updated_at: string;
    // OotoCV phase 6: reject-flow feedback (migration 024).
    feedback_type?: FeedbackChip | null;
    regenerated_at?: string | null;
    regeneration_count?: number;     // capped at 2 by the backend (R8)
}

export interface TaskStatus {
    task_id: string;
    status: 'queued' | 'running' | 'completed' | 'failed';
    progress: {
        completed: number;
        total: number;
        failed?: number;
        last_error?: string;
    } | null;
    created_at: string | null;
    completed_at: string | null;
    error: string | null;
}

export interface MessageResponse {
    message: string;
    job_id?: string;
    task_id?: string;
}

// OotoCV: Application tracker (phase 5 + 6 — offer + ghost commentary)
export type ApplicationStatus =
    | 'applied'
    | 'replied'
    | 'interview'
    | 'rejected'
    | 'ghosting'
    | 'offer';   // OotoCV phase 6 celebration state (migration 023)

export interface Application {
    id: string;
    job_id: string;
    job_title: string | null;
    company_name: string | null;
    resume_id: string | null;
    cv_version: 'base' | 'tailored';
    status: ApplicationStatus;
    status_history: Array<{ status: string; timestamp: string }>;
    applied_at: string;
    // OotoCV phase 6: computed server-side on every read, never stored.
    // Backend recomputes from days_since_update so commentary ages with the row.
    // Response carries Cache-Control: no-store (R5).
    ghost_commentary?: string | null;
    days_since_update?: number | null;
}

// Scheduler types
export interface PipelineRun {
    status: 'running' | 'completed' | 'failed';
    started_at: string | null;
    finished_at: string | null;
    error?: string | null;
}

export interface ServiceToggles {
    openrouter: boolean;
    apify: boolean;
    google_docs: boolean;
}

export interface SchedulerStatus {
    scheduler_running: boolean;
    last_runs: Record<string, PipelineRun>;
    jobs: Array<{ name: string; next_run_utc: string | null }>;
}

// ─────────────────────────────────────────────────────────────────
// OotoCV phase 6 — runs feed, pipeline config, system status, roast
// (Migrations 021–025, ADRs 0023–0025)
// ─────────────────────────────────────────────────────────────────

/** One row from /api/runs (RPC `runs_with_counts`). */
export interface Run {
    id: string;
    started_at: string;
    finished_at: string | null;
    status: 'running' | 'completed' | 'failed' | 'skipped';
    jobs_found: number;
    tailor_count: number;
    borderline_count: number;
    apply_direct_count: number;
    skip_count: number;
}

export type PipelineMode = 'auto' | 'manual';

/** Per-stage pipeline mode + auto_send_threshold (ADR-0024). */
export interface PipelineConfig {
    scrape_mode: PipelineMode;
    evaluate_mode: PipelineMode;
    tailor_mode: PipelineMode;
    auto_send_threshold: number;   // 0..4, see ADR-0012
}

/** Cron sidebar pulse feed (replaces SchedulerStatus polling for the pulse). */
export interface SystemStatus {
    cron_state: 'active' | 'sleeping' | 'error';
    next_run_at: string | null;     // ISO timestamp, or null if all stages manual
    last_error: string | null;
}

/** One entry in the transient resume roast response. */
export interface RoastItem {
    section: string;
    quote: string;
    verdict: string;
    fixed?: string | null;
}

export interface RoastResponse {
    items: RoastItem[];
}

// Export singleton instance
export const apiClient = new ApiClient();
export default apiClient;
