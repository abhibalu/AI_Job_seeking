import React from 'react';
import { motion } from 'motion/react';
import { cn } from '../lib/utils';
import type { Evaluation, Gaps } from '../types';

interface MatchBriefProps {
  evaluation: Evaluation;
}

// Map score to signal dots and label
function getSignalInfo(score: number | null) {
  const filled = score != null ? Math.round((score / 100) * 4) : 0;
  let label = 'Unknown';
  if (score != null) {
    if (score >= 80) label = 'Strong position';
    else if (score >= 60) label = 'Solid match';
    else if (score >= 40) label = 'Worth considering';
    else label = 'Uphill battle';
  }
  return { filled, label };
}

function getStrengths(evaluation: Evaluation): Array<{ text: string; chip: string; chipColor: string }> {
  const strengths: Array<{ text: string; chip: string; chipColor: string }> = [];

  if (evaluation.matched_keywords?.length) {
    evaluation.matched_keywords.slice(0, 3).forEach(kw => {
      strengths.push({ text: kw, chip: 'req met', chipColor: 'bg-semantic-green/10 text-semantic-green' });
    });
  }

  if (evaluation.improvement_suggestions?.your_strengths_to_highlight) {
    (evaluation.improvement_suggestions as any).your_strengths_to_highlight?.slice(0, 2).forEach((s: string) => {
      strengths.push({ text: s, chip: 'evidence', chipColor: 'bg-teal-500/10 text-teal-400' });
    });
  }

  if (evaluation.interview_tips?.your_strengths_to_highlight?.length) {
    evaluation.interview_tips.your_strengths_to_highlight.slice(0, 2).forEach(s => {
      if (!strengths.find(x => x.text === s)) {
        strengths.push({ text: s, chip: 'signal', chipColor: 'bg-semantic-slate/10 text-semantic-slate' });
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

export const MatchBrief: React.FC<MatchBriefProps> = ({ evaluation }) => {
  const { filled, label } = getSignalInfo(evaluation.job_match_score);
  const strengths = getStrengths(evaluation);
  const gapItems = getGapItems(evaluation.gaps);

  return (
    <div className="space-y-4 p-6 rounded-xl border border-white/5 bg-surface">
      {/* Section header */}
      <div className="flex items-center justify-between">
        <span className="text-[9px] font-mono uppercase tracking-widest text-gray-500">Your brief</span>
        <span className="text-[10px] font-mono text-gray-600">
          {strengths.length} strengths · {gapItems.length} gaps
        </span>
      </div>

      {/* Signal dots */}
      <div className="flex items-center gap-2">
        <div className="flex gap-1">
          {[0, 1, 2, 3].map(i => (
            <div
              key={i}
              className={cn(
                'w-2 h-2 rounded-full',
                i < filled ? 'bg-semantic-green' : 'bg-white/[0.08]'
              )}
            />
          ))}
        </div>
        <span className="text-[10px] font-mono text-gray-500">{label}</span>
      </div>

      {/* Strengths */}
      {strengths.length > 0 && (
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-gray-500 mb-2">
            Lead with these
          </div>
          <div className="space-y-1.5">
            {strengths.map((s, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.08, duration: 0.3 }}
                className="flex items-start gap-3 px-3 py-2.5 rounded-lg bg-base/50 border-l-2 border-semantic-green/35"
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
      {gapItems.length > 0 && (
        <div>
          <div className="text-[10px] font-mono uppercase tracking-widest text-gray-500 mb-2">
            Handle these
          </div>
          <div className="space-y-1.5">
            {gapItems.map((g, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: (strengths.length + i) * 0.08, duration: 0.3 }}
              >
                <div className="flex items-start gap-3 px-3 py-2.5 rounded-lg bg-base/50 border-l-2 border-semantic-amber/35">
                  <span className={cn(
                    'text-[8px] font-bold uppercase rounded-[2px] px-1.5 py-0.5 flex-shrink-0 mt-0.5',
                    severityChip[g.severity] || severityChip.minor
                  )}>
                    {g.severity}
                  </span>
                  <span className="text-[11px] font-sans text-gray-400 leading-relaxed">{g.text}</span>
                </div>
                {g.strategy && (
                  <div className="text-[9px] font-mono text-gray-600 mt-0.5 pl-0.5">
                    <span className="text-accent">→</span> {g.strategy}
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
