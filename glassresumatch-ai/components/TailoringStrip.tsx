/**
 * TailoringStrip.tsx — OotoCV reference visual + real SSE wiring.
 *
 * The reference's TailoringStrip is purely cosmetic (mock messages with a
 * fake completion timer). The live version drives the same visual from
 * the existing `useSSE` hook + `cancelTask` so progress is real and
 * cancellable.
 *
 * Behavior:
 *   - Single-line typewriter over a stage-aware message map.
 *   - `key={taskId ?? job.id}` on TypewriterWaitState forces a fresh
 *     instance per job/task so message rotation restarts cleanly.
 *   - "cancel" button calls apiClient.cancelTask(taskId) and waits.
 *   - On run_complete with status!='cancelled', forwards resume_id from
 *     progress payload to onComplete for direct navigation to review.
 */
import React, { useCallback, useState } from 'react';
import { Loader2 } from 'lucide-react';

import { useSSE } from '../hooks/useSSE';
import { TypewriterWaitState } from './TypewriterWaitState';
import { apiClient } from '../services/apiClient';
import type { ReferenceJob } from '../services/jobAdapter';

interface TailoringStripProps {
  job: ReferenceJob;
  taskId: string | null;
  onComplete: (resumeId?: string) => void;
  onCancel: () => void;
}

const tailoringMessages = (role: string, company: string) => [
  `Reading ${company}'s job description... (already in pain)`,
  `Counting buzzwords... 17. A new record.`,
  `Identifying actual requirements vs. founder's wishlist...`,
  `Quietly judging their Glassdoor reviews...`,
  `Tailoring your narrative for ${role}... nearly there`,
  `Sending good vibes... (this part is free)`,
];

const stageMessages: Record<string, string> = {
  queued:     'Queued — waiting for an agent slot…',
  planning:   'Planning changes…',
  drafting:   'Tailoring your CV…',
  critiquing: 'Reviewing changes…',
  revising:   'Refining edits…',
  saving:     'Saving your tailored CV…',
};

export const TailoringStrip: React.FC<TailoringStripProps> = ({ job, taskId, onComplete, onCancel }) => {
  const [stage, setStage] = useState<string | null>(null);
  const [resumeId, setResumeId] = useState<string | undefined>(undefined);
  const [cancelling, setCancelling] = useState(false);

  useSSE(taskId, {
    onProgress: (event) => {
      const p = event.progress;
      if (p?.stage) setStage(p.stage);
      if (p?.resume_id) setResumeId(p.resume_id);
    },
    onRunComplete: (event) => {
      if (event.status === 'cancelled') {
        onCancel();
        return;
      }
      const rid = event.progress?.resume_id ?? resumeId;
      onComplete(rid);
    },
  });

  const handleCancel = useCallback(async () => {
    if (!taskId || cancelling) return;
    setCancelling(true);
    try {
      await apiClient.cancelTask(taskId);
    } catch {
      // Even on a network error, surface as cancel — the worker checks
      // status at node boundaries and will exit either way.
    } finally {
      onCancel();
    }
  }, [taskId, cancelling, onCancel]);

  // Live (stage-aware) message overrides the rotating typewriter set.
  const liveMessage = stage ? stageMessages[stage] : null;

  return (
    <div className="border-t border-white/5 bg-surface px-6 py-3 flex items-center gap-4">
      {/* Left: job context */}
      <div className="shrink-0 text-xs font-mono text-gray-500">
        <span className="text-accent">{job.role}</span>
        <span className="mx-1.5">·</span>
        <span>{job.company}</span>
      </div>

      <div className="w-px h-4 bg-white/10 shrink-0" />

      {/* Typewriter line */}
      <div className="flex-1 min-w-0">
        {liveMessage ? (
          <div className="text-xs font-mono text-gray-300">
            <span className="text-accent mr-2">→</span>
            {liveMessage}
          </div>
        ) : (
          <TypewriterWaitState
            key={taskId ?? job.id}
            messages={tailoringMessages(job.role, job.company)}
            speed={25}
            delayBetweenMessages={1200}
            compact
          />
        )}
      </div>

      {/* Cancel */}
      <button
        onClick={handleCancel}
        disabled={cancelling}
        className="shrink-0 text-xs font-mono text-gray-500 hover:text-gray-300 transition-colors flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-wait"
      >
        {cancelling && <Loader2 className="w-3 h-3 animate-spin" />}
        {cancelling ? 'Cancelling…' : 'cancel'}
      </button>
    </div>
  );
};
