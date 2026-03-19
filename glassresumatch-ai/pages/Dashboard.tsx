import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion } from 'motion/react';
import { Terminal, ArrowRight, MoreHorizontal } from 'lucide-react';
import { cn } from '../lib/utils';
import { JobWithEvaluation } from '../services/jobService';
import { EvaluationStats } from '../services/apiClient';

interface DashboardProps {
  jobs: JobWithEvaluation[];
  activeJobs: JobWithEvaluation[];
  actionedJobs: JobWithEvaluation[];
  stats: EvaluationStats | null;
  loading: boolean;
  loadingMore: boolean;
  hasMore: boolean;
  loadMore: () => void;
  selectedJobId: string | null;
  onJobClick: (job: JobWithEvaluation) => void;
  onAction: (jobId: string, cvVersion: 'base' | 'tailored') => void;
  onSkip: (jobId: string) => void;
  verdictFilter: string[];
  onVerdictFilterChange: (verdicts: string[]) => void;
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

function groupJobs(jobs: JobWithEvaluation[]) {
  const tailor: JobWithEvaluation[] = [];
  const apply: JobWithEvaluation[] = [];
  const borderline: JobWithEvaluation[] = [];
  const skip: JobWithEvaluation[] = [];

  for (const job of jobs) {
    const v = getVerdictType(job);
    if (v === 'tailor') tailor.push(job);
    else if (v === 'apply') apply.push(job);
    else if (v === 'borderline') borderline.push(job);
    else skip.push(job);
  }

  // Interleave tailor + apply by score
  const actionRequired = [...tailor, ...apply].sort(
    (a, b) => (b.evaluation?.job_match_score ?? 0) - (a.evaluation?.job_match_score ?? 0)
  );

  return { actionRequired, borderline, skip };
}

// --- Card Components ---

const TailorCard: React.FC<{
  job: JobWithEvaluation;
  selected: boolean;
  onClick: () => void;
  onAction: (cv: 'base' | 'tailored') => void;
  onSkip: () => void;
}> = ({ job, selected, onClick, onAction, onSkip }) => {
  const eval_ = job.evaluation;
  const score = eval_?.job_match_score ?? 0;
  const filled = Math.round((score / 100) * 4);
  const isTailor = getVerdictType(job) === 'tailor';
  const reason = eval_?.wit_line || eval_?.summary || '';
  const topStrength = eval_?.interview_tips?.your_strengths_to_highlight?.[0]
    || eval_?.matched_keywords?.[0] || '';

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        'group relative flex flex-col gap-2 p-[13px_15px] rounded-[9px] border cursor-pointer transition-colors',
        selected
          ? 'border-accent border-l-accent bg-[#141414]'
          : 'border-transparent hover:border-white/[0.12] hover:bg-[#141414]'
      )}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="min-w-0">
          <div className="text-[12px] font-sans font-semibold text-gray-200 truncate">
            {job.title || 'Untitled Role'}
          </div>
          <div className="text-[10px] font-mono text-gray-600 truncate">
            {job.company_name} {job.location && `· ${job.location}`}
          </div>
        </div>
        <MoreHorizontal className="w-3.5 h-3.5 text-gray-600 opacity-30 group-hover:opacity-100 transition-opacity flex-shrink-0" />
      </div>

      {/* Verdict block */}
      <div className={cn(
        'bg-base/80 rounded-[5px] p-[7px_10px] border-l-2',
        isTailor ? 'border-semantic-green/50' : 'border-semantic-amber/50'
      )}>
        <div className="flex items-start gap-2">
          <Terminal className="w-3 h-3 text-gray-600 mt-0.5 flex-shrink-0" />
          <span className="text-[9px] font-mono text-gray-500 leading-relaxed line-clamp-2">
            {reason}
          </span>
        </div>
      </div>

      {/* Signal row (TAILOR only) */}
      {isTailor && (
        <div className="flex items-center gap-2">
          <div className="flex gap-0.5">
            {[0, 1, 2, 3].map(i => (
              <div
                key={i}
                className={cn(
                  'w-1.5 h-1.5 rounded-full',
                  i < filled ? 'bg-semantic-green' : 'bg-white/[0.08]'
                )}
              />
            ))}
          </div>
          {topStrength && (
            <span className="text-[9px] font-mono text-gray-600 truncate">
              Lead with <span className="text-accent">→</span> {topStrength}
            </span>
          )}
        </div>
      )}

      {/* Borderline: deciding factor */}
      {!isTailor && (
        <div className="flex items-center gap-2">
          <span className="text-[8px] font-bold uppercase rounded-[2px] px-1.5 py-0.5 bg-semantic-amber/10 text-semantic-amber">
            deciding factor
          </span>
          <span className="text-[9px] font-mono text-gray-600 truncate">
            {eval_?.gaps?.technical?.[0] || eval_?.gaps?.domain?.[0] || 'Review required'}
          </span>
        </div>
      )}

      {/* Quick actions */}
      <div className="absolute bottom-3 right-3 flex gap-1.5 opacity-0 translate-y-1 group-hover:opacity-100 group-hover:translate-y-0 transition-all duration-300">
        <button
          onClick={(e) => { e.stopPropagation(); onSkip(); }}
          className="text-[9px] font-mono text-gray-600 px-2 py-1 rounded-[5px] border border-white/[0.08] hover:text-gray-400 hover:border-white/15 transition-colors"
        >
          Skip
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onAction(job.tailoring_status === 'ready' ? 'tailored' : 'base'); }}
          className="text-[9px] font-bold px-2 py-1 rounded-[5px] bg-accent text-[#0d0d0d] hover:bg-accent-hover transition-colors"
        >
          {isTailor ? 'Tailor & Approve' : 'Tailor Anyway'}
        </button>
      </div>
    </motion.div>
  );
};

const ApplyDirectCard: React.FC<{
  job: JobWithEvaluation;
  selected: boolean;
  onClick: () => void;
  onAction: () => void;
}> = ({ job, selected, onClick, onAction }) => {
  const take = job.evaluation?.wit_line || job.evaluation?.summary || '';

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        'flex items-center gap-3 p-[10px_15px] rounded-[9px] border cursor-pointer transition-colors',
        selected
          ? 'border-accent bg-[#141414]'
          : 'border-transparent hover:border-white/[0.12] hover:bg-[#141414]'
      )}
      onClick={onClick}
    >
      <div className="flex-1 min-w-0">
        <div className="text-[12px] font-sans font-semibold text-gray-200 truncate">{job.title || 'Untitled'}</div>
        <div className="flex items-center gap-1.5">
          <span className="text-[9px] font-mono text-gray-600 truncate">{job.company_name}</span>
          {take && (
            <span className="text-[9px] font-mono text-gray-600 italic truncate">· {take}</span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        <span className="text-[8px] font-bold uppercase rounded-[2px] px-1.5 py-0.5 bg-semantic-slate/10 text-semantic-slate">
          direct
        </span>
        <button
          onClick={(e) => { e.stopPropagation(); onAction(); }}
          className="text-[9px] font-bold px-2.5 py-1 rounded-[5px] bg-accent text-[#0d0d0d] hover:bg-accent-hover transition-colors whitespace-nowrap"
        >
          Apply <span className="text-[#0d0d0d]">→</span>
        </button>
      </div>
    </motion.div>
  );
};

const SkipCard: React.FC<{
  job: JobWithEvaluation;
  selected: boolean;
  onClick: () => void;
}> = ({ job, selected, onClick }) => {
  const killShot = job.evaluation?.wit_line || job.evaluation?.summary || '';

  return (
    <div
      className={cn(
        'flex items-center gap-2 p-[8px_13px] rounded-[7px] border cursor-pointer transition-all',
        'opacity-[0.38] hover:opacity-[0.65]',
        selected ? 'border-accent' : 'border-transparent'
      )}
      onClick={onClick}
    >
      <div className="w-0.5 h-[14px] bg-semantic-red/40 rounded-full flex-shrink-0" />
      <span className="text-[11px] font-sans text-gray-400 truncate">{job.title || 'Untitled'}</span>
      {killShot && (
        <span className="text-[9px] font-mono text-gray-600 truncate">· {killShot}</span>
      )}
      <span className="ml-auto text-[8px] font-bold uppercase rounded-[2px] px-1.5 py-0.5 bg-semantic-red/10 text-semantic-red flex-shrink-0">
        skip
      </span>
    </div>
  );
};

// --- Section Header ---

const SectionHeader: React.FC<{ label: string; count: number }> = ({ label, count }) => (
  <div className="text-[8px] font-mono text-gray-500 uppercase tracking-[0.08em] px-3 pt-4 pb-1.5">
    {label} · {count}
  </div>
);

// --- Main Dashboard ---

export const Dashboard: React.FC<DashboardProps> = ({
  activeJobs,
  actionedJobs,
  stats,
  loading,
  loadingMore,
  hasMore,
  loadMore,
  selectedJobId,
  onJobClick,
  onAction,
  onSkip,
  verdictFilter,
  onVerdictFilterChange,
}) => {
  const [showSkips, setShowSkips] = useState(false);
  const feedRef = useRef<HTMLDivElement>(null);
  const sentinelRef = useRef<HTMLDivElement>(null);

  // Infinite scroll with ref pattern (per CLAUDE.md)
  const loadMoreRef = useRef(loadMore);
  useEffect(() => { loadMoreRef.current = loadMore; }, [loadMore]);

  useEffect(() => {
    if (!sentinelRef.current || !hasMore) return;
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) loadMoreRef.current(); },
      { root: feedRef.current, threshold: 0.1 }
    );
    obs.observe(sentinelRef.current);
    return () => obs.disconnect();
  }, [hasMore]);

  const { actionRequired, borderline, skip } = groupJobs(activeJobs);

  // Apply verdict filter
  const filteredActionRequired = verdictFilter.length === 0 ? actionRequired
    : actionRequired.filter(j => {
        const v = getVerdictType(j);
        return verdictFilter.includes(v === 'tailor' ? 'TAILOR' : 'APPLY DIRECT');
      });
  const filteredBorderline = verdictFilter.length === 0 || verdictFilter.includes('BORDERLINE') ? borderline : [];
  const filteredSkip = verdictFilter.length === 0 || verdictFilter.includes('SKIP') ? skip : [];

  const verdictPills: Array<{ label: string; key: string; count: number; color: string }> = [
    { label: 'TAILOR', key: 'TAILOR', count: stats?.by_action?.tailor ?? 0, color: 'text-semantic-green bg-semantic-green/10 border-semantic-green/20' },
    { label: 'APPLY DIRECT', key: 'APPLY DIRECT', count: stats?.by_action?.apply ?? 0, color: 'text-semantic-slate bg-semantic-slate/10 border-semantic-slate/20' },
    { label: 'BORDERLINE', key: 'BORDERLINE', count: borderline.length, color: 'text-semantic-amber bg-semantic-amber/10 border-semantic-amber/20' },
    { label: 'SKIP', key: 'SKIP', count: stats?.by_action?.skip ?? 0, color: 'text-semantic-red bg-semantic-red/10 border-semantic-red/20' },
  ];

  const toggleVerdict = (key: string) => {
    if (verdictFilter.includes(key)) {
      onVerdictFilterChange(verdictFilter.filter(v => v !== key));
    } else {
      onVerdictFilterChange([...verdictFilter, key]);
    }
  };

  const renderCard = useCallback((job: JobWithEvaluation, dimmed = false) => {
    const v = getVerdictType(job);
    const wrapper = (children: React.ReactNode) => (
      <div key={job.id} className={cn(dimmed && 'opacity-30')}>
        {children}
      </div>
    );

    if (v === 'apply') {
      return wrapper(
        <ApplyDirectCard
          job={job}
          selected={selectedJobId === job.id}
          onClick={() => onJobClick(job)}
          onAction={() => onAction(job.id, job.tailoring_status === 'ready' ? 'tailored' : 'base')}
        />
      );
    }

    if (v === 'skip') {
      return wrapper(
        <SkipCard
          job={job}
          selected={selectedJobId === job.id}
          onClick={() => onJobClick(job)}
        />
      );
    }

    // tailor or borderline
    return wrapper(
      <TailorCard
        job={job}
        selected={selectedJobId === job.id}
        onClick={() => onJobClick(job)}
        onAction={(cv) => onAction(job.id, cv)}
        onSkip={() => onSkip(job.id)}
      />
    );
  }, [selectedJobId, onJobClick, onAction, onSkip]);

  return (
    <div className="w-80 flex-shrink-0 border-r border-white/5 flex flex-col h-full bg-base">
      {/* Feed Header */}
      <div className="sticky top-0 z-10 bg-base border-b border-white/5 px-4 py-3">
        {/* Top row */}
        <div className="flex items-center gap-2 mb-2">
          <div className="w-2 h-2 rounded-full bg-semantic-green animate-pulse" />
          <span className="text-[10px] font-mono text-gray-500">Today's run</span>
        </div>

        {/* Verdict filter pills */}
        <div className="flex flex-wrap gap-1.5">
          {verdictPills.map(pill => {
            const active = verdictFilter.includes(pill.key);
            return (
              <button
                key={pill.key}
                onClick={() => toggleVerdict(pill.key)}
                className={cn(
                  'text-[9px] font-mono font-bold px-2 py-0.5 rounded-md border transition-colors cursor-pointer',
                  active ? pill.color : 'text-gray-600 bg-transparent border-white/[0.06] hover:border-white/10'
                )}
              >
                {pill.label} {pill.count > 0 && pill.count}
              </button>
            );
          })}
        </div>
      </div>

      {/* Feed body */}
      <div ref={feedRef} className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-5 h-5 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
          </div>
        ) : activeJobs.length === 0 ? (
          <div className="text-center py-16 px-4">
            <p className="text-[11px] font-mono text-gray-600">
              No jobs yet. That changes today.
            </p>
          </div>
        ) : (
          <>
            {/* Action Required */}
            {filteredActionRequired.length > 0 && (
              <>
                <SectionHeader label="Action required" count={filteredActionRequired.length} />
                <div className="space-y-0.5">
                  {filteredActionRequired.map(job => renderCard(job))}
                </div>
              </>
            )}

            {/* Borderline */}
            {filteredBorderline.length > 0 && (
              <>
                <SectionHeader label="Your call" count={filteredBorderline.length} />
                <div className="space-y-0.5">
                  {filteredBorderline.map(job => renderCard(job))}
                </div>
              </>
            )}

            {/* Skip - collapsed */}
            {filteredSkip.length > 0 && (
              <>
                {!showSkips ? (
                  <button
                    onClick={() => setShowSkips(true)}
                    className="w-full text-center py-2 text-[9px] font-mono text-gray-600 hover:text-gray-400 transition-colors cursor-pointer"
                  >
                    {filteredSkip.length} hard passes hidden — show them?
                  </button>
                ) : (
                  <>
                    <SectionHeader label="Hard passes" count={filteredSkip.length} />
                    <div className="space-y-0.5">
                      {filteredSkip.map(job => renderCard(job))}
                    </div>
                  </>
                )}
              </>
            )}

            {/* Actioned - dimmed */}
            {actionedJobs.length > 0 && (
              <>
                <SectionHeader label="Done" count={actionedJobs.length} />
                <div className="space-y-0.5">
                  {actionedJobs.map(job => renderCard(job, true))}
                </div>
              </>
            )}

            {/* Infinite scroll sentinel */}
            {hasMore && (
              <div ref={sentinelRef} className="py-4 flex justify-center">
                {loadingMore && (
                  <div className="w-4 h-4 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
