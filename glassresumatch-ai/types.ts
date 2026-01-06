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
export type ViewMode = 'all' | 'evaluated' | 'pending' | 'resume';

// Filter options
export interface FilterOptions {
  searchQuery: string;
  verdict: 'all' | 'Strong Match' | 'Moderate Match' | 'Weak Match';
  action: 'all' | 'apply' | 'tailor' | 'skip';
  sortBy: 'score' | 'company' | 'date';
  sortOrder: 'asc' | 'desc';
}

// --- Resume Builder Types ---

export interface Experience {
  id: string;
  company: string;
  role: string;
  period: string;
  location?: string;
  achievements: string[];
}

export interface Education {
  id: string;
  institution: string;
  degree: string;
  period: string;
  location: string;
}

export interface ResumeData {
  fullName: string;
  title?: string;
  phone: string;
  email: string;
  location: string;
  websites: string[];
  summary?: string;
  experience: Experience[];
  education: Education[];
  skills: string[];
}

export const INITIAL_DATA: ResumeData = {
  fullName: "Your Name",
  title: "Professional Title",
  phone: "+1 234 567 890",
  email: "email@example.com",
  location: "City, Country",
  websites: [],
  summary: "Professional summary goes here...",
  experience: [],
  education: [],
  skills: []
};
