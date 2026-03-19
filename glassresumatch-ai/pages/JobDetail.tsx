import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ExternalLink, Building2, Clock, Users, DollarSign, Mail, ChevronDown } from 'lucide-react';
import { motion } from 'motion/react';
import { cn } from '../lib/utils';
import { MatchBrief } from '../components/MatchBrief';
import { JobWithEvaluation } from '../services/jobService';
import { apiClient } from '../services/apiClient';
import type { Evaluation, ResumeChange, ParseResult } from '../types';
import { formatTimeAgo } from '../utils/format';

interface JobDetailProps {
  job: JobWithEvaluation;
  onTailorStart: (jobId: string) => void;
  onAction: (jobId: string, cvVersion: 'base' | 'tailored') => void;
  onSkip: (jobId: string) => void;
}

type VerdictType = 'tailor' | 'apply' | 'borderline' | 'skip';

function getVerdictType(job: JobWithEvaluation): VerdictType {
  const action = job.evaluation?.recommended_action;
  if (action === 'apply') return 'apply';
  if (action === 'skip') return 'skip';
  if (action === 'tailor') {
    const score = job.evaluation?.job_match_score ?? 0;
    return score >= 50 ? 'tailor' : 'borderline';
  }
  return 'borderline';
}

const verdictColors: Record<VerdictType, string> = {
  tailor: 'border-l-semantic-green',
  borderline: 'border-l-semantic-amber',
  apply: 'border-l-semantic-slate',
  skip: 'border-l-semantic-red',
};

const verdictBadge: Record<VerdictType, { label: string; color: string }> = {
  tailor: { label: 'TAILOR', color: 'bg-semantic-green/10 text-semantic-green' },
  borderline: { label: 'BORDERLINE', color: 'bg-semantic-amber/10 text-semantic-amber' },
  apply: { label: 'APPLY DIRECT', color: 'bg-semantic-slate/10 text-semantic-slate' },
  skip: { label: 'SKIP', color: 'bg-semantic-red/10 text-semantic-red' },
};

// --- Verdict Typewriter ---
const seenVerdicts = new Set<string>();

const VerdictTypewriter: React.FC<{ text: string; jobId: string }> = ({ text, jobId }) => {
  const [displayed, setDisplayed] = useState('');
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (seenVerdicts.has(jobId)) {
      setDisplayed(text);
      setDone(true);
      return;
    }
    setDisplayed('');
    setDone(false);
    let i = 0;
    const timer = setInterval(() => {
      i++;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) {
        clearInterval(timer);
        setDone(true);
        seenVerdicts.add(jobId);
      }
    }, 30);
    return () => clearInterval(timer);
  }, [text, jobId]);

  return (
    <span className="text-[11px] font-mono text-gray-400 leading-relaxed">
      {displayed}
      {!done && (
        <motion.span
          animate={{ opacity: [1, 0] }}
          transition={{ repeat: Infinity, duration: 0.8 }}
          className="inline-block w-[6px] h-[13px] bg-gray-400 ml-0.5 align-middle"
        />
      )}
    </span>
  );
};

// --- Parse Result section (The Job) ---
const JobSection: React.FC<{ evaluation: Evaluation; parsedJd: ParseResult | null; muted?: boolean }> = ({
  evaluation, parsedJd, muted,
}) => {
  const technicalGaps = evaluation.gaps?.technical || [];

  return (
    <div className={cn('space-y-4 p-6 rounded-xl border border-white/5 bg-surface', muted && 'opacity-50')}>
      <div className="text-[8px] font-mono text-gray-500 uppercase tracking-[0.08em]">
        The job (no fluff)
      </div>
      <div className="grid grid-cols-2 gap-6">
        {/* How to strengthen your CV */}
        <div>
          <div className="text-[8px] font-mono text-gray-500 uppercase tracking-[0.08em] mb-2.5">
            How to strengthen your CV
          </div>
          {evaluation.improvement_suggestions?.resume_edits?.slice(0, 5).map((edit, i) => (
            <div key={i} className="flex gap-1.5 mb-1.5">
              <div className="w-[3px] h-[3px] rounded-full bg-gray-600 mt-[5px] flex-shrink-0" />
              <span className="text-[11px] font-sans text-gray-500 leading-relaxed">{edit.suggestion}</span>
            </div>
          ))}
        </div>

        {/* What they actually need */}
        <div>
          <div className="text-[8px] font-mono text-gray-500 uppercase tracking-[0.08em] mb-2.5">
            What they actually need
          </div>
          {parsedJd?.must_haves?.slice(0, 4).map((item, i) => (
            <div key={i} className="flex gap-1.5 mb-1.5">
              <div className="w-[3px] h-[3px] rounded-full bg-gray-600 mt-[5px] flex-shrink-0" />
              <span className="text-[11px] font-sans text-gray-500 leading-relaxed">
                <span className="text-semantic-green font-medium">Must: </span>{item}
              </span>
            </div>
          ))}
          {parsedJd?.nice_to_haves?.slice(0, 3).map((item, i) => (
            <div key={`nice-${i}`} className="flex gap-1.5 mb-1.5">
              <div className="w-[3px] h-[3px] rounded-full bg-gray-600 mt-[5px] flex-shrink-0" />
              <span className="text-[11px] font-sans text-gray-500 leading-relaxed">
                Nice: {item}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Gaps to watch */}
      {technicalGaps.length > 0 && (
        <div className="space-y-2 pt-2 border-t border-white/5">
          <div className="text-[8px] font-mono text-semantic-amber uppercase tracking-[0.08em]">Gaps to watch</div>
          {technicalGaps.map((gap, i) => {
            const parts = gap.split('—');
            return (
              <div key={i} className="flex items-start gap-2 p-[8px_10px] bg-semantic-amber/[0.03] border border-semantic-amber/[0.08] rounded-[6px]">
                <div className="w-0.5 h-[14px] bg-semantic-amber/40 rounded-full flex-shrink-0 mt-0.5" />
                <div>
                  <span className="text-[10px] text-semantic-amber font-bold">{parts[0]}</span>
                  {parts[1] && <span className="text-[10px] text-gray-600"> — {parts[1]}</span>}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

// --- CV Diff ---
const CVDiff: React.FC<{ changes: ResumeChange[]; loading?: boolean; error?: string | null }> = ({ changes, loading, error }) => {
  if (loading) {
    return (
      <div className="space-y-3 p-6 rounded-xl border border-white/5 bg-surface">
        <div className="text-[8px] font-mono text-gray-500 uppercase tracking-[0.08em]">What we changed in your CV</div>
        <div className="text-[10px] font-mono text-gray-600 animate-pulse">Loading changes…</div>
      </div>
    );
  }
  if (error) {
    return (
      <div className="space-y-3 p-6 rounded-xl border border-white/5 bg-surface">
        <div className="text-[8px] font-mono text-gray-500 uppercase tracking-[0.08em]">What we changed in your CV</div>
        <div className="text-[10px] font-mono text-semantic-red/70">Couldn't load changes</div>
      </div>
    );
  }
  if (changes.length === 0) return null;

  return (
    <div className="space-y-3 p-6 rounded-xl border border-white/5 bg-surface">
      <div className="text-[8px] font-mono text-gray-500 uppercase tracking-[0.08em]">What we changed in your CV</div>
      <div className="bg-base/80 border border-white/[0.08] rounded-[7px] p-[12px_14px] space-y-3">
        {changes.slice(0, 6).map((change, i) => (
          <div key={change.id} className={cn('flex gap-2.5 pb-2.5', i < changes.length - 1 && 'border-b border-white/5')}>
            <span className="text-[8px] font-mono text-gray-600 uppercase w-[52px] flex-shrink-0 mt-0.5">
              {change.location}
            </span>
            <div className="min-w-0">
              {change.original_text && (
                <div className="text-[9px] font-sans text-gray-600 line-through mb-0.5">{change.original_text}</div>
              )}
              {change.tailored_text && (
                <div className="text-[9px] font-sans text-gray-400">{change.tailored_text}</div>
              )}
              {change.reason && (
                <div className="text-[8px] font-mono text-accent/70 mt-0.5">→ {change.reason}</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

// --- Collapsible ---
const Collapsible: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-t border-white/5">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between py-3 text-[9px] font-mono text-gray-500 uppercase tracking-[0.08em] hover:text-gray-400 cursor-pointer"
      >
        {label}
        <ChevronDown className={cn('w-3 h-3 transition-transform', open && 'rotate-180')} />
      </button>
      {open && <div className="pb-4">{children}</div>}
    </div>
  );
};

// --- Main JobDetail ---
export const JobDetail: React.FC<JobDetailProps> = ({ job, onTailorStart, onAction, onSkip }) => {
  const navigate = useNavigate();
  const eval_ = job.evaluation;
  const verdict = getVerdictType(job);
  const [parsedJd, setParsedJd] = useState<ParseResult | null>(null);
  const [changes, setChanges] = useState<ResumeChange[]>([]);
  const [changesLoading, setChangesLoading] = useState(false);
  const [changesError, setChangesError] = useState<string | null>(null);
  const [actionInFlight, setActionInFlight] = useState<string | null>(null);

  // Fetch parsed JD and changes
  useEffect(() => {
    setParsedJd(null);
    setChanges([]);
    setChangesLoading(false);
    setChangesError(null);
    if (!job.id) return;

    apiClient.getParsedJD(job.id).then(setParsedJd).catch(() => {});

    if (job.tailoring_status === 'ready') {
      setChangesLoading(true);
      apiClient.getTailoredVersions(job.id).then(versions => {
        if (versions.length > 0) {
          return apiClient.getResumeChanges(versions[0].id).then(setChanges);
        }
      }).catch(() => {
        setChangesError('Failed to load changes');
      }).finally(() => {
        setChangesLoading(false);
      });
    }
  }, [job.id, job.tailoring_status]);

  if (!eval_) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-[11px] font-mono text-gray-600">Not yet evaluated</p>
      </div>
    );
  }

  const reason = eval_.wit_line || eval_.summary || '';
  const badge = verdictBadge[verdict];
  const score = eval_.job_match_score ?? 0;
  const filled = Math.round((score / 100) * 4);

  // Tags from evaluation
  const tags: string[] = [];
  if (eval_.required_exp) tags.push(eval_.required_exp);
  if (parsedJd?.domain) tags.push(parsedJd.domain);
  if (parsedJd?.seniority) tags.push(parsedJd.seniority);

  const handleTailor = () => {
    if (job.tailoring_status === 'ready') {
      apiClient.getTailoredVersions(job.id).then(versions => {
        if (versions.length > 0) navigate(`/tailoring/${versions[0].id}`);
      });
      return;
    }
    setActionInFlight('tailor');
    onTailorStart(job.id);
    // Don't clear actionInFlight — navigation will unmount this component
  };

  const handleApplyDirect = () => {
    setActionInFlight('apply');
    onAction(job.id, job.tailoring_status === 'ready' ? 'tailored' : 'base');
    // Parent opens new tab — no await possible, clear after brief delay
    setTimeout(() => setActionInFlight(null), 1500);
  };

  return (
    <div className="h-full flex flex-col">
      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {/* Hero */}
        <div>
          {/* Company row */}
          <div className="flex items-center gap-2 mb-2">
            <div className="w-6 h-6 rounded-[5px] bg-surface-hover flex items-center justify-center">
              <Building2 className="w-3.5 h-3.5 text-gray-500" />
            </div>
            <span className="text-[11px] font-sans text-gray-400">{job.company_name}</span>
            {job.location && (
              <>
                <span className="text-gray-600">·</span>
                <span className="text-[11px] font-sans text-gray-500">{job.location}</span>
              </>
            )}
          </div>

          {/* Role title */}
          <h1 className="text-[22px] font-sans font-bold text-gray-100 tracking-[-0.3px] mb-2">
            {job.title || 'Untitled Role'}
          </h1>

          {/* Tags */}
          {tags.length > 0 && (
            <div className="flex gap-1.5 flex-wrap mb-4">
              {tags.map((tag, i) => (
                <span key={i} className="text-[9px] text-gray-600 bg-surface/60 border border-white/[0.07] rounded-[3px] px-1.5 py-0.5">
                  {tag}
                </span>
              ))}
            </div>
          )}

          {/* Metadata row */}
          {(() => {
            const metaItems: React.ReactNode[] = [];
            const freshness = formatTimeAgo(job.posted_at);
            if (freshness) metaItems.push(<span key="posted" className="flex items-center gap-1"><Clock className="w-3 h-3" />{freshness}</span>);
            if (job.applicants_count && job.applicants_count > 0) metaItems.push(<span key="applicants" className="flex items-center gap-1"><Users className="w-3 h-3" />{job.applicants_count} applicants</span>);
            if (job.salary_info) metaItems.push(<span key="salary" className="flex items-center gap-1"><DollarSign className="w-3 h-3" />{job.salary_info}</span>);
            if (eval_.recruiter_email) metaItems.push(<a key="recruiter" href={`mailto:${eval_.recruiter_email}`} className="flex items-center gap-1 hover:text-gray-400"><Mail className="w-3 h-3" />{eval_.recruiter_email}</a>);
            return metaItems.length > 0 ? (
              <div className="flex items-center gap-3 text-[10px] font-mono text-gray-500 mb-3">
                {metaItems.map((item, i) => (
                  <React.Fragment key={i}>
                    {i > 0 && <span className="text-gray-700">·</span>}
                    {item}
                  </React.Fragment>
                ))}
              </div>
            ) : null;
          })()}

          {/* Verdict block */}
          <div className={cn(
            'bg-base/80 rounded-[8px] border border-white/[0.08] border-l-[3px] p-[12px_14px]',
            verdictColors[verdict]
          )}>
            <div className="flex items-center gap-2 mb-1.5">
              <span className={cn('text-[8px] font-bold uppercase rounded-[2px] px-1.5 py-0.5', badge.color)}>
                {badge.label}
              </span>
              {(verdict === 'tailor' || verdict === 'borderline') && (
                <div className="flex gap-0.5 ml-1">
                  {[0, 1, 2, 3].map(i => (
                    <div key={i} className={cn('w-1.5 h-1.5 rounded-full', i < filled ? 'bg-semantic-green' : 'bg-white/[0.08]')} />
                  ))}
                </div>
              )}
            </div>
            {reason && <VerdictTypewriter text={reason} jobId={job.id} />}
            {eval_.summary && eval_.summary !== reason && (
              <div className="text-[9px] font-mono text-gray-500 mt-1.5">
                <span className="text-accent">→</span> {eval_.summary}
              </div>
            )}
          </div>
        </div>

        {/* Verdict-conditional sections */}
        {verdict === 'tailor' && (
          <>
            <MatchBrief evaluation={eval_} />
            <JobSection evaluation={eval_} parsedJd={parsedJd} />
            <CVDiff changes={changes} loading={changesLoading} error={changesError} />
          </>
        )}

        {verdict === 'borderline' && (
          <>
            {/* Deciding Factor - prominent */}
            <div className="p-6 rounded-xl border border-semantic-amber/20 bg-semantic-amber/[0.03]">
              <div className="text-[8px] font-mono text-semantic-amber uppercase tracking-[0.08em] mb-2">Deciding factor</div>
              <div className="text-[12px] font-sans text-gray-300">
                {eval_.gaps?.technical?.[0] || eval_.gaps?.domain?.[0] || 'This one could go either way.'}
              </div>
            </div>
            <MatchBrief evaluation={eval_} />
            <JobSection evaluation={eval_} parsedJd={parsedJd} />
          </>
        )}

        {verdict === 'apply' && (
          <>
            <MatchBrief evaluation={eval_} />
            <JobSection evaluation={eval_} parsedJd={parsedJd} />
            <CVDiff changes={changes} loading={changesLoading} error={changesError} />
          </>
        )}

        {verdict === 'skip' && (
          <>
            {/* Kill Shot - prominent */}
            <div className="p-6 rounded-xl border border-semantic-red/20 bg-semantic-red/[0.03]">
              <div className="text-[8px] font-mono text-semantic-red uppercase tracking-[0.08em] mb-2">Kill shot</div>
              <div className="text-[12px] font-sans text-gray-300">
                {eval_.wit_line || eval_.summary || 'Hard pass.'}
              </div>
            </div>
            <JobSection evaluation={eval_} parsedJd={parsedJd} muted />
          </>
        )}

        {/* Layer 3 — Collapsible deep-dive sections */}
        {verdict !== 'skip' && (
          <div className="mt-2">
            {/* Interview Prep */}
            {(eval_.interview_tips?.high_priority_topics?.length || eval_.interview_tips?.questions_to_ask?.length) && (
              <Collapsible label="Interview Prep">
                {eval_.interview_tips?.high_priority_topics && eval_.interview_tips.high_priority_topics.length > 0 && (
                  <div className="mb-3">
                    <div className="text-[8px] font-mono text-gray-500 uppercase tracking-[0.08em] mb-2">High priority topics</div>
                    <div className="space-y-2">
                      {eval_.interview_tips.high_priority_topics.map((t, i) => (
                        <div key={i} className="p-[8px_10px] border border-white/[0.07] rounded-[6px]">
                          <div className="text-[11px] font-sans text-gray-300 font-medium">{t.topic}</div>
                          <div className="text-[10px] font-sans text-gray-500 mt-0.5">Why: {t.why}</div>
                          <div className="text-[10px] font-sans text-gray-500 mt-0.5">Prep: {t.prep}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {eval_.interview_tips?.questions_to_ask && eval_.interview_tips.questions_to_ask.length > 0 && (
                  <div>
                    <div className="text-[8px] font-mono text-gray-500 uppercase tracking-[0.08em] mb-2">Questions to ask</div>
                    <div className="space-y-1">
                      {eval_.interview_tips.questions_to_ask.map((q, i) => (
                        <div key={i} className="flex gap-1.5">
                          <div className="w-[3px] h-[3px] rounded-full bg-gray-600 mt-[5px] flex-shrink-0" />
                          <span className="text-[11px] font-sans text-gray-400 leading-relaxed">{q}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </Collapsible>
            )}

            {/* ATS Keywords */}
            {parsedJd?.ats_keywords && parsedJd.ats_keywords.length > 0 && (verdict === 'tailor' || verdict === 'borderline') && (
              <Collapsible label="ATS Keywords">
                <div className="flex flex-wrap gap-1.5">
                  {parsedJd.ats_keywords.map((kw, i) => (
                    <span key={i} className="text-[9px] font-mono text-gray-500 bg-surface/60 border border-white/[0.07] rounded-[3px] px-1.5 py-0.5">
                      {kw}
                    </span>
                  ))}
                </div>
              </Collapsible>
            )}

            {/* Company */}
            {job.applicants_count != null && job.applicants_count > 0 && (
              <Collapsible label="Company">
                <div className="text-[11px] font-sans text-gray-400">
                  <span className="text-[8px] font-mono text-gray-500 uppercase tracking-[0.08em]">Applicants: </span>
                  {job.applicants_count}
                </div>
              </Collapsible>
            )}
          </div>
        )}
      </div>

      {/* Sticky CTA footer */}
      <div className="flex-shrink-0 border-t border-white/[0.08] bg-base px-6 py-3 flex items-center gap-2">
        <div className="flex-1" />

        {/* Skip button — hidden for borderline (has its own contextual skip) */}
        {verdict !== 'borderline' && (
          <button
            onClick={() => onSkip(job.id)}
            disabled={!!actionInFlight}
            className={cn(
              'text-[9px] font-mono text-gray-600 px-3 py-1.5 border border-white/[0.08] rounded-[6px] hover:text-gray-400 transition-colors cursor-pointer',
              actionInFlight && 'opacity-50 cursor-not-allowed',
            )}
          >
            Skip
          </button>
        )}

        {/* Original JD */}
        {job.job_url && (
          <a
            href={job.job_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[9px] font-mono text-gray-600 px-3 py-1.5 border border-white/[0.08] rounded-[6px] hover:text-gray-400 transition-colors flex items-center gap-1"
          >
            Original JD <ExternalLink className="w-3 h-3" />
          </a>
        )}

        {/* Primary CTA */}
        {verdict === 'tailor' && (
          <button
            onClick={handleTailor}
            disabled={!!actionInFlight}
            className={cn(
              'bg-accent text-[#0d0d0d] text-[10px] font-bold px-[18px] py-2.5 rounded-[7px] hover:bg-accent-hover transition-colors cursor-pointer',
              actionInFlight && 'opacity-50 cursor-not-allowed',
            )}
          >
            {actionInFlight === 'tailor' ? 'Tailoring…' : job.tailoring_status === 'ready' ? 'Review & Send →' : 'Tailor CV →'}
          </button>
        )}

        {verdict === 'borderline' && (
          <div className="flex gap-2">
            <button
              onClick={handleTailor}
              disabled={!!actionInFlight}
              className={cn(
                'bg-accent text-[#0d0d0d] text-[10px] font-bold px-4 py-2.5 rounded-[7px] hover:bg-accent-hover transition-colors cursor-pointer',
                actionInFlight && 'opacity-50 cursor-not-allowed',
              )}
            >
              {actionInFlight === 'tailor' ? 'Tailoring…' : 'Tailor CV →'}
            </button>
            <button
              onClick={() => onSkip(job.id)}
              disabled={!!actionInFlight}
              className={cn(
                'text-[10px] font-bold text-gray-400 px-4 py-2.5 border border-white/[0.08] rounded-[7px] hover:text-gray-300 transition-colors cursor-pointer',
                actionInFlight && 'opacity-50 cursor-not-allowed',
              )}
            >
              Skip This One
            </button>
          </div>
        )}

        {verdict === 'apply' && (
          <button
            onClick={handleApplyDirect}
            disabled={!!actionInFlight}
            className={cn(
              'bg-accent text-[#0d0d0d] text-[10px] font-bold px-[18px] py-2.5 rounded-[7px] hover:bg-accent-hover transition-colors cursor-pointer',
              actionInFlight && 'opacity-50 cursor-not-allowed',
            )}
          >
            <span>{actionInFlight === 'apply' ? 'Applying…' : 'Apply Direct →'}</span>
            <span className="block text-[8px] font-normal opacity-70">Opens posting in new tab</span>
          </button>
        )}

        {verdict === 'skip' && (
          <button
            onClick={handleTailor}
            disabled={!!actionInFlight}
            className={cn(
              'text-[10px] font-mono text-gray-600 px-4 py-2.5 border border-white/[0.08] rounded-[7px] hover:text-gray-400 transition-colors cursor-pointer',
              actionInFlight && 'opacity-50 cursor-not-allowed',
            )}
          >
            {actionInFlight === 'tailor' ? 'Tailoring…' : 'Override & Tailor'}
          </button>
        )}
      </div>
    </div>
  );
};
