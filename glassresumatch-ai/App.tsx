import React, { useState, useEffect, useCallback } from 'react';
import { Evaluation, EvaluationStats } from './services/apiClient';
import {
  fetchJobsWithEvaluations,
  fetchEvaluations,
  evaluateJob,
  getEvaluationStats,
  getEvaluation,
  JobWithEvaluation
} from './services/jobService';
import { ViewMode, FilterOptions } from './types';
import { JobCard } from './components/JobCard';
import { JobModal } from './components/JobModal';
import { Pagination } from './components/Pagination';
import { Header } from './components/Header';
import { FilterBar } from './components/FilterBar';
import { StatsCard } from './components/StatsCard';
import { ResumePreview } from './components/ResumePreview';
import { BatchEvaluate } from './components/BatchEvaluate';
import { GlassCard } from './components/GlassCard';
import { Loader2, Sparkles, AlertCircle } from 'lucide-react';

const App: React.FC = () => {
  // Data state
  const [jobs, setJobs] = useState<JobWithEvaluation[]>([]);
  const [stats, setStats] = useState<EvaluationStats | null>(null);
  const [totalJobs, setTotalJobs] = useState(0);

  // UI state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedEvaluation, setSelectedEvaluation] = useState<Evaluation | null>(null);
  const [evaluatingJobId, setEvaluatingJobId] = useState<string | null>(null);

  // Filter state
  const [viewMode, setViewMode] = useState<ViewMode>('all');
  const [filters, setFilters] = useState<FilterOptions>({
    searchQuery: '',
    verdict: 'all',
    action: 'all',
    sortBy: 'score',
    sortOrder: 'desc',
  });

  // Modals
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isBatchModalOpen, setIsBatchModalOpen] = useState(false);
  const [newJobText, setNewJobText] = useState('');
  const [analyzing, setAnalyzing] = useState(false);

  const ITEMS_PER_PAGE = 9;

  // Load jobs and stats based on view mode
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const statsResult = await getEvaluationStats().catch(() => null);
      setStats(statsResult);

      if (viewMode === 'evaluated') {
        // Fetch from evaluations endpoint directly
        const actionFilter = filters.action !== 'all' ? filters.action : undefined;
        const evaluationsResult = await fetchEvaluations(currentPage, ITEMS_PER_PAGE, actionFilter);

        // Convert evaluations to JobWithEvaluation format
        const jobsWithEvals: JobWithEvaluation[] = evaluationsResult.data.map(e => ({
          id: e.job_id,
          title: e.title_role,
          company_name: e.company_name,
          location: null,
          posted_at: null,
          applicants_count: null,
          evaluation: e,
          isEvaluated: true,
        }));

        setJobs(jobsWithEvals);
        setTotalJobs(evaluationsResult.total);
      } else {
        // Fetch from jobs endpoint
        const jobsResult = await fetchJobsWithEvaluations(currentPage, ITEMS_PER_PAGE);
        setJobs(jobsResult.data);
        setTotalJobs(jobsResult.total);
      }
    } catch (err) {
      console.error('Failed to load data:', err);
      setError('Failed to load jobs. Make sure the API server is running.');
    } finally {
      setLoading(false);
    }
  }, [currentPage, viewMode, filters.action]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Filter and sort jobs
  const filteredJobs = jobs.filter(job => {
    // View mode filter
    if (viewMode === 'evaluated' && !job.isEvaluated) return false;
    if (viewMode === 'pending' && job.isEvaluated) return false;

    // Search filter
    if (filters.searchQuery) {
      const query = filters.searchQuery.toLowerCase();
      const matchesCompany = job.company_name?.toLowerCase().includes(query);
      const matchesTitle = job.title?.toLowerCase().includes(query);
      if (!matchesCompany && !matchesTitle) return false;
    }

    // Verdict filter
    if (filters.verdict !== 'all' && job.evaluation?.verdict !== filters.verdict) {
      return false;
    }

    // Action filter
    if (filters.action !== 'all' && job.evaluation?.recommended_action !== filters.action) {
      return false;
    }

    return true;
  }).sort((a, b) => {
    const multiplier = filters.sortOrder === 'asc' ? 1 : -1;

    switch (filters.sortBy) {
      case 'score':
        return ((b.evaluation?.job_match_score || 0) - (a.evaluation?.job_match_score || 0)) * multiplier;
      case 'company':
        return ((a.company_name || '').localeCompare(b.company_name || '')) * multiplier;
      case 'date':
        return ((b.posted_at || '').localeCompare(a.posted_at || '')) * multiplier;
      default:
        return 0;
    }
  });

  // Handle job card click
  const handleJobClick = async (job: JobWithEvaluation) => {
    if (job.isEvaluated && job.evaluation) {
      // Fetch full evaluation details
      try {
        const fullEval = await getEvaluation(job.id);
        setSelectedEvaluation(fullEval);
      } catch {
        setSelectedEvaluation(job.evaluation);
      }
    } else {
      // Show a toast or trigger evaluation
      handleEvaluateJob(job.id);
    }
  };

  // Handle evaluate job
  const handleEvaluateJob = async (jobId: string) => {
    setEvaluatingJobId(jobId);
    try {
      await evaluateJob(jobId);
      // Reload data to get updated evaluation
      await loadData();
      // Open the modal with the new evaluation
      const evaluation = await getEvaluation(jobId);
      setSelectedEvaluation(evaluation);
    } catch (err) {
      console.error('Failed to evaluate job:', err);
      setError('Failed to evaluate job. Please try again.');
    } finally {
      setEvaluatingJobId(null);
    }
  };

  // Handle analyze new JD (keep for future Gemini integration)
  const handleAnalyzeNewJob = async () => {
    if (!newJobText.trim()) return;
    setAnalyzing(true);
    try {
      // For now, just close the modal - this would integrate with Gemini
      setIsAddModalOpen(false);
      setNewJobText('');
      alert('New JD analysis coming soon! This will integrate with your Gemini key.');
    } catch (error) {
      console.error('Analysis failed', error);
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 selection:bg-blue-100 selection:text-blue-900">
      {/* Abstract Background Blobs */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-blue-100/50 blur-[100px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-purple-100/50 blur-[100px]" />
        <div className="absolute top-[30%] left-[60%] w-[20%] h-[20%] rounded-full bg-emerald-50/60 blur-[80px]" />
      </div>

      <Header
        onAddJob={() => setIsAddModalOpen(true)}
        onBatchEvaluate={() => setIsBatchModalOpen(true)}
        totalJobs={totalJobs}
        evaluatedCount={stats?.total_evaluated || 0}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
      />

      <main className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

        {/* Stats Card */}
        <StatsCard stats={stats} totalJobs={totalJobs} />

        {/* Filter Bar */}
        {/* Filter Bar */}
        {viewMode !== 'resume' && (
          <FilterBar
            viewMode={viewMode}
            onViewModeChange={setViewMode}
            filters={filters}
            onFiltersChange={setFilters}
          />
        )}

        {/* Error Message */}
        {error && (
          <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 mb-6 flex items-center">
            <AlertCircle className="w-5 h-5 text-rose-500 mr-3" />
            <p className="text-rose-700">{error}</p>
            <button
              onClick={loadData}
              className="ml-auto px-3 py-1 bg-rose-100 hover:bg-rose-200 text-rose-700 rounded-lg text-sm font-medium"
            >
              Retry
            </button>
          </div>
        )}

        {viewMode === 'resume' ? (
          <ResumePreview />
        ) : loading ? (
          <div className="flex flex-col items-center justify-center h-[60vh]">
            <Loader2 className="w-12 h-12 text-slate-300 animate-spin mb-4" />
            <p className="text-slate-500 animate-pulse font-medium">Loading jobs...</p>
          </div>
        ) : filteredJobs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-[40vh]">
            <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-4">
              <Sparkles className="w-8 h-8 text-slate-300" />
            </div>
            <p className="text-slate-500 font-medium">No jobs match your filters</p>
            <button
              onClick={() => {
                setViewMode('all');
                setFilters({
                  searchQuery: '',
                  verdict: 'all',
                  action: 'all',
                  sortBy: 'score',
                  sortOrder: 'desc',
                });
              }}
              className="mt-3 text-blue-600 hover:text-blue-700 text-sm font-medium"
            >
              Clear filters
            </button>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredJobs.map((job) => (
                <JobCard
                  key={job.id}
                  job={job}
                  onClick={() => handleJobClick(job)}
                  onEvaluate={() => handleEvaluateJob(job.id)}
                  isEvaluating={evaluatingJobId === job.id}
                />
              ))}
            </div>

            <Pagination
              currentPage={currentPage}
              totalPages={Math.ceil(totalJobs / ITEMS_PER_PAGE)}
              onPageChange={setCurrentPage}
            />
          </>
        )}
      </main>

      {/* Evaluation Detail Modal */}
      <JobModal
        evaluation={selectedEvaluation}
        onClose={() => setSelectedEvaluation(null)}
      />

      {/* Batch Evaluate Modal */}
      <BatchEvaluate
        isOpen={isBatchModalOpen}
        onClose={() => setIsBatchModalOpen(false)}
        onComplete={loadData}
      />

      {/* Add New Job / AI Analysis Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-slate-900/20 backdrop-blur-sm transition-opacity"
            onClick={() => !analyzing && setIsAddModalOpen(false)}
          />
          <GlassCard className="w-full max-w-2xl p-6 z-20 bg-white/95 shadow-2xl">
            <h2 className="text-xl font-bold mb-4 flex items-center text-slate-900">
              <Sparkles className="w-5 h-5 mr-2 text-blue-600" />
              Analyze New Job Description
            </h2>
            <textarea
              className="w-full h-48 bg-slate-50 border border-slate-200 rounded-xl p-4 text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-none transition-all"
              placeholder="Paste job description here..."
              value={newJobText}
              onChange={(e) => setNewJobText(e.target.value)}
              disabled={analyzing}
            />
            <div className="flex justify-end mt-4 space-x-3">
              <button
                onClick={() => setIsAddModalOpen(false)}
                disabled={analyzing}
                className="px-4 py-2 rounded-lg hover:bg-slate-100 text-slate-500 font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAnalyzeNewJob}
                disabled={analyzing || !newJobText.trim()}
                className="px-6 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-medium shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center transition-all"
              >
                {analyzing ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  'Analyze Match'
                )}
              </button>
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
};

export default App;