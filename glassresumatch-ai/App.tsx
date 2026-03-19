import React, { useState, useCallback, useMemo } from 'react';
import { Routes, Route, useNavigate } from 'react-router-dom';
import { JobWithEvaluation } from './services/jobService';
import { apiClient } from './services/apiClient';
import { useJobs } from './hooks/useJobs';
import { Sidebar } from './components/Sidebar';
import { TailoringStrip } from './components/TailoringStrip';
import { Dashboard } from './pages/Dashboard';
import { JobDetail } from './pages/JobDetail';
import { TailoringReview } from './pages/TailoringReview';
import { ApplicationTracker } from './pages/ApplicationTracker';
import { SetupPage } from './pages/SetupPage';
import { Toast } from './components/Toast';
import type { FilterOptions, Job } from './types';
import { Briefcase } from 'lucide-react';

const App: React.FC = () => {
  const navigate = useNavigate();

  // Onboarding gate
  const [showOnboarding, setShowOnboarding] = useState(
    !localStorage.getItem('onboarding_complete')
  );

  // Feed filters
  const [filters] = useState<FilterOptions>({
    searchQuery: '',
    verdict: 'all',
    action: 'all',
    sortBy: 'score',
    sortOrder: 'desc',
  });

  // Verdict filter (client-side)
  const [verdictFilter, setVerdictFilter] = useState<string[]>([]);

  // Selected job
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  // Tailoring state
  const [tailoringJob, setTailoringJob] = useState<Job | null>(null);
  const [tailoringTaskId, setTailoringTaskId] = useState<string | null>(null);

  // Toast
  const [toast, setToast] = useState<{ message: string; type: 'error' | 'success' } | null>(null);

  // Jobs hook
  const {
    activeJobs,
    actionedJobs,
    stats,
    loading,
    loadingMore,
    hasMore,
    loadMore,
    refresh,
    markActioned,
    unmarkActioned,
  } = useJobs('all', filters);

  // All jobs for lookup
  const allJobs = useMemo(() => [...activeJobs, ...actionedJobs], [activeJobs, actionedJobs]);

  // Actionable badge count — from stats (not paginated list) for accuracy
  const actionableBadge = useMemo(() => {
    if (stats?.by_action) {
      return (stats.by_action['apply'] || 0) + (stats.by_action['tailor'] || 0);
    }
    return 0;
  }, [stats]);

  const selectedJob = allJobs.find(j => j.id === selectedJobId) || null;

  const handleJobClick = useCallback((job: JobWithEvaluation) => {
    setSelectedJobId(job.id);
  }, []);

  const handleAction = useCallback(async (jobId: string, cvVersion: 'base' | 'tailored') => {
    const job = allJobs.find(j => j.id === jobId);
    markActioned(jobId);

    // Open job URL
    if (job?.job_url) {
      window.open(job.job_url, '_blank');
    }

    try {
      await apiClient.patchJobAction(jobId, cvVersion);
      // Create application record
      await apiClient.createApplication(jobId, cvVersion, {
        jobTitle: job?.title || undefined,
        companyName: job?.company_name || undefined,
      });
    } catch {
      unmarkActioned(jobId);
      setToast({ message: 'Action failed. Try again.', type: 'error' });
    }
  }, [allJobs, markActioned, unmarkActioned]);

  const handleSkip = useCallback((jobId: string) => {
    markActioned(jobId);
  }, [markActioned]);

  const handleTailorStart = useCallback(async (jobId: string) => {
    const job = allJobs.find(j => j.id === jobId);
    if (!job) return;

    try {
      const result = await apiClient.tailorResume(jobId);
      setTailoringJob(job);
      // If the tailoring returns a task_id for SSE tracking
      if ((result as any).task_id) {
        setTailoringTaskId((result as any).task_id);
      }
    } catch (err: any) {
      setToast({ message: `Tailoring failed: ${err.message}`, type: 'error' });
    }
  }, [allJobs]);

  const handleTailorComplete = useCallback((jobId: string) => {
    setTailoringJob(null);
    setTailoringTaskId(null);
    refresh(true);

    // Navigate to review
    apiClient.getTailoredVersions(jobId).then(versions => {
      if (versions.length > 0) {
        navigate(`/tailoring/${versions[0].id}`);
      }
    }).catch(() => {});
  }, [refresh, navigate]);

  const handleTailorCancel = useCallback(() => {
    setTailoringJob(null);
    setTailoringTaskId(null);
  }, []);

  // Onboarding gate
  if (showOnboarding) {
    return (
      <SetupPage
        isOnboarding={true}
        onComplete={() => setShowOnboarding(false)}
      />
    );
  }

  return (
    <div className="flex h-screen bg-base text-gray-200 font-sans overflow-hidden">
      <Sidebar actionableBadge={actionableBadge} />

      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex-1 flex min-h-0">
          <Routes>
            <Route
              path="/"
              element={
                <>
                  {/* Feed pane */}
                  <Dashboard
                    jobs={allJobs}
                    activeJobs={activeJobs}
                    actionedJobs={actionedJobs}
                    stats={stats}
                    loading={loading}
                    loadingMore={loadingMore}
                    hasMore={hasMore}
                    loadMore={loadMore}
                    selectedJobId={selectedJobId}
                    onJobClick={handleJobClick}
                    onAction={handleAction}
                    onSkip={handleSkip}
                    verdictFilter={verdictFilter}
                    onVerdictFilterChange={setVerdictFilter}
                  />

                  {/* Detail pane */}
                  <div className="flex-1 min-w-0">
                    {selectedJob ? (
                      <JobDetail
                        job={selectedJob}
                        onTailorStart={handleTailorStart}
                        onAction={handleAction}
                        onSkip={handleSkip}
                      />
                    ) : (
                      <div className="h-full flex flex-col items-center justify-center text-gray-600">
                        <Briefcase className="w-8 h-8 mb-3 opacity-30" />
                        <p className="text-[11px] font-mono">Select a job to view details</p>
                      </div>
                    )}
                  </div>
                </>
              }
            />
            <Route path="/tailoring/:id" element={<TailoringReview />} />
            <Route path="/tracker" element={<ApplicationTracker />} />
            <Route path="/settings" element={<SetupPage isOnboarding={false} />} />
            <Route
              path="/onboarding"
              element={<SetupPage isOnboarding={true} onComplete={() => navigate('/')} />}
            />
          </Routes>
        </div>

        {/* Tailoring Strip */}
        {tailoringJob && (
          <TailoringStrip
            job={tailoringJob}
            taskId={tailoringTaskId}
            onComplete={handleTailorComplete}
            onCancel={handleTailorCancel}
          />
        )}
      </div>

      {toast && (
        <Toast message={toast.message} type={toast.type} onDismiss={() => setToast(null)} />
      )}
    </div>
  );
};

export default App;
