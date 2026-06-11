/**
 * App.tsx — OotoCV shell (ADR-0026, supersedes ADR-0007).
 *
 * Routes match the OotoCV reference verbatim:
 *   /              Dashboard (single-column fat-card feed)
 *   /job/:id       JobDetail (verdict-conditional layout)
 *   /tailoring/:id TailoringReview (2-pane diff + cover letter)
 *   /roast         ResumeRoast (3-state utility)
 *   /tracker       ApplicationTracker
 *   /settings      Settings
 *   /onboarding    Onboarding (5-step wizard)
 *
 * The TailoringStrip floats outside the route tree so navigation never
 * interrupts an in-flight tailoring job. Onboarding hides the Sidebar
 * (`isConfigured && <Sidebar />`) to focus the wizard.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom';

import { Sidebar } from './components/Sidebar';
import { TailoringStrip } from './components/TailoringStrip';
import { ApplicationTracker } from './pages/ApplicationTracker';
import { Dashboard } from './pages/Dashboard';
import { JobDetail } from './pages/JobDetail';
import { Onboarding } from './pages/Onboarding';
import { ResumeRoast } from './pages/ResumeRoast';
import { Settings } from './pages/Settings';
import { TailoringReview } from './pages/TailoringReview';
import { cn } from './lib/utils';
import type { ReferenceJob } from './services/jobAdapter';

const App: React.FC = () => {
  const navigate = useNavigate();

  // Onboarding gate: localStorage flag from the original SetupPage flow
  // is mirrored under the OotoCV key so a returning user doesn't get
  // dropped back into the wizard.
  const [isConfigured, setIsConfigured] = useState<boolean | null>(null);
  useEffect(() => {
    const t = setTimeout(() => {
      const legacy = localStorage.getItem('onboarding_complete');
      const ootocv = localStorage.getItem('ootocv_configured');
      setIsConfigured(ootocv !== 'false' && (ootocv === 'true' || legacy === 'true' || legacy === null));
    }, 200);
    return () => clearTimeout(t);
  }, []);

  // Sidebar badge — Dashboard reports its actionable count up.
  const [actionableBadge, setActionableBadge] = useState(0);
  const handleActionableCount = useCallback((n: number) => {
    setActionableBadge(n);
  }, []);

  // TailoringStrip controls — a Job from the feed becomes the in-flight
  // tailoring job; SSE wiring lives inside TailoringStrip via useSSE.
  const [tailoringJob, setTailoringJob] = useState<ReferenceJob | null>(null);
  const [tailoringTaskId, setTailoringTaskId] = useState<string | null>(null);

  const handleTailoringComplete = useCallback((resumeId?: string) => {
    if (tailoringJob && resumeId) {
      navigate(`/tailoring/${resumeId}`);
    } else if (tailoringJob) {
      navigate(`/tailoring/${tailoringJob.id}`);
    }
    setTailoringJob(null);
    setTailoringTaskId(null);
  }, [tailoringJob, navigate]);

  const handleTailoringCancel = useCallback(() => {
    setTailoringJob(null);
    setTailoringTaskId(null);
  }, []);

  if (isConfigured === null) {
    return (
      <div className="h-screen w-screen bg-base flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-2 border-accent border-t-transparent animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-base text-gray-200 font-sans overflow-hidden">
      {isConfigured && <Sidebar actionableBadge={actionableBadge} />}
      <div className={cn('flex-1 flex flex-col overflow-hidden', !isConfigured && 'w-full')}>
        <main className="flex-1 overflow-y-auto flex flex-col">
          <Routes>
            {!isConfigured ? (
              <Route path="*" element={<Navigate to="/onboarding" replace />} />
            ) : (
              <>
                <Route
                  path="/"
                  element={
                    <Dashboard
                      onTailor={(job, taskId) => {
                        setTailoringJob(job);
                        setTailoringTaskId(taskId);
                      }}
                      onActionableCountChange={handleActionableCount}
                    />
                  }
                />
                <Route
                  path="/job/:id"
                  element={
                    <JobDetail
                      onTailor={(job, taskId) => {
                        setTailoringJob(job);
                        setTailoringTaskId(taskId);
                      }}
                    />
                  }
                />
                <Route path="/tailoring/:id" element={<TailoringReview />} />
                <Route path="/roast" element={<ResumeRoast />} />
                <Route path="/tracker" element={<ApplicationTracker />} />
                <Route path="/settings" element={<Settings />} />
              </>
            )}
            <Route
              path="/onboarding"
              element={
                <Onboarding
                  onComplete={() => {
                    localStorage.setItem('ootocv_configured', 'true');
                    localStorage.setItem('onboarding_complete', 'true');
                    setIsConfigured(true);
                  }}
                />
              }
            />
          </Routes>
        </main>

        {/* TailoringStrip floats above the main scroll area so navigation
            doesn't disrupt the in-flight job (R: ambient agentic work). */}
        {tailoringJob && (
          <TailoringStrip
            job={tailoringJob}
            taskId={tailoringTaskId}
            onComplete={handleTailoringComplete}
            onCancel={handleTailoringCancel}
          />
        )}
      </div>
    </div>
  );
};

export default App;
