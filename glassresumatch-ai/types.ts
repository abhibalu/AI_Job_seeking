// Re-export all types from apiClient for convenience
export {
  type Job,
  type JobDetail,
  type JobStats,
  type Gaps,
  type ImprovementSuggestions,
  type InterviewTips,
  type Evaluation,
  type EvaluationStats,
  type ParseResult,
  type TaskStatus,
  type MessageResponse,
} from './services/apiClient';

export { type JobWithEvaluation } from './services/jobService';

// View mode for the app
export type ViewMode = 'all' | 'evaluated' | 'pending';

// Filter options
export interface FilterOptions {
  searchQuery: string;
  verdict: 'all' | 'Strong Match' | 'Moderate Match' | 'Weak Match';
  action: 'all' | 'apply' | 'tailor' | 'skip';
  sortBy: 'score' | 'company' | 'date';
  sortOrder: 'asc' | 'desc';
}
