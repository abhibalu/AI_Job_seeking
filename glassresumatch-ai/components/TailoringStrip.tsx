import React, { useState, useCallback, useEffect } from 'react';
import { useSSE } from '../hooks/useSSE';
import { cn } from '../lib/utils';
import { TypewriterWaitState } from './TypewriterWaitState';
import type { Job } from '../types';

interface TailoringStripProps {
  job: Job;
  taskId: string | null;
  onComplete: (jobId: string, resumeId?: string) => void;
  onCancel: () => void;
}

const STAGES = ['queued', 'planning', 'drafting', 'critiquing', 'revising', 'saving'] as const;

const stageMessages: Record<string, string> = {
  queued: 'Starting up…',
  planning: 'Analyzing job requirements…',
  drafting: 'Tailoring your CV…',
  critiquing: 'Reviewing changes…',
  revising: 'Refining edits…',
  saving: 'Saving your tailored CV…',
};

export const TailoringStrip: React.FC<TailoringStripProps> = ({
  job, taskId, onComplete, onCancel,
}) => {
  const [stage, setStage] = useState('queued');
  const [stopping, setStopping] = useState(false);
  const [typewriterDone, setTypewriterDone] = useState(false);

  // Reset typewriter animation whenever stage advances
  useEffect(() => {
    setTypewriterDone(false);
  }, [stage]);

  useSSE(taskId, {
    onProgress: useCallback((event) => {
      const s = (event as any).progress?.stage;
      if (s) setStage(s);
    }, []),
    onRunComplete: useCallback((event) => {
      if (event.status === 'cancelled') return;
      const resumeId = (event as any).progress?.resume_id;
      onComplete(job.id, resumeId);
    }, [job.id, onComplete]),
  });

  const currentStageIndex = STAGES.indexOf(stage as typeof STAGES[number]);
  const message = stageMessages[stage] || 'Processing…';

  const handleStop = () => {
    setStopping(true);
    onCancel();
  };

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 w-[420px] border-t-2 border-accent bg-surface border border-white/10 rounded-sm px-5 py-4">
      {/* Job context + stop button */}
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-mono text-gray-500 truncate max-w-[260px]">
          {job.title}
          {job.company_name && (
            <span className="text-gray-600"> · {job.company_name}</span>
          )}
        </span>
        <button
          onClick={handleStop}
          disabled={stopping}
          className={cn(
            'text-xs font-mono text-gray-600 hover:text-semantic-red-400 transition-colors cursor-pointer flex-shrink-0 ml-4',
            stopping && 'opacity-50 cursor-not-allowed',
          )}
        >
          {stopping ? 'Stopping…' : 'Stop Tailoring'}
        </button>
      </div>

      {/* Pipeline stage dots */}
      <div className="flex items-center gap-2 mb-3">
        {STAGES.map((s, i) => {
          const isPast = i < currentStageIndex;
          const isCurrent = i === currentStageIndex;
          return (
            <div
              key={s}
              className={cn(
                'rounded-full transition-all',
                isCurrent
                  ? 'w-2.5 h-2.5 bg-accent animate-pulse'
                  : isPast
                    ? 'w-1.5 h-1.5 bg-accent'
                    : 'w-1.5 h-1.5 bg-white/15',
              )}
            />
          );
        })}
      </div>

      {/* Stage message with typewriter */}
      <div className="min-h-[24px] flex items-center">
        {typewriterDone ? (
          <span className="font-mono text-sm text-gray-300">{message}</span>
        ) : (
          <TypewriterWaitState
            key={stage}
            messages={[message]}
            onComplete={() => setTypewriterDone(true)}
            speed={20}
            loop={false}
            className="text-sm text-gray-300"
          />
        )}
      </div>
    </div>
  );
};
