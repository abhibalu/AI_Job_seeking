/**
 * Dashboard.tsx — OotoCV reference layout, wired to the live backend.
 *
 * Single-column fat-card feed grouped by verdict:
 *   Primary    : TAILOR + APPLY DIRECT       (action band — top of feed)
 *   Borderline : BORDERLINE                  (secondary group, smaller header)
 *   SKIP       : SKIP                        (collapsed by default)
 *
 * Data: fetches `apiClient.getJobs({is_evaluated: true})` so cards always
 * have a verdict. Each backend Job + Evaluation is mapped through
 * `toReferenceJob` before render. Run grouping (per ADR-0025) is handled
 * by the feed header copy ("Last run today at 5:00 PM — N jobs found").
 *
 * Skip and Apply-Direct overrides are local-only (optimistic) — the
 * backend tracks Apply via /api/applications which the JobDetail page
 * fires; the Dashboard just removes the card from view immediately.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

import { JobCard } from '../components/JobCard';
import { TypewriterWaitState } from '../components/TypewriterWaitState';
import { fetchJobsWithEvaluations } from '../services/jobService';
import type { JobWithEvaluation } from '../services/jobService';
import { toReferenceJob } from '../services/jobAdapter';
import type { ReferenceJob } from '../services/jobAdapter';
import { apiClient } from '../services/apiClient';

type Override = 'SKIP' | 'APPLIED';

interface DashboardProps {
  /** Called when the user clicks Tailor on a JobCard. Receives the
   * reference-shape job plus a backend task_id from `tailorResume`. */
  onTailor?: (job: ReferenceJob, taskId: string) => void;
  onActionableCountChange?: (count: number) => void;
}

const FEED_LOADED_KEY = 'feed_loaded';

export const Dashboard: React.FC<DashboardProps> = ({ onTailor, onActionableCountChange }) => {
  // Loading typewriter — first visit per session only.
  const [showLoadingTypewriter] = useState(() => !sessionStorage.getItem(FEED_LOADED_KEY));
  const [loadingTypewriterDone, setLoadingTypewriterDone] = useState(!showLoadingTypewriter);

  const [refJobs, setRefJobs] = useState<ReferenceJob[]>([]);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [feedLoaded, setFeedLoaded] = useState(false);

  // Optimistic overrides: SKIP removes the card from primary, APPLIED
  // hides it entirely (treated as logged in tracker).
  const [overrides, setOverrides] = useState<Record<string, Override>>({});

  // Skip toggle for the collapsed Skip section.
  const [showSkipped, setShowSkipped] = useState(false);

  // Load jobs once on mount. Page 1 with a high limit — the OotoCV feed
  // is a flat scroll, not paginated; users go to the tracker for old jobs.
  useEffect(() => {
    let cancelled = false;
    fetchJobsWithEvaluations(1, 100, undefined, true)
      .then(({ data }) => {
        if (cancelled) return;
        const mapped = data
          .filter((j: JobWithEvaluation) => j.isEvaluated && j.evaluation)
          .map(j => toReferenceJob(j));
        setRefJobs(mapped);
        setFeedLoaded(true);
      })
      .catch(err => {
        if (cancelled) return;
        setFetchError(err?.message ?? 'Failed to load jobs.');
        setFeedLoaded(true);
      });
    return () => { cancelled = true; };
  }, []);

  const handleLoadComplete = useCallback(() => {
    sessionStorage.setItem(FEED_LOADED_KEY, 'true');
    setLoadingTypewriterDone(true);
  }, []);

  const effectiveVerdict = useCallback((job: ReferenceJob): ReferenceJob['verdict'] | 'APPLIED' => {
    return (overrides[job.id] as Override) || job.verdict;
  }, [overrides]);

  const primary = useMemo(() => refJobs.filter(j => {
    const v = effectiveVerdict(j);
    return v === 'TAILOR' || v === 'APPLY DIRECT';
  }), [refJobs, effectiveVerdict]);

  const borderline = useMemo(
    () => refJobs.filter(j => effectiveVerdict(j) === 'BORDERLINE'),
    [refJobs, effectiveVerdict],
  );

  const skipped = useMemo(
    () => refJobs.filter(j => effectiveVerdict(j) === 'SKIP'),
    [refJobs, effectiveVerdict],
  );

  // Bubble the actionable count to App.tsx for the sidebar badge.
  useEffect(() => {
    onActionableCountChange?.(primary.length);
  }, [primary.length, onActionableCountChange]);

  const handleSkip = useCallback((id: string) => {
    setOverrides(prev => ({ ...prev, [id]: 'SKIP' }));
  }, []);

  const handleApplyDirect = useCallback(async (job: ReferenceJob) => {
    // Open the original posting in a new tab.
    if (job.originalUrl) {
      window.open(job.originalUrl, '_blank', 'noopener,noreferrer');
    }
    // Optimistically log the application — fire-and-forget; if it fails
    // the user can still re-record it from the JobDetail page.
    try {
      await apiClient.createApplication(job.id, 'base', {
        jobTitle: job.role,
        companyName: job.company,
      });
    } catch {
      /* swallow — optimistic UI is what matters here */
    }
    setOverrides(prev => ({ ...prev, [job.id]: 'APPLIED' }));
  }, []);

  const handleTailor = useCallback(async (job: ReferenceJob) => {
    // Kick off the background tailoring pipeline; App.tsx mounts the
    // TailoringStrip with the returned task_id so SSE drives progress.
    try {
      const resp = await apiClient.tailorResume(job.id);
      onTailor?.(job, resp.task_id);
    } catch (err) {
      // Failure is non-fatal — keep the card on screen so the user can retry.
      console.warn('tailorResume failed:', err);
    }
  }, [onTailor]);

  // First-load typewriter
  if (showLoadingTypewriter && !loadingTypewriterDone) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <TypewriterWaitState
          messages={[
            'Waking up the cron job...',
            'Scraping job boards...',
            'Filtering out "entry-level" roles requiring 5 years experience...',
            "Judging Glassdoor reviews so you don't have to...",
            'Compiling your feed...',
          ]}
          onComplete={handleLoadComplete}
        />
      </div>
    );
  }

  // Network spinner while the real fetch resolves (typewriter already finished)
  if (!feedLoaded) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-6 h-6 rounded-full border-2 border-accent/40 border-t-accent animate-spin" />
      </div>
    );
  }

  if (fetchError) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <p className="text-semantic-red font-mono text-sm">{fetchError}</p>
      </div>
    );
  }

  const visibleTotal = refJobs.length - Object.values(overrides).filter(v => v === 'APPLIED').length;
  const headerTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  return (
    <div className="flex-1 p-8 overflow-y-auto max-w-3xl w-full">
      <header className="mb-8">
        <h1 className="text-3xl font-sans font-bold tracking-tight text-white mb-2">Feed</h1>
        <p className="text-gray-400 font-mono text-sm">
          Last run today at {headerTime} — {visibleTotal} job{visibleTotal !== 1 ? 's' : ''} found.
        </p>
      </header>

      {/* Primary: TAILOR + APPLY DIRECT */}
      {primary.length > 0 ? (
        <div className="flex flex-col gap-3">
          {primary.map(job => (
            <JobCard
              key={job.id}
              job={job}
              onSkip={handleSkip}
              onTailor={handleTailor}
              onApplyDirect={handleApplyDirect}
            />
          ))}
        </div>
      ) : (
        <div className="py-12 text-center">
          <p className="text-gray-500 font-mono text-sm">
            Nothing actionable left. You're either very decisive or very tired. Check back at 5pm.
          </p>
        </div>
      )}

      {/* Secondary: BORDERLINE */}
      {borderline.length > 0 && (
        <div className="mt-10">
          <div className="flex items-center gap-3 mb-4">
            <h2 className="text-sm font-mono text-gray-500 uppercase tracking-wider">Borderline</h2>
            <div className="h-px flex-1 bg-white/5" />
            <span className="text-xs font-mono text-gray-600">{borderline.length} job{borderline.length !== 1 ? 's' : ''}</span>
          </div>
          <p className="text-xs font-mono text-gray-600 mb-4">
            Not obvious wins. Might be worth a shot if the week is slow.
          </p>
          <div className="flex flex-col gap-3">
            {borderline.map(job => (
              <JobCard
                key={job.id}
                job={job}
                onSkip={handleSkip}
                onTailor={handleTailor}
                onApplyDirect={handleApplyDirect}
              />
            ))}
          </div>
        </div>
      )}

      {/* Collapsed: SKIP */}
      {skipped.length > 0 && (
        <div className="mt-8">
          <button
            onClick={() => setShowSkipped(!showSkipped)}
            className="w-full py-3 px-4 flex items-center justify-center gap-2 rounded-lg border border-white/5 bg-surface hover:bg-surface-hover text-sm font-mono text-gray-400 transition-colors"
          >
            {showSkipped ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            {skipped.length} hard pass{skipped.length !== 1 ? 'es' : ''} hidden — {showSkipped ? 'hide them' : 'show them?'}
          </button>

          {showSkipped && (
            <div className="flex flex-col gap-3 mt-4">
              {skipped.map(job => (
                <JobCard
                  key={job.id}
                  job={job}
                  dimmed
                  onSkip={handleSkip}
                  onTailor={handleTailor}
                  onApplyDirect={handleApplyDirect}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {refJobs.length === 0 && (
        <div className="mt-12 text-center">
          <p className="text-gray-500 font-mono italic">
            Nothing today. The job market is tired. Check back at 5pm.
          </p>
        </div>
      )}
    </div>
  );
};
