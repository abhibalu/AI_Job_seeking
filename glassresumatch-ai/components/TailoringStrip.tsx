import React from 'react';
import { useNavigate } from 'react-router-dom';
import { TypewriterWaitState } from './TypewriterWaitState';
import { useSSE } from '../hooks/useSSE';
import { cn } from '../lib/utils';
import type { Job } from '../types';

interface TailoringStripProps {
  job: Job;
  taskId: string | null;
  onComplete: (jobId: string) => void;
  onCancel: () => void;
}

const processingMessages = [
  'Reading the job description...',
  'Matching your experience...',
  'Tailoring your CV...',
  'Almost there...',
];

export const TailoringStrip: React.FC<TailoringStripProps> = ({
  job, taskId, onComplete, onCancel,
}) => {
  const navigate = useNavigate();

  useSSE(taskId, {
    onRunComplete: () => {
      onComplete(job.id);
    },
  });

  return (
    <div className="border-t border-white/5 bg-surface px-6 py-3 flex items-center gap-4">
      {/* Job context */}
      <span className="text-accent font-mono text-xs truncate max-w-[120px]">{job.title}</span>
      <span className="text-gray-600 font-mono text-xs">·</span>
      <span className="text-gray-600 font-mono text-xs truncate max-w-[100px]">{job.company_name}</span>

      {/* Divider */}
      <div className="w-px h-4 bg-white/[0.08]" />

      {/* Typewriter */}
      <div className="flex-1 min-w-0">
        <TypewriterWaitState
          key={job.id}
          messages={processingMessages}
          onComplete={() => {}}
          speed={30}
          delayBetweenMessages={1200}
          className="text-[10px]"
        />
      </div>

      {/* Cancel */}
      <button
        onClick={onCancel}
        className="text-xs font-mono text-gray-600 hover:text-gray-400 transition-colors cursor-pointer flex-shrink-0"
      >
        Cancel
      </button>
    </div>
  );
};
