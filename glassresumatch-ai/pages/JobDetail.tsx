/**
 * JobDetail.tsx — OotoCV reference layout, wired to live backend.
 *
 * Fetches `apiClient.getJob(id)` + `apiClient.getEvaluation(id)` and maps
 * them through `toReferenceJob`. The verdict-conditional section order
 * comes from the reference:
 *   TAILOR / BORDERLINE / APPLY DIRECT → verdict take → red_flags → summary → MatchBrief → action bar
 *   SKIP                               → red_flags + kill_shot lead, JD muted
 *
 * Clicking "Tailor & Approve" calls `apiClient.tailorResume(id)`, hands
 * the task_id back up via `onTailor`, and navigates home so the
 * TailoringStrip is visible while the pipeline runs.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, ExternalLink, FileText, Terminal, XCircle } from 'lucide-react';

import { cn } from '../lib/utils';
import { MatchBrief } from '../components/MatchBrief';
import { apiClient } from '../services/apiClient';
import { toReferenceJob } from '../services/jobAdapter';
import type { ReferenceJob, ReferenceVerdict } from '../services/jobAdapter';

const verdictStyles: Record<ReferenceVerdict, string> = {
  TAILOR:         'bg-semantic-green/10 text-semantic-green border-semantic-green/20',
  BORDERLINE:     'bg-semantic-amber/10 text-semantic-amber border-semantic-amber/20',
  SKIP:           'bg-semantic-red/10 text-semantic-red border-semantic-red/20',
  'APPLY DIRECT': 'bg-semantic-slate/10 text-semantic-slate border-semantic-slate/20',
};

interface JobDetailProps {
  onTailor?: (job: ReferenceJob, taskId: string) => void;
}

export const JobDetail: React.FC<JobDetailProps> = ({ onTailor }) => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [job, setJob] = useState<ReferenceJob | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [loading, setLoading] = useState(true);
  const [tailoring, setTailoring] = useState(false);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setLoading(true);
    setNotFound(false);
    Promise.all([
      apiClient.getJob(id),
      apiClient.getEvaluation(id).catch(() => null),
    ])
      .then(([backendJob, evaluation]) => {
        if (cancelled) return;
        setJob(toReferenceJob(backendJob, evaluation));
        setLoading(false);
      })
      .catch(() => {
        if (cancelled) return;
        setNotFound(true);
        setLoading(false);
      });
    return () => { cancelled = true; };
  }, [id]);

  const handleTailor = useCallback(async () => {
    if (!job) return;
    setTailoring(true);
    try {
      const resp = await apiClient.tailorResume(job.id);
      onTailor?.(job, resp.task_id);
      navigate('/');   // TailoringStrip lives on the feed; let user see it
    } catch (err) {
      setTailoring(false);
      console.warn('tailorResume failed:', err);
    }
  }, [job, navigate, onTailor]);

  const handleSkip = useCallback(() => {
    navigate('/');
  }, [navigate]);

  const handleApplyDirect = useCallback(async () => {
    if (!job) return;
    if (job.originalUrl) {
      window.open(job.originalUrl, '_blank', 'noopener,noreferrer');
    }
    try {
      await apiClient.createApplication(job.id, 'base', {
        jobTitle: job.role,
        companyName: job.company,
      });
    } catch {
      /* swallow — optimistic */
    }
    navigate('/tracker');
  }, [job, navigate]);

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
          <p className="text-gray-400 font-mono text-sm">Job not found. It probably got away.</p>
          <button
            onClick={() => navigate('/')}
            className="text-accent font-mono text-sm hover:underline"
          >
            ← Back to feed
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 p-8 overflow-y-auto max-w-4xl mx-auto w-full">
      <button
        onClick={() => navigate(-1)}
        className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors mb-8 font-mono text-sm"
      >
        <ArrowLeft className="w-4 h-4" /> Back to feed
      </button>

      <header className="mb-10">
        <div className="flex items-start justify-between gap-6">
          <div>
            <h1 className="text-4xl font-sans font-bold tracking-tight text-white mb-2">
              {job.role}
            </h1>
            <div className="flex items-center gap-3 text-lg text-gray-400">
              <span>{job.company}</span>
              {job.location && <><span>•</span><span>{job.location}</span></>}
              <span>•</span>
              <span className="font-mono text-sm">{job.postedAt}</span>
            </div>
          </div>
          <div className={cn('px-4 py-2 rounded-lg border font-mono font-bold text-sm whitespace-nowrap', verdictStyles[job.verdict])}>
            {job.verdict}
          </div>
        </div>
      </header>

      <div className="space-y-8">
        {/* Verdict take — terminal block */}
        <div className="flex items-start gap-3 p-4 rounded-lg bg-base/50 border border-white/5">
          <Terminal className="w-4 h-4 text-accent mt-1 shrink-0" />
          <p className="text-lg font-mono text-gray-200 leading-relaxed">
            {job.verdictReason}
          </p>
        </div>

        {/* Red flags */}
        {job.redFlags.length > 0 && (
          <section className="space-y-3">
            <h2 className="text-sm font-mono text-gray-500 uppercase tracking-wider">Red Flags</h2>
            <div className="flex flex-col gap-2">
              {job.redFlags.map((flag, idx) => {
                const [label, ...rest] = flag.split('—');
                const explanation = rest.join('—').trim();
                return (
                  <div key={idx} className="flex items-start gap-3 p-3 rounded-lg bg-semantic-red/5 border border-semantic-red/10 font-mono text-sm">
                    <span className="mt-0.5">🚩</span>
                    <div>
                      <span className="text-semantic-red/90 font-bold">{label.trim()}</span>
                      {explanation && <span className="text-gray-400 ml-2">— {explanation}</span>}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* JD Summary */}
        {job.summary && (
          <section className="space-y-3">
            <h2 className="text-sm font-mono text-gray-500 uppercase tracking-wider">JD Summary (No Fluff)</h2>
            <p className="text-gray-300 leading-relaxed font-sans">{job.summary}</p>
          </section>
        )}

        {/* MatchBrief */}
        {((job.strengths?.length ?? 0) > 0 || (job.gaps?.length ?? 0) > 0) && (
          <MatchBrief
            strengths={job.strengths}
            gaps={job.gaps}
            matchScore={job.matchScore}
          />
        )}

        {/* Action bar */}
        <div className="pt-8 flex items-center gap-3 border-t border-white/5">
          {job.verdict === 'APPLY DIRECT' ? (
            <button
              onClick={handleApplyDirect}
              className="flex-1 bg-accent hover:bg-accent-hover text-[#0d0d0d] font-bold py-4 px-6 rounded-xl transition-colors flex items-center justify-center gap-2"
            >
              <ExternalLink className="w-5 h-5" />
              Apply Direct
            </button>
          ) : job.verdict !== 'SKIP' ? (
            <button
              onClick={handleTailor}
              disabled={tailoring}
              className={cn(
                'flex-1 font-bold py-4 px-6 rounded-xl transition-colors flex items-center justify-center gap-2',
                tailoring
                  ? 'bg-surface text-gray-500 cursor-not-allowed'
                  : 'bg-accent hover:bg-accent-hover text-[#0d0d0d]',
              )}
            >
              <FileText className="w-5 h-5" />
              {tailoring ? 'Tailoring…' : 'Tailor & Approve'}
            </button>
          ) : (
            // SKIP — Override as primary
            <button
              onClick={handleTailor}
              disabled={tailoring}
              className="flex-1 bg-surface hover:bg-surface-hover border border-white/10 text-gray-200 font-bold py-4 px-6 rounded-xl transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <FileText className="w-5 h-5" />
              {tailoring ? 'Tailoring…' : 'Override & Tailor Anyway'}
            </button>
          )}

          {job.verdict !== 'SKIP' && (
            <button
              onClick={handleSkip}
              className="px-6 py-4 rounded-xl border border-white/10 hover:bg-surface-hover text-gray-300 font-medium transition-colors flex items-center gap-2"
            >
              <XCircle className="w-4 h-4" />
              Skip
            </button>
          )}

          {job.originalUrl && (
            <a
              href={job.originalUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="px-6 py-4 rounded-xl border border-white/10 hover:bg-surface-hover text-gray-300 font-medium transition-colors flex items-center gap-2"
            >
              <ExternalLink className="w-4 h-4" />
              Original JD
            </a>
          )}
        </div>
      </div>
    </div>
  );
};
