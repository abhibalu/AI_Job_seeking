import apiClient, {
  Job,
  JobDetail,
  Evaluation,
  EvaluationStats,
  ParseResult,
  TaskStatus,
  MessageResponse
} from './apiClient';

// Re-export types for convenience
export type { Job, JobDetail, Evaluation, EvaluationStats, ParseResult, TaskStatus, MessageResponse };

/**
 * Combined job with optional evaluation data
 */
export interface JobWithEvaluation extends Job {
  evaluation?: Evaluation;
  isEvaluated: boolean;
}

/**
 * Fetch jobs with their evaluation status
 */
export const fetchJobsWithEvaluations = async (
  page: number,
  limit: number,
  company?: string,
  is_evaluated?: boolean
): Promise<{ data: JobWithEvaluation[]; total: number }> => {
  try {
    // Fetch jobs and evaluations in parallel
    const [jobs, evaluations] = await Promise.all([
      apiClient.getJobs((page - 1) * limit, limit, company, is_evaluated),
      apiClient.getEvaluations(0, 1000), // Get all evaluations for matching
    ]);

    // Create a map of evaluations by job_id
    const evalMap = new Map<string, Evaluation>();
    evaluations.forEach(e => evalMap.set(e.job_id, e));

    // Merge jobs with their evaluations
    const jobsWithEvals: JobWithEvaluation[] = jobs.map(job => ({
      ...job,
      evaluation: evalMap.get(job.id),
      isEvaluated: evalMap.has(job.id),
    }));

    // Get total count from stats
    const stats = await apiClient.getJobStats(company, is_evaluated);

    return {
      data: jobsWithEvals,
      total: stats.total_jobs,
    };
  } catch (error) {
    console.error('Failed to fetch jobs:', error);
    throw error;
  }
};

/**
 * Fetch only evaluated jobs
 */
export const fetchEvaluations = async (
  page: number,
  limit: number,
  action?: 'apply' | 'tailor' | 'skip'
): Promise<{ data: Evaluation[]; total: number }> => {
  try {
    const evaluations = await apiClient.getEvaluations((page - 1) * limit, limit, action);
    const stats = await apiClient.getEvaluationStats();

    return {
      data: evaluations,
      total: stats.total_evaluated,
    };
  } catch (error) {
    console.error('Failed to fetch evaluations:', error);
    throw error;
  }
};

/**
 * Evaluate a single job
 */
export const evaluateJob = async (jobId: string, force: boolean = false): Promise<MessageResponse> => {
  try {
    return await apiClient.evaluateJob(jobId, force);
  } catch (error) {
    console.error('Failed to evaluate job:', error);
    throw error;
  }
};

/**
 * Start batch evaluation
 */
export const startBatchEvaluation = async (
  maxJobs: number,
  onlyUnevaluated: boolean = true,
  companyFilter?: string
): Promise<MessageResponse> => {
  try {
    return await apiClient.batchEvaluate(maxJobs, onlyUnevaluated, companyFilter);
  } catch (error) {
    console.error('Failed to start batch evaluation:', error);
    throw error;
  }
};

/**
 * Get batch task status
 */
export const getTaskStatus = async (taskId: string): Promise<TaskStatus> => {
  try {
    return await apiClient.getTaskStatus(taskId);
  } catch (error) {
    console.error('Failed to get task status:', error);
    throw error;
  }
};

/**
 * Parse JD for a job
 */
export const parseJobDescription = async (jobId: string, force: boolean = false): Promise<MessageResponse> => {
  try {
    return await apiClient.parseJD(jobId, force);
  } catch (error) {
    console.error('Failed to parse JD:', error);
    throw error;
  }
};

/**
 * Get parsed JD results
 */
export const getParsedJD = async (jobId: string): Promise<ParseResult> => {
  try {
    return await apiClient.getParsedJD(jobId);
  } catch (error) {
    console.error('Failed to get parsed JD:', error);
    throw error;
  }
};

/**
 * Get evaluation stats for dashboard
 */
export const getEvaluationStats = async (): Promise<EvaluationStats> => {
  try {
    return await apiClient.getEvaluationStats();
  } catch (error) {
    console.error('Failed to get evaluation stats:', error);
    throw error;
  }
};

/**
 * Get single evaluation
 */
export const getEvaluation = async (jobId: string): Promise<Evaluation> => {
  try {
    return await apiClient.getEvaluation(jobId);
  } catch (error) {
    console.error('Failed to get evaluation:', error);
    throw error;
  }
};

/**
 * Delete jobs in bulk
 */
export const deleteJobs = async (ids: string[]): Promise<void> => {
  try {
    await apiClient.deleteJobs(ids);
  } catch (error) {
    console.error('Failed to delete jobs:', error);
    throw error;
  }
};

/**
 * Import job from URL
 */
export const importJob = async (url: string): Promise<{
  id: string;
  status: string;
  count?: number;
  first_job?: { id: string; title: string; company: string };
  ids?: string[];
}> => {
  try {
    return await apiClient.importJob(url);
  } catch (error) {
    console.error('Failed to import job:', error);
    throw error;
  }
};

/**
 * Get all job IDs (for select all)
 */
export const getAllJobIds = async (company?: string): Promise<string[]> => {
  try {
    return await apiClient.getAllJobIds(company);
  } catch (error) {
    console.error('Failed to get all job IDs:', error);
    throw error;
  }
};
