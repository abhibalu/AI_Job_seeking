/**
 * TailoringReview.tsx — OotoCV reference layout, wired to live backend.
 *
 * The reference shows a 2-pane Base/Tailored diff with a single global
 * "Request Changes" / "Approve & Send" flow. The live backend has
 * per-change `resume_changes` rows (ADR-0010) so we can render the diff
 * from real data instead of hardcoded text. Per-change accept/reject UI
 * is intentionally omitted in this port — the reference uses a single
 * "Request Changes" textarea that re-runs the pipeline with the user's
 * feedback (mapped to bulk apply behaviour + a re-tailor call).
 *
 * Approve & Send:
 *   updateTailoredStatus('approved')
 *   exportToGoogleDocs(jobId)   → toast variants per ExportResult.status
 *   navigate('/tracker')
 *
 * `:id` in the route is the resume_id (Phase 1 placeholder-row pattern).
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { AnimatePresence, motion } from 'motion/react';
import { ArrowLeft, CheckCircle2, RefreshCw, RotateCcw, Send, Sparkles } from 'lucide-react';

import { cn } from '../lib/utils';
import { MatchBrief } from '../components/MatchBrief';
import { TypewriterWaitState } from '../components/TypewriterWaitState';
import { apiClient } from '../services/apiClient';
import { toReferenceJob } from '../services/jobAdapter';
import type { ReferenceJob } from '../services/jobAdapter';
import type { ResumeChange } from '../services/apiClient';

type ReviewState = 'idle' | 'requesting' | 'reprocessing' | 'approved';

const reprocessMessages = (role: string, company: string) => [
  `Noted. Calling BS on that phrasing...`,
  `Adjusting your narrative for ${role}...`,
  `Consulting the ghost of Steve Jobs...`,
  `Better. Probably.`,
  `Saving for ${company}...`,
];

export const TailoringReview: React.FC = () => {
  const { id } = useParams();
  const navigate = useNavigate();

  const [job, setJob]                 = useState<ReferenceJob | null>(null);
  const [changes, setChanges]         = useState<ResumeChange[]>([]);
  const [coverLetter, setCoverLetter] = useState<string>('');
  const [loading, setLoading]         = useState(true);
  const [notFound, setNotFound]       = useState(false);
  const [reviewState, setReviewState] = useState<ReviewState>('idle');
  const [changeRequest, setChangeRequest] = useState('');
  const [isRegenerated, setIsRegenerated] = useState(false);
  const [exportStatus, setExportStatus]   = useState<string | null>(null);

  // Resolve resume_id → tailored resume + its job context for the header.
  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    (async () => {
      try {
        const tailored = await apiClient.getResumeById(id);
        if (cancelled) return;
        setCoverLetter(tailored.cover_letter ?? '');

        const [backendJob, evaluation, changeRows] = await Promise.all([
          apiClient.getJob(tailored.job_id),
          apiClient.getEvaluation(tailored.job_id).catch(() => null),
          apiClient.getResumeChanges(id).catch(() => [] as ResumeChange[]),
        ]);
        if (cancelled) return;

        setJob(toReferenceJob(backendJob, evaluation));
        setChanges(changeRows);
        setLoading(false);
      } catch {
        if (cancelled) return;
        setNotFound(true);
        setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [id]);

  const role    = job?.role    ?? 'this role';
  const company = job?.company ?? 'the company';

  // The reference shows a single "rephrase" example. We surface the
  // first non-NULL `tailored_text` from changes (sorted by confidence,
  // lowest-first so the spotlight goes to the riskiest edit) so the
  // 2-pane diff actually reflects real backend output.
  const featuredChange = useMemo(() => {
    if (changes.length === 0) return null;
    const sorted = [...changes].sort(
      (a, b) => (a.confidence ?? 1) - (b.confidence ?? 1),
    );
    return sorted.find(c => c.tailored_text && c.original_text) ?? sorted[0];
  }, [changes]);

  const remainingCount = useMemo(
    () => changes.filter(c => c.review_action == null).length,
    [changes],
  );

  const handleApprove = useCallback(async () => {
    if (!id || !job) return;
    setReviewState('approved');

    try {
      await apiClient.updateTailoredStatus(id, 'approved');
    } catch (err) {
      console.warn('updateTailoredStatus failed:', err);
    }

    try {
      const result = await apiClient.exportToGoogleDocs(job.id);
      if (result.status === 'success' || result.status === 'no_changes') {
        setExportStatus('Sent to Google Drive.');
        if (result.url) window.open(result.url, '_blank', 'noopener,noreferrer');
      } else if (result.status === 'partial') {
        setExportStatus(`Sent with ${result.summary?.skipped ?? '?'} sections skipped.`);
        if (result.url) window.open(result.url, '_blank', 'noopener,noreferrer');
      } else {
        setExportStatus('GDoc export failed. Try again from settings.');
      }
    } catch (err: any) {
      setExportStatus(err?.message ? `Export error: ${err.message}` : 'Export failed.');
    }

    setTimeout(() => navigate('/tracker'), 2500);
  }, [id, job, navigate]);

  const handleRequestChanges = useCallback(() => {
    setReviewState('requesting');
  }, []);

  // Re-tailor: save cover letter, then trigger a fresh tailoring run
  // (the backend treats this as a new run for the same job).
  const handleRetailor = useCallback(async () => {
    if (!job || !changeRequest.trim()) return;
    setReviewState('reprocessing');
    try {
      // Capture the feedback as cover-letter context for now — this lets
      // the next pass have access to the user's stated discontent without
      // requiring a new backend field (we keep per-change feedback chips
      // for granular reject; this flow is a "I want a rewrite" coarse path).
      if (id) {
        const enrichedCover = `${coverLetter}\n\n[Re-tailor note]: ${changeRequest.trim()}`;
        await apiClient.updateCoverLetter(id, enrichedCover);
      }
      await apiClient.tailorResume(job.id);
    } catch (err) {
      console.warn('re-tailor failed:', err);
    }
  }, [job, id, changeRequest, coverLetter]);

  const handleReprocessComplete = useCallback(() => {
    setIsRegenerated(true);
    setChangeRequest('');
    setReviewState('idle');
  }, []);

  const handleCoverLetterBlur = useCallback(async () => {
    if (!id) return;
    try {
      await apiClient.updateCoverLetter(id, coverLetter);
    } catch {
      /* swallow — autosave is best-effort */
    }
  }, [id, coverLetter]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-6 h-6 rounded-full border-2 border-accent/40 border-t-accent animate-spin" />
      </div>
    );
  }

  if (notFound || !job) {
    return (
      <div className="flex-1 p-8 flex items-center justify-center">
        <div className="text-center space-y-3">
          <p className="text-gray-400 font-mono text-sm">Tailored resume not found.</p>
          <button onClick={() => navigate('/')} className="text-accent font-mono text-sm hover:underline">
            ← Back to feed
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 p-8 overflow-y-auto max-w-6xl mx-auto w-full flex flex-col h-full">
      <button
        onClick={() => navigate('/')}
        className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors mb-6 font-mono text-sm shrink-0"
      >
        <ArrowLeft className="w-4 h-4" /> Back to feed
      </button>

      <header className="mb-8 shrink-0 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-sans font-bold tracking-tight text-white mb-2">
            Tailoring Review
          </h1>
          <p className="text-gray-400 font-mono text-sm">
            Reviewing changes for {company} · {role}
            {remainingCount > 0 && (
              <span className="ml-2 text-gray-500">· {remainingCount} unreviewed</span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isRegenerated && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex items-center gap-2 text-semantic-amber bg-semantic-amber/10 px-3 py-1.5 rounded-lg border border-semantic-amber/20"
            >
              <RefreshCw className="w-4 h-4" />
              <span className="font-mono text-sm font-medium">Regenerated</span>
            </motion.div>
          )}
          <div className="flex items-center gap-2 text-semantic-green bg-semantic-green/10 px-3 py-1.5 rounded-lg border border-semantic-green/20">
            <Sparkles className="w-4 h-4" />
            <span className="font-mono text-sm font-medium">AI Tailored</span>
          </div>
        </div>
      </header>

      {/* MatchBrief reference */}
      {((job.strengths?.length ?? 0) > 0 || (job.gaps?.length ?? 0) > 0) && (
        <details className="shrink-0 mb-6 group">
          <summary className="flex items-center gap-2 cursor-pointer list-none font-mono text-xs text-gray-500 uppercase tracking-wider hover:text-gray-300 transition-colors select-none">
            <span className="group-open:hidden">▶</span>
            <span className="hidden group-open:inline">▼</span>
            Your brief — what the AI was optimising for
          </summary>
          <div className="mt-4">
            <MatchBrief strengths={job.strengths} gaps={job.gaps} matchScore={job.matchScore} />
          </div>
        </details>
      )}

      {/* CV diff panes — driven by featuredChange when present, mock copy otherwise */}
      <div className="flex-1 grid grid-cols-2 gap-6 min-h-0 mb-6">
        <section className="flex flex-col border border-white/5 bg-surface rounded-xl overflow-hidden">
          <div className="p-4 border-b border-white/5 bg-surface-hover flex items-center justify-between">
            <h2 className="font-mono text-sm text-gray-400 uppercase tracking-wider">Base CV</h2>
            <span className="text-xs text-gray-500 font-mono">Original</span>
          </div>
          <div className="p-6 overflow-y-auto flex-1 font-sans text-sm text-gray-300 space-y-6">
            {featuredChange?.original_text ? (
              <div>
                <div className="text-[10px] font-mono text-gray-500 uppercase tracking-wider mb-2">
                  {featuredChange.location}
                </div>
                <p className="bg-semantic-red/10 text-semantic-red/90 px-2 py-1.5 rounded line-through decoration-semantic-red/50 leading-relaxed">
                  {featuredChange.original_text}
                </p>
              </div>
            ) : (
              <p className="text-gray-500 italic">No diff available — backend may still be processing.</p>
            )}
          </div>
        </section>

        <section className="flex flex-col border border-accent/20 bg-surface rounded-xl overflow-hidden relative">
          <div className="p-4 border-b border-accent/20 bg-accent/5 flex items-center justify-between">
            <h2 className="font-mono text-sm text-accent uppercase tracking-wider">Tailored CV</h2>
            <span className="text-xs text-accent/70 font-mono">Optimized for JD</span>
          </div>

          {/* Reprocessing overlay */}
          <AnimatePresence>
            {reviewState === 'reprocessing' && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="absolute inset-0 bg-base/80 flex items-center justify-center z-10 backdrop-blur-sm"
              >
                <TypewriterWaitState
                  key={changeRequest}
                  messages={reprocessMessages(role, company)}
                  onComplete={handleReprocessComplete}
                  speed={22}
                  delayBetweenMessages={900}
                />
              </motion.div>
            )}
          </AnimatePresence>

          <div className="p-6 overflow-y-auto flex-1 font-sans text-sm text-gray-300 space-y-6">
            {featuredChange?.tailored_text ? (
              <div>
                <div className="text-[10px] font-mono text-gray-500 uppercase tracking-wider mb-2">
                  {featuredChange.location}
                </div>
                <p className={cn(
                  'px-2 py-1.5 rounded leading-relaxed',
                  isRegenerated
                    ? 'bg-semantic-amber/10 text-semantic-amber/90'
                    : 'bg-semantic-green/10 text-semantic-green/90',
                )}>
                  {featuredChange.tailored_text}
                </p>
                {featuredChange.reason && (
                  <p className="text-xs font-mono text-gray-500 mt-2">
                    <span className="text-accent mr-1">→</span>
                    {featuredChange.reason}
                  </p>
                )}
              </div>
            ) : (
              <p className="text-gray-500 italic">Tailored content will appear here when ready.</p>
            )}
          </div>
        </section>
      </div>

      {/* Cover letter (editable; autosaves on blur via updateCoverLetter) */}
      <section className="shrink-0 border border-white/5 bg-surface rounded-xl overflow-hidden mb-6">
        <div className="p-4 border-b border-white/5 bg-surface-hover flex items-center justify-between">
          <h2 className="font-mono text-sm text-gray-400 uppercase tracking-wider">Cover Letter</h2>
          <span className="text-xs text-gray-500 font-mono">Edits autosave on blur</span>
        </div>
        <textarea
          value={coverLetter}
          onChange={e => setCoverLetter(e.target.value)}
          onBlur={handleCoverLetterBlur}
          placeholder="Auto-generated cover letter will appear here after tailoring."
          rows={8}
          className="w-full bg-transparent p-6 font-sans text-sm text-gray-300 leading-relaxed focus:outline-none resize-none"
        />
      </section>

      {/* Request changes form */}
      <AnimatePresence>
        {reviewState === 'requesting' && (
          <motion.section
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="shrink-0 mb-6 overflow-hidden"
          >
            <div className="border border-semantic-amber/20 bg-semantic-amber/5 rounded-xl p-5 space-y-3">
              <h3 className="font-mono text-sm text-semantic-amber uppercase tracking-wider">What needs changing?</h3>
              <textarea
                autoFocus
                value={changeRequest}
                onChange={e => setChangeRequest(e.target.value)}
                placeholder="Be specific — 'the Zustand section undersells my state management breadth' beats 'make it better.'"
                rows={3}
                className="w-full bg-base border border-white/10 rounded-lg px-4 py-3 text-sm text-gray-200 font-sans placeholder-gray-600 focus:outline-none focus:border-semantic-amber/40 transition-colors resize-none"
              />
              <div className="flex items-center gap-3 justify-end">
                <button
                  onClick={() => setReviewState('idle')}
                  className="px-4 py-2 text-sm font-mono text-gray-400 hover:text-gray-200 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleRetailor}
                  disabled={!changeRequest.trim()}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-semantic-amber/10 border border-semantic-amber/30 text-semantic-amber font-mono text-sm font-medium hover:bg-semantic-amber/20 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <RotateCcw className="w-4 h-4" />
                  Re-tailor
                </button>
              </div>
            </div>
          </motion.section>
        )}
      </AnimatePresence>

      {/* Action bar */}
      <div className="shrink-0 border-t border-white/5 pt-6 flex items-center justify-between gap-6">
        <div className="flex-1 max-w-xl">
          <AnimatePresence mode="wait">
            {reviewState === 'approved' ? (
              <motion.div
                key="success"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex items-center gap-3 text-semantic-green text-base font-sans"
              >
                <CheckCircle2 className="w-5 h-5 shrink-0" />
                <span>{exportStatus ?? 'Approved. Pushing to Google Drive and logging in tracker.'}</span>
              </motion.div>
            ) : reviewState === 'requesting' ? (
              <motion.p
                key="requesting"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-gray-400 font-mono text-sm"
              >
                Describe what's wrong and we'll re-run the tailoring pass.
              </motion.p>
            ) : (
              <motion.p
                key="hype"
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                className="text-gray-400 font-sans italic text-base leading-relaxed"
              >
                "You have shipped production systems. You have debugged at midnight. You have survived bad managers. {company} doesn't know what's coming. Send it."
              </motion.p>
            )}
          </AnimatePresence>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {reviewState === 'idle' && (
            <button
              onClick={handleRequestChanges}
              className={cn(
                'flex items-center gap-2 px-5 py-3.5 rounded-xl border font-mono text-sm transition-colors',
                isRegenerated
                  ? 'border-semantic-amber/20 hover:bg-semantic-amber/5 text-semantic-amber'
                  : 'border-white/10 hover:bg-surface-hover text-gray-300',
              )}
            >
              <RotateCcw className="w-4 h-4" />
              {isRegenerated ? 'Request More Changes' : 'Request Changes'}
            </button>
          )}
          <button
            onClick={handleApprove}
            disabled={reviewState === 'approved' || reviewState === 'reprocessing'}
            className="bg-accent hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed text-[#0d0d0d] font-bold py-3.5 px-8 rounded-xl transition-all flex items-center justify-center gap-3 shadow-lg shadow-accent/20 hover:shadow-accent/40"
          >
            {reviewState === 'approved' ? (
              <>
                <CheckCircle2 className="w-5 h-5" />
                Sent
              </>
            ) : (
              <>
                <Send className="w-5 h-5" />
                Approve & Send
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
