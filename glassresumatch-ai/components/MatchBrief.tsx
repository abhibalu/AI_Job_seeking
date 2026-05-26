import React, { useState } from 'react';
import { motion } from 'motion/react';
import { cn } from '../lib/utils';
import type { Evaluation, Gaps } from '../types';

interface MatchBriefProps {
  evaluation: Evaluation;
}

function getStrengths(evaluation: Evaluation): Array<{ text: string; chip: string; chipColor: string; borderColor: string }> {
  const strengths: Array<{ text: string; chip: string; chipColor: string; borderColor: string }> = [];

  if (evaluation.matched_keywords?.length) {
    evaluation.matched_keywords.slice(0, 3).forEach(kw => {
      strengths.push({ text: kw, chip: 'req met', chipColor: 'bg-semantic-green/10 text-semantic-green', borderColor: 'border-semantic-green/35' });
    });
  }

  if (evaluation.improvement_suggestions?.your_strengths_to_highlight) {
    (evaluation.improvement_suggestions as any).your_strengths_to_highlight?.slice(0, 2).forEach((s: string) => {
      strengths.push({ text: s, chip: 'evidence', chipColor: 'bg-teal-500/10 text-teal-400', borderColor: 'border-teal-400/35' });
    });
  }

  if (evaluation.interview_tips?.your_strengths_to_highlight?.length) {
    evaluation.interview_tips.your_strengths_to_highlight.slice(0, 2).forEach(s => {
      if (!strengths.find(x => x.text === s)) {
        strengths.push({ text: s, chip: 'signal', chipColor: 'bg-semantic-slate/10 text-semantic-slate', borderColor: 'border-teal-400/35' });
      }
    });
  }

  return strengths.slice(0, 5);
}

function getGapItems(gaps: Gaps | null): Array<{ text: string; severity: string; strategy?: string }> {
  if (!gaps) return [];
  const items: Array<{ text: string; severity: string; strategy?: string }> = [];

  gaps.technical?.forEach(g => items.push({ text: g, severity: 'notable' }));
  gaps.domain?.forEach(g => items.push({ text: g, severity: 'minor' }));
  gaps.soft_skills?.forEach(g => items.push({ text: g, severity: 'minor' }));

  return items.slice(0, 5);
}

const severityChip: Record<string, string> = {
  minor: 'bg-semantic-amber/10 text-semantic-amber',
  notable: 'bg-orange-500/10 text-orange-400',
  significant: 'bg-semantic-red/10 text-semantic-red',
};

const DEFAULT_VISIBLE = 3;

export const MatchBrief: React.FC<MatchBriefProps> = ({ evaluation }) => {
  const [expanded, setExpanded] = useState(false);
  const strengths = getStrengths(evaluation);
  const gapItems = getGapItems(evaluation.gaps);

  const visibleStrengths = expanded ? strengths : strengths.slice(0, DEFAULT_VISIBLE);
  const visibleGaps = expanded ? gapItems : gapItems.slice(0, DEFAULT_VISIBLE);
  const hiddenCount = Math.max(0, strengths.length - DEFAULT_VISIBLE) + Math.max(0, gapItems.length - DEFAULT_VISIBLE);

  return (
    <div className="space-y-4 p-6 rounded-xl border border-white/5 bg-surface">
      {/* Section header */}
      <div className="flex items-center justify-between">
        <span className="text-[9px] font-mono uppercase tracking-widest text-gray-500">Your brief</span>
        <span className="text-[10px] font-mono text-gray-600">
          {strengths.length} strengths · {gapItems.length} gaps
        </span>
      </div>

      {/* Strengths */}
      {visibleStrengths.length > 0 && (
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-gray-500 mb-2">
            Lead with these
          </div>
          <div className="space-y-1.5">
            {visibleStrengths.map((s, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.08, duration: 0.3 }}
                className={cn('flex items-start gap-3 px-3 py-2.5 rounded-lg bg-base/50 border-l-2', s.borderColor)}
              >
                <span className={cn(
                  'text-[8px] font-bold uppercase rounded-[2px] px-1.5 py-0.5 flex-shrink-0 mt-0.5',
                  s.chipColor
                )}>
                  {s.chip}
                </span>
                <span className="text-[11px] font-sans text-gray-400 leading-relaxed">{s.text}</span>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* Gaps */}
      {visibleGaps.length > 0 && (
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-gray-500 mb-2">
            Handle these
          </div>
          <div className="space-y-1.5">
            {visibleGaps.map((g, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: (visibleStrengths.length + i) * 0.08, duration: 0.3 }}
              >
                <div className={cn(
                  'flex items-start gap-3 px-3 py-2.5 rounded-lg bg-base/50',
                  g.severity === 'notable' ? 'border-l-[3px] border-orange-400/50' : 'border-l-2 border-semantic-amber/25',
                )}>
                  <span className={cn(
                    'text-[8px] font-bold uppercase rounded-[2px] px-1.5 py-0.5 flex-shrink-0 mt-0.5',
                    severityChip[g.severity] || severityChip.minor
                  )}>
                    {g.severity}
                  </span>
                  <div className="min-w-0">
                    <span className="text-[11px] font-sans text-gray-400 leading-relaxed">{g.text}</span>
                    {g.strategy && (
                      <div className="text-[10px] font-mono text-gray-400 mt-1">
                        <span className="text-accent">→</span> {g.strategy}
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* Expand toggle */}
      {hiddenCount > 0 && !expanded && (() => {
        const hiddenStrengths = Math.max(0, strengths.length - DEFAULT_VISIBLE);
        const hiddenGaps = Math.max(0, gapItems.length - DEFAULT_VISIBLE);
        const parts: string[] = [];
        if (hiddenStrengths > 0) parts.push(`${hiddenStrengths} strength${hiddenStrengths > 1 ? 's' : ''}`);
        if (hiddenGaps > 0) parts.push(`${hiddenGaps} gap${hiddenGaps > 1 ? 's' : ''}`);
        return (
          <motion.button
            onClick={() => setExpanded(true)}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="group flex items-center gap-1.5 text-[9px] font-mono text-gray-500 mt-2 px-3 py-1.5 rounded-md border border-dashed border-white/8 hover:border-accent/30 hover:text-accent transition-colors duration-200 cursor-pointer"
          >
            <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-white/5 group-hover:bg-accent/10 text-[8px] font-bold transition-colors duration-200">
              +{hiddenCount}
            </span>
            {parts.join(', ')}
          </motion.button>
        );
      })()}
    </div>
  );
};
