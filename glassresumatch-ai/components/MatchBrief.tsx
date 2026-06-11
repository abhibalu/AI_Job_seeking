/**
 * MatchBrief.tsx — OotoCV reference verbatim.
 *
 * Strengths + gaps signal panel. Both `strengths` and `gaps` come from the
 * `ReferenceJob` shape produced by `services/jobAdapter.toReferenceJob`.
 * The gap.strategy field is the load-bearing copy — it's the agent telling
 * the user how to handle each gap.
 */
import React from 'react';

import { cn } from '../lib/utils';
import type { ReferenceGap, ReferenceGapSeverity, ReferenceStrength, ReferenceStrengthType } from '../services/jobAdapter';

const scoreLabel: Record<number, string> = {
  4: 'Strong position',
  3: 'Good position',
  2: 'Fair shot',
  1: 'Uphill battle',
  0: 'Tough ask',
};

const strengthChip: Record<ReferenceStrengthType, string> = {
  'req met':  'bg-semantic-green/10 text-semantic-green border-semantic-green/20',
  'evidence': 'bg-teal-400/10 text-teal-400 border-teal-400/20',
  'signal':   'bg-semantic-slate/10 text-semantic-slate border-semantic-slate/20',
};

const gapChip: Record<ReferenceGapSeverity, string> = {
  'minor':       'bg-semantic-amber/10 text-semantic-amber border-semantic-amber/20',
  'notable':     'bg-orange-400/10 text-orange-400 border-orange-400/20',
  'significant': 'bg-semantic-red/10 text-semantic-red border-semantic-red/20',
};

const strengthBorder: Record<ReferenceStrengthType, string> = {
  'req met':  'border-l-semantic-green/40',
  'evidence': 'border-l-teal-400/40',
  'signal':   'border-l-semantic-slate/40',
};

const gapBorder: Record<ReferenceGapSeverity, string> = {
  'minor':       'border-l-semantic-amber/40',
  'notable':     'border-l-orange-400/40',
  'significant': 'border-l-semantic-red/40',
};

interface MatchBriefProps {
  strengths?: ReferenceStrength[];
  gaps?: ReferenceGap[];
  matchScore?: number;
}

export const MatchBrief: React.FC<MatchBriefProps> = ({ strengths = [], gaps = [], matchScore = 0 }) => {
  const score = Math.max(0, Math.min(4, Math.round(matchScore)));
  const label = scoreLabel[score] ?? 'Unknown';

  return (
    <div className="space-y-6 p-5 rounded-xl border border-white/5 bg-base/40">
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono text-gray-500 uppercase tracking-wider">Your brief</span>
        <span className="text-xs font-mono text-gray-500">
          {strengths.length > 0 && `${strengths.length} strength${strengths.length !== 1 ? 's' : ''}`}
          {strengths.length > 0 && gaps.length > 0 && ' · '}
          {gaps.length > 0 && `${gaps.length} gap${gaps.length !== 1 ? 's' : ''}`}
        </span>
      </div>

      {/* Signal dots */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className={cn(
                'w-2.5 h-2.5 rounded-full transition-colors',
                i < score ? 'bg-accent' : 'bg-white/10'
              )}
            />
          ))}
        </div>
        <span className="text-xs font-mono text-gray-400">{label}</span>
      </div>

      {/* Strengths */}
      {strengths.length > 0 && (
        <div className="space-y-2">
          <span className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">Lead with these</span>
          <div className="space-y-2">
            {strengths.map((s, idx) => (
              <div
                key={idx}
                className={cn(
                  'flex items-start justify-between gap-3 pl-3 pr-3 py-2.5 rounded-r-lg border-l-2 bg-white/[0.02]',
                  strengthBorder[s.type]
                )}
              >
                <span className="text-sm text-gray-300 font-sans leading-snug flex-1">{s.text}</span>
                <span className={cn(
                  'shrink-0 px-2 py-0.5 rounded border text-[10px] font-mono font-semibold whitespace-nowrap',
                  strengthChip[s.type]
                )}>
                  {s.type}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Gaps — strategy line is the most important copy */}
      {gaps.length > 0 && (
        <div className="space-y-2">
          <span className="text-[10px] font-mono text-gray-500 uppercase tracking-wider">Handle these</span>
          <div className="space-y-3">
            {gaps.map((g, idx) => (
              <div
                key={idx}
                className={cn(
                  'flex flex-col gap-1.5 pl-3 pr-3 py-2.5 rounded-r-lg border-l-2 bg-white/[0.02]',
                  gapBorder[g.severity]
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <span className="text-sm text-gray-300 font-sans leading-snug flex-1">{g.text}</span>
                  <span className={cn(
                    'shrink-0 px-2 py-0.5 rounded border text-[10px] font-mono font-semibold whitespace-nowrap',
                    gapChip[g.severity]
                  )}>
                    {g.severity}
                  </span>
                </div>
                <p className="text-xs font-mono text-gray-500 leading-relaxed">
                  <span className="text-accent mr-1">→</span>
                  {g.strategy}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
