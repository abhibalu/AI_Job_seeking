/**
 * JobCard.tsx — OotoCV reference verbatim.
 *
 * Fat 2-column card: left holds role + verdict reason + red flags, right
 * holds verdict badge + strength/gap counts + quick actions. The whole card
 * is a Link to `/job/:id` so the entire surface is clickable except the
 * action buttons, which stopPropagation to keep their handlers.
 */
import React from 'react';
import { motion } from 'motion/react';
import { Link } from 'react-router-dom';
import { Building2, Clock, ExternalLink, FileEdit, MapPin, Skull, Terminal, XCircle } from 'lucide-react';

import { cn } from '../lib/utils';
import type { ReferenceJob, ReferenceVerdict } from '../services/jobAdapter';

const verdictStyles: Record<ReferenceVerdict, string> = {
  TAILOR:         'bg-semantic-green/10 text-semantic-green border-semantic-green/20',
  BORDERLINE:     'bg-semantic-amber/10 text-semantic-amber border-semantic-amber/20',
  SKIP:           'bg-semantic-red/10 text-semantic-red border-semantic-red/20',
  'APPLY DIRECT': 'bg-semantic-slate/10 text-semantic-slate border-semantic-slate/20',
};

const verdictAccentBar: Record<ReferenceVerdict, string> = {
  TAILOR:         'bg-semantic-green/50',
  BORDERLINE:     'bg-semantic-amber/50',
  SKIP:           'bg-semantic-red/50',
  'APPLY DIRECT': 'bg-semantic-slate/50',
};

interface JobCardProps {
  job: ReferenceJob;
  dimmed?: boolean;
  onSkip?: (jobId: string) => void;
  onTailor?: (job: ReferenceJob) => void;
  onApplyDirect?: (job: ReferenceJob) => void;
}

export const JobCard: React.FC<JobCardProps> = ({ job, dimmed, onSkip, onTailor, onApplyDirect }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        'group relative flex items-start gap-6 px-5 py-4 rounded-xl border bg-surface transition-all duration-300',
        'border-white/5 hover:border-white/10 hover:bg-surface-hover',
        dimmed && 'opacity-50 hover:opacity-80 saturate-50'
      )}
    >
      {/* LEFT COLUMN */}
      <div className="flex-1 flex flex-col gap-3 min-w-0 z-10">
        <div>
          <h3 className="font-sans font-semibold text-lg text-white group-hover:text-accent transition-colors">
            {job.role}
          </h3>
          <div className="flex items-center gap-4 mt-2 text-sm text-gray-400 font-mono tracking-tight">
            <span className="flex items-center gap-1.5 truncate">
              <Building2 className="w-3.5 h-3.5 shrink-0" />
              <span className="truncate">{job.company}</span>
            </span>
            {job.location && (
              <span className="flex items-center gap-1.5 shrink-0">
                <MapPin className="w-3.5 h-3.5" />
                {job.location}
              </span>
            )}
            <span className="flex items-center gap-1.5 shrink-0">
              <Clock className="w-3.5 h-3.5" />
              {job.postedAt}
            </span>
          </div>
        </div>

        {/* Verdict reason */}
        <div className="bg-base/50 rounded-lg p-4 border border-white/5 relative overflow-hidden">
          <div className={cn('absolute top-0 left-0 w-1 h-full', verdictAccentBar[job.verdict])} />
          <div className="flex items-start gap-3">
            <Terminal className="w-4 h-4 text-gray-500 mt-0.5 shrink-0" />
            <p className="text-sm text-gray-300 font-mono leading-relaxed">
              {job.verdictReason}
            </p>
          </div>
        </div>

        {/* Red flags — em-dash split, label bold then explanation muted */}
        {job.redFlags.length > 0 && (
          <div className="flex flex-col gap-2">
            {job.redFlags.map((flag, idx) => {
              const [label, ...rest] = flag.split('—');
              const explanation = rest.join('—').trim();
              return (
                <div key={idx} className="flex items-start gap-2 px-3 py-2 rounded-md bg-semantic-red/5 border border-semantic-red/10">
                  <Skull className="w-4 h-4 text-semantic-red/80 shrink-0 mt-0.5" />
                  <div className="text-xs font-mono">
                    <span className="text-semantic-red/90 font-bold">{label.trim()}</span>
                    {explanation && <span className="text-gray-400 ml-2">— {explanation}</span>}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* RIGHT COLUMN */}
      <div className="w-64 shrink-0 flex flex-col items-end justify-between self-stretch gap-4 z-10">
        <div className={cn('px-3 py-1.5 rounded border text-[11px] font-mono font-bold tracking-wider whitespace-nowrap uppercase shadow-sm', verdictStyles[job.verdict])}>
          {job.verdict}
        </div>

        {((job.strengths?.length ?? 0) > 0 || (job.gaps?.length ?? 0) > 0) && (
          <div className="text-xs font-mono text-gray-500 text-right mt-auto mb-2">
            {[
              (job.strengths?.length ?? 0) > 0 ? `${job.strengths!.length} strength${job.strengths!.length !== 1 ? 's' : ''}` : null,
              (job.gaps?.length ?? 0) > 0      ? `${job.gaps!.length} gap${job.gaps!.length !== 1 ? 's' : ''}`              : null,
            ].filter(Boolean).join(' · ')}
          </div>
        )}

        {/* Quick actions inline */}
        <div className={cn('flex items-center gap-2', !((job.strengths?.length ?? 0) > 0 || (job.gaps?.length ?? 0) > 0) && 'mt-auto')}>
          {job.verdict !== 'SKIP' && (
            <button
              onClick={(e) => { e.preventDefault(); e.stopPropagation(); onSkip?.(job.id); }}
              className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-surface border border-white/10 text-xs font-mono text-gray-300 hover:text-white hover:bg-surface-hover transition-colors"
            >
              <XCircle className="w-3.5 h-3.5" />
              Skip
            </button>
          )}

          {job.verdict === 'SKIP' ? (
            <button
              onClick={(e) => { e.preventDefault(); e.stopPropagation(); onTailor?.(job); }}
              className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-surface border border-white/10 text-xs font-mono text-gray-300 hover:text-white hover:bg-surface-hover transition-colors"
            >
              <FileEdit className="w-3.5 h-3.5" />
              Override & Tailor
            </button>
          ) : job.verdict === 'APPLY DIRECT' ? (
            <button
              onClick={(e) => { e.preventDefault(); e.stopPropagation(); onApplyDirect?.(job); }}
              className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-accent text-[#0d0d0d] text-xs font-mono font-bold hover:bg-accent-hover transition-colors"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              Apply Direct
            </button>
          ) : (
            <button
              onClick={(e) => { e.preventDefault(); e.stopPropagation(); onTailor?.(job); }}
              className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-accent text-[#0d0d0d] text-xs font-mono font-bold hover:bg-accent-hover transition-colors"
            >
              <FileEdit className="w-3.5 h-3.5" />
              Tailor & Approve
            </button>
          )}
        </div>
      </div>

      {/* Full-card link — z-0 so buttons capture clicks first */}
      <Link
        to={`/job/${job.id}`}
        className="absolute inset-0 z-0"
        aria-label={`View details for ${job.role} at ${job.company}`}
      />
    </motion.div>
  );
};
