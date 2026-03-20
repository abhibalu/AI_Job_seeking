import React, { useState, useCallback, useMemo, useEffect } from 'react';
import { Routes, Route, useNavigate } from 'react-router-dom';
import { JobWithEvaluation } from './services/jobService';
import { apiClient } from './services/apiClient';
import type { ServiceToggles } from './services/apiClient';
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
  const [serviceToggles, setServiceToggles] = useState<ServiceToggles | null>(null);

  useEffect(() => {
    apiClient.getServiceToggles().then(setServiceToggles).catch(() => {});
  }, []);

  const refreshToggles = useCallback(() => {
    apiClient.getServiceToggles().then(setServiceToggles).catch(() => {});
  }, []);

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
    updateJobEvaluation,
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

  const handleUndoSkip = useCallback((jobId: string) => {
    unmarkActioned(jobId);
  }, [unmarkActioned]);

  const handleReEvaluate = useCallback(async (jobId: string) => {
    await apiClient.evaluateJob(jobId, true);
    const freshEval = await apiClient.getEvaluation(jobId);
    updateJobEvaluation(jobId, freshEval);
  }, [updateJobEvaluation]);

  const handleTailorStart = useCallback(async (jobId: string) => {
    const job = allJobs.find(j => j.id === jobId);
    if (!job) return;

    // Already tailored — navigate to existing review
    if (job.tailoring_status === 'ready') {
      apiClient.getTailoredVersions(jobId).then(versions => {
        if (versions.length > 0) navigate(`/tailoring/${versions[0].id}`);
      }).catch(() => {});
      return;
    }

    // Already in progress — don't fire another run
    if (job.tailoring_status === 'processing') {
      setToast({ message: 'Already tailoring this job', type: 'error' });
      return;
    }

    // Concurrency guard — one tailoring at a time
    if (tailoringJob) {
      setToast({ message: `Already tailoring ${tailoringJob.title}`, type: 'error' });
      return;
    }

    try {
      const result = await apiClient.tailorResume(jobId);
      // Show TailoringStrip with real SSE tracking
      setTailoringJob(job);
      setTailoringTaskId(result.task_id);
    } catch (err: any) {
      setToast({ message: `Tailoring failed: ${err.message}`, type: 'error' });
    }
  }, [allJobs, navigate, tailoringJob]);

  const handleTailorComplete = useCallback((jobId: string, resumeId?: string) => {
    setTailoringJob(null);
    setTailoringTaskId(null);
    refresh(true);

    if (resumeId) {
      navigate(`/tailoring/${resumeId}`);
    } else {
      // Fallback: fetch versions
      apiClient.getTailoredVersions(jobId).then(versions => {
        if (versions.length > 0) {
          navigate(`/tailoring/${versions[0].id}`);
        }
      }).catch(() => {});
    }
  }, [refresh, navigate]);

  const handleTailorCancel = useCallback(async () => {
    if (tailoringTaskId) {
      try {
        await apiClient.cancelTask(tailoringTaskId);
      } catch {}
    }
    setTailoringJob(null);
    setTailoringTaskId(null);
    setToast({ message: 'Tailoring stopped', type: 'success' });
  }, [tailoringTaskId]);

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
                    onTailorStart={handleTailorStart}
                    onAction={handleAction}
                    onSkip={handleSkip}
                    verdictFilter={verdictFilter}
                    onVerdictFilterChange={setVerdictFilter}
                    isTailoring={!!tailoringJob}
                    serviceToggles={serviceToggles}
                  />

                  {/* Detail pane */}
                  <div className="flex-1 min-w-0 h-full overflow-hidden">
                    {selectedJob ? (
                      <JobDetail
                        job={selectedJob}
                        onTailorStart={handleTailorStart}
                        onAction={handleAction}
                        onSkip={handleSkip}
                        onUndoSkip={handleUndoSkip}
                        onReEvaluate={handleReEvaluate}
                        serviceToggles={serviceToggles}
                      />
                    ) : (
                      <div className="h-full flex items-center justify-center">
                        <p className="text-[11px] font-mono text-gray-600">Select a job to view details</p>
                      </div>
                    )}
                  </div>
                </>
              }
            />
            <Route path="/tailoring/:id" element={<TailoringReview serviceToggles={serviceToggles} />} />
            <Route path="/tracker" element={<ApplicationTracker />} />
            <Route path="/settings" element={<SetupPage isOnboarding={false} onTogglesChanged={refreshToggles} />} />
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
