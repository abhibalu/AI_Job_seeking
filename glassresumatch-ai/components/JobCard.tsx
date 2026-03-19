import React, { useState } from 'react';
import { JobWithEvaluation } from '../services/jobService';
import { GlassCard } from './GlassCard';
import { Building2, Briefcase, Play, MoreHorizontal } from 'lucide-react';

interface JobCardProps {
  job: JobWithEvaluation;
  onClick: () => void;
  onEvaluate?: () => void;
  isEvaluating?: boolean;
  onAction?: (jobId: string, cvVersion: 'base' | 'tailored') => void;
}

export const JobCard: React.FC<JobCardProps> = ({ job, onClick, onEvaluate, isEvaluating, onAction }) => {
  const [showActions, setShowActions] = useState(false);
  const evaluation = job.evaluation;

  const isReady = job.tailoring_status === 'ready';
  const cvVersion: 'base' | 'tailored' = isReady ? 'tailored' : 'base';
  const applyButtonLabel = isReady ? 'Apply with tailored CV →' : 'Apply with base CV →';

  const handleDotsClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowActions(prev => !prev);
  };

  const handleApply = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (job.job_url) {
      window.open(job.job_url, '_blank', 'noopener,noreferrer');
    }
    onAction?.(job.id, cvVersion);
    setShowActions(false);
  };

  const getVerdictColor = (verdict: string | null | undefined) => {
    switch (verdict) {
      case 'Strong Match': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'Moderate Match': return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'Weak Match': return 'bg-rose-50 text-rose-700 border-rose-200';
      default: return 'bg-slate-50 text-slate-600 border-slate-200';
    }
  };

  const getActionColor = (action: string | null | undefined) => {
    switch (action) {
      case 'apply': return 'bg-emerald-500';
      case 'tailor': return 'bg-amber-500';
      case 'skip': return 'bg-rose-500';
      default: return 'bg-slate-300';
    }
  };

  const getScoreColor = (score: number | null | undefined) => {
    if (!score) return 'text-slate-400';
    if (score >= 80) return 'text-emerald-600';
    if (score >= 50) return 'text-amber-600';
    return 'text-rose-600';
  };

  const handleEvaluateClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onEvaluate?.();
  };

  return (
    <GlassCard onClick={onClick} hoverEffect={true} className="h-full flex flex-col p-6 group border-slate-200/60">
      {/* ⋯ quick action trigger — always visible at opacity-30, full on hover or touch-toggle */}
      <div className="absolute top-3 right-3 flex items-center gap-1.5 z-10">
        {/* Quick action panel: slides in on card hover (desktop) or when touch-toggled */}
        <div className={`flex items-center transition-all duration-200 ${
          showActions
            ? 'opacity-100 translate-x-0'
            : 'opacity-0 group-hover:opacity-100 translate-x-2 group-hover:translate-x-0'
        }`}>
          <button
            onClick={handleApply}
            className="px-2.5 py-1 bg-slate-900 text-white text-[11px] font-medium rounded-md hover:bg-slate-700 transition-colors whitespace-nowrap shadow-sm"
          >
            {applyButtonLabel}
          </button>
        </div>
        <button
          onClick={handleDotsClick}
          className={`p-0.5 rounded transition-opacity duration-200 ${
            showActions ? 'opacity-100' : 'opacity-30 group-hover:opacity-100'
          }`}
        >
          <MoreHorizontal className="w-4 h-4 text-slate-500" />
        </button>
      </div>

      <div className="flex justify-between items-start mb-4">
        <div className="flex items-center space-x-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-slate-800 to-slate-900 flex items-center justify-center text-white font-bold text-xl shadow-md">
            {(job.company_name || 'U').substring(0, 1)}
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-800 group-hover:text-blue-600 transition-colors">
              {job.title || 'Untitled Position'}
            </h3>
            <div className="flex items-center text-sm text-slate-500">
              <Building2 className="w-3 h-3 mr-1" />
              {job.company_name || 'Unknown Company'}
            </div>
          </div>
        </div>

        {job.isEvaluated && evaluation ? (
          <div className={`px-3 py-1 rounded-full text-xs font-semibold border mr-6 ${getVerdictColor(evaluation.verdict)}`}>
            {evaluation.verdict}
          </div>
        ) : (
          <div className="px-3 py-1 rounded-full text-xs font-semibold border mr-6 bg-slate-100 text-slate-500 border-slate-200">
            Not Evaluated
          </div>
        )}
      </div>

      <div className="mb-4 flex-1">
        {job.isEvaluated && evaluation?.summary ? (
          <p className="text-sm text-slate-600 line-clamp-3 leading-relaxed">
            {evaluation.summary}
          </p>
        ) : (
          <p className="text-sm text-slate-400 italic">
            Click to view details or evaluate this job
          </p>
        )}
      </div>

      <div className="mt-auto pt-4 border-t border-slate-100 flex items-center justify-between">
        {job.isEvaluated && evaluation ? (
          <>
            <div className="flex flex-col">
              <span className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">Match Score</span>
              <span className={`text-2xl font-bold ${getScoreColor(evaluation.job_match_score)}`}>
                {evaluation.job_match_score}%
              </span>
            </div>

            <div className="flex items-center space-x-3">
              {/* Action badge */}
              <div className={`px-3 py-1.5 rounded-lg text-xs font-bold text-white uppercase tracking-wide ${getActionColor(evaluation.recommended_action)}`}>
                {evaluation.recommended_action}
              </div>

              {/* Experience */}
              <div className="flex flex-col items-end">
                <span className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold mb-1">Exp</span>
                <div className="flex items-center text-sm text-slate-700 bg-slate-100 px-2 py-1 rounded-md">
                  <Briefcase className="w-3 h-3 mr-1.5 text-slate-400" />
                  {evaluation.required_exp || 'N/A'}
                </div>
              </div>
            </div>
          </>
        ) : (
          <>
            <div className="flex flex-col">
              <span className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">Status</span>
              <span className="text-sm text-slate-500">Pending Evaluation</span>
            </div>

            <button
              onClick={handleEvaluateClick}
              disabled={isEvaluating}
              className="flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md hover:shadow-lg"
            >
              {isEvaluating ? (
                <>
                  <div className="w-4 h-4 mr-2 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Evaluating...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-1.5" />
                  Evaluate
                </>
              )}
            </button>
          </>
        )}
      </div>

    </GlassCard>
  );
};