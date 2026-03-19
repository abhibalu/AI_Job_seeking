import React, { useState, useCallback } from 'react';
import { useSSE } from '../hooks/useSSE';
import { cn } from '../lib/utils';
import type { Job } from '../types';

interface TailoringStripProps {
  job: Job;
  taskId: string | null;
  onComplete: (jobId: string, resumeId?: string) => void;
  onCancel: () => void;
}

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

  useSSE(taskId, {
    onProgress: useCallback((event) => {
      const s = (event as any).progress?.stage;
      if (s) setStage(s);
    }, []),
    onRunComplete: useCallback((event) => {
      if (event.status === 'cancelled') {
        // Cancel already handled by onCancel
        return;
      }
      const resumeId = (event as any).progress?.resume_id;
      onComplete(job.id, resumeId);
    }, [job.id, onComplete]),
  });

  const message = stageMessages[stage] || 'Processing…';

  const handleStop = () => {
    setStopping(true);
    onCancel();
  };

  return (
    <div className="border-t border-white/5 bg-surface px-6 py-3 flex items-center gap-4">
      {/* Job context */}
      <span className="text-accent font-mono text-xs truncate max-w-[120px]">{job.title}</span>
      <span className="text-gray-600 font-mono text-xs">·</span>
      <span className="text-gray-600 font-mono text-xs truncate max-w-[100px]">{job.company_name}</span>

      {/* Divider */}
      <div className="w-px h-4 bg-white/[0.08]" />

      {/* Stage message */}
      <div className="flex-1 min-w-0 flex items-center gap-2">
        <div className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse flex-shrink-0" />
        <span className="text-[10px] font-mono text-gray-400 truncate">{message}</span>
      </div>

      {/* Stop button */}
      <button
        onClick={handleStop}
        disabled={stopping}
        className={cn(
          'text-xs font-mono text-gray-600 hover:text-semantic-red-400 transition-colors cursor-pointer flex-shrink-0',
          stopping && 'opacity-50 cursor-not-allowed',
        )}
      >
        {stopping ? 'Stopping…' : 'Stop Tailoring'}
      </button>
    </div>
  );
};
