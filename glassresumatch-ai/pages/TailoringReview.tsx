import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'motion/react';
import confetti from 'canvas-confetti';
import { Check, X, RotateCcw } from 'lucide-react';
import { cn } from '../lib/utils';
import { apiClient } from '../services/apiClient';
import type { ResumeChange, TailoredResume } from '../types';
import { Toast } from '../components/Toast';

const feedbackChips = ['Too formal', 'Not accurate', 'Other'];

interface ChangeCardProps {
  change: ResumeChange;
  onAction: (changeId: string, action: 'accept' | 'reject' | 'keep_original') => void;
}

const ChangeCard: React.FC<ChangeCardProps> = ({ change, onAction }) => {
  const [showFeedback, setShowFeedback] = useState(false);
  const isLowConfidence = (change.confidence ?? 1) < 0.6;

  return (
    <div className={cn(
      'flex gap-2.5 p-[10px_14px] rounded-[8px] bg-surface border border-white/[0.06] mb-3',
      'border-l-2',
      change.review_action === 'accept' ? 'border-l-semantic-green/50' :
      change.review_action === 'reject' ? 'border-l-semantic-red/50' :
      change.review_action === 'keep_original' ? 'border-l-gray-500/50' :
      isLowConfidence ? 'border-l-semantic-amber/50' : 'border-l-semantic-green/50'
    )}>
      {/* Section label */}
      <span className="text-[8px] font-mono text-gray-600 uppercase w-[56px] flex-shrink-0 mt-1">
        {change.location}
      </span>

      <div className="flex-1 min-w-0">
        {/* Original */}
        {change.original_text && (
          <div className="text-[10px] font-sans text-gray-600 line-through mb-1">{change.original_text}</div>
        )}
        {/* Tailored */}
        {change.tailored_text && (
          <div className="text-[10px] font-sans text-gray-400">{change.tailored_text}</div>
        )}
        {/* Reason */}
        {change.reason && (
          <div className="text-[8px] font-mono text-accent/70 mt-1">→ {change.reason}</div>
        )}
        {/* Confidence indicator */}
        {isLowConfidence && !change.review_action && (
          <div className="text-[8px] font-mono text-semantic-amber mt-1">review suggested</div>
        )}

        {/* Feedback chips (on reject) */}
        {showFeedback && (
          <div className="flex gap-1.5 mt-2">
            {feedbackChips.map(chip => (
              <button
                key={chip}
                onClick={() => {
                  setShowFeedback(false);
                  onAction(change.id, 'reject');
                }}
                className="text-[8px] font-mono text-gray-500 px-2 py-1 border border-white/[0.08] rounded-[4px] hover:text-gray-300 hover:border-white/15 transition-colors cursor-pointer"
              >
                {chip}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex gap-1 flex-shrink-0 mt-0.5">
        {change.review_action ? (
          <span className={cn(
            'text-[8px] font-mono px-2 py-1 rounded-[4px]',
            change.review_action === 'accept' ? 'text-semantic-green bg-semantic-green/5' :
            change.review_action === 'reject' ? 'text-semantic-red bg-semantic-red/5' :
            'text-gray-500 bg-white/5'
          )}>
            {change.review_action === 'accept' ? 'Accepted' :
             change.review_action === 'reject' ? 'Rejected' : 'Kept original'}
          </span>
        ) : (
          <>
            <button
              onClick={() => onAction(change.id, 'accept')}
              className="text-semantic-green text-[9px] font-mono px-1.5 py-1 border border-semantic-green/20 rounded-[4px] hover:bg-semantic-green/5 transition-colors cursor-pointer"
              title="Accept"
            >
              <Check className="w-3 h-3" />
            </button>
            <button
              onClick={() => setShowFeedback(true)}
              className="text-semantic-red text-[9px] font-mono px-1.5 py-1 border border-semantic-red/20 rounded-[4px] hover:bg-semantic-red/5 transition-colors cursor-pointer"
              title="Reject"
            >
              <X className="w-3 h-3" />
            </button>
            <button
              onClick={() => onAction(change.id, 'keep_original')}
              className="text-gray-500 text-[9px] font-mono px-1.5 py-1 border border-white/[0.08] rounded-[4px] hover:text-gray-300 transition-colors cursor-pointer"
              title="Keep original"
            >
              <RotateCcw className="w-3 h-3" />
            </button>
          </>
        )}
      </div>
    </div>
  );
};

export const TailoringReview: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [resume, setResume] = useState<TailoredResume | null>(null);
  const [changes, setChanges] = useState<ResumeChange[]>([]);
  const [coverLetter, setCoverLetter] = useState('');
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{ message: string; type: 'error' | 'success' } | null>(null);
  const [approving, setApproving] = useState(false);
  const approveRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);

    // Load resume by its own ID (not job_id) and its changes
    Promise.all([
      apiClient.getResumeById(id),
      apiClient.getResumeChanges(id).catch(() => []),
    ]).then(([resumeData, ch]) => {
      if (resumeData) {
        setResume(resumeData);
        setCoverLetter(resumeData.cover_letter || '');
      }
      setChanges(ch.sort((a, b) => (a.confidence ?? 1) - (b.confidence ?? 1)));
      setLoading(false);
    }).catch(() => {
      setLoading(false);
    });
  }, [id]);

  const handleChangeAction = useCallback(async (changeId: string, action: 'accept' | 'reject' | 'keep_original') => {
    if (!id) return;
    // Optimistic update
    setChanges(prev => prev.map(c =>
      c.id === changeId ? { ...c, review_action: action } : c
    ));
    try {
      await apiClient.applyChangeAction(id, changeId, action);
    } catch {
      // Rollback
      setChanges(prev => prev.map(c =>
        c.id === changeId ? { ...c, review_action: null } : c
      ));
      setToast({ message: 'Failed to save change. Try again.', type: 'error' });
    }
  }, [id]);

  const handleBulkAccept = useCallback(async () => {
    if (!id) return;
    try {
      await apiClient.applyBulkChangeAction(id, 'accept', 'remaining');
      setChanges(prev => prev.map(c =>
        c.review_action === null ? { ...c, review_action: 'accept' } : c
      ));
    } catch {
      setToast({ message: 'Bulk accept failed.', type: 'error' });
    }
  }, [id]);

  const handleApprove = useCallback(async () => {
    if (!id || !resume || approving) return;
    setApproving(true);
    try {
      await apiClient.updateTailoredStatus(id, 'approved');

      // Export to Google Docs
      try {
        const result = await apiClient.exportToGoogleDocs(resume.job_id);
        if (result.url) {
          window.open(result.url, '_blank');
        }
      } catch {
        // Non-fatal — approve succeeded, GDoc export is best-effort
        setToast({ message: 'Approved, but Google Docs export failed.', type: 'error' });
      }

      // Record application in tracker
      try {
        await apiClient.createApplication(resume.job_id, 'tailored', {
          jobTitle: resume.content?.fullName ? undefined : undefined,
          resumeId: id,
        });
      } catch {
        // Non-fatal — approve + export succeeded, tracking is best-effort
      }

      // Confetti + button hype
      if (approveRef.current) {
        const rect = approveRef.current.getBoundingClientRect();
        confetti({
          particleCount: 80,
          spread: 60,
          origin: {
            x: (rect.left + rect.width / 2) / window.innerWidth,
            y: (rect.top + rect.height / 2) / window.innerHeight,
          },
          colors: ['#fbbf24', '#4ade80', '#f87171'],
          ticks: 40,
        });
      }

      setTimeout(() => navigate('/'), 600);
    } catch {
      setToast({ message: 'Approval failed. Try again.', type: 'error' });
      setApproving(false);
    }
  }, [id, resume, approving, navigate]);

  const handleCoverLetterBlur = useCallback(async () => {
    if (!id) return;
    try {
      await apiClient.updateCoverLetter(id, coverLetter);
    } catch {
      setToast({ message: 'Failed to save cover letter.', type: 'error' });
    }
  }, [id, coverLetter]);

  const accepted = changes.filter(c => c.review_action === 'accept').length;
  const rejected = changes.filter(c => c.review_action === 'reject').length;
  const pending = changes.filter(c => c.review_action === null).length;

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="w-5 h-5 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full">
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto p-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-xl font-sans font-bold text-gray-100 mb-1">
              Tailoring Review
            </h1>
            <div className="text-[10px] font-mono text-gray-500">
              {changes.length} changes · {resume?.cover_letter ? 'Cover letter included' : 'No cover letter'}
            </div>
          </div>

          {/* Changes */}
          <div className="mb-8">
            {changes.map(change => (
              <ChangeCard key={change.id} change={change} onAction={handleChangeAction} />
            ))}
          </div>

          {/* Cover Letter */}
          {(resume?.cover_letter || coverLetter) && (
            <div className="mb-8">
              <div className="text-[8px] font-mono text-gray-500 uppercase tracking-[0.08em] mb-3">Cover letter</div>
              <textarea
                value={coverLetter}
                onChange={(e) => setCoverLetter(e.target.value)}
                onBlur={handleCoverLetterBlur}
                className="w-full bg-surface border border-white/[0.06] rounded-xl p-4 text-[11px] font-sans text-gray-300 leading-relaxed resize-none focus:outline-none focus:border-white/15 min-h-[200px]"
              />
            </div>
          )}
        </div>
      </div>

      {/* Sticky approve footer */}
      <div className="flex-shrink-0 border-t border-white/[0.08] bg-base flex items-center gap-3 px-8 py-3">
        <div className="flex-1 flex items-center gap-3 text-[10px] font-mono">
          <span className="text-semantic-green">{accepted} accepted</span>
          <span className="text-gray-500">·</span>
          <span className="text-gray-500">{pending} pending</span>
          <span className="text-gray-500">·</span>
          <span className="text-semantic-red">{rejected} rejected</span>
        </div>

        {pending > 0 && (
          <button
            onClick={handleBulkAccept}
            className="text-[9px] font-mono text-gray-400 px-3 py-1.5 border border-white/[0.08] rounded-[6px] hover:text-gray-200 transition-colors cursor-pointer"
          >
            Accept all remaining →
          </button>
        )}

        <button
          onClick={() => navigate('/')}
          className="text-[9px] font-mono text-gray-600 px-3 py-1.5 border border-white/[0.08] rounded-[6px] hover:text-gray-400 transition-colors cursor-pointer"
        >
          Skip
        </button>

        <button
          ref={approveRef}
          onClick={handleApprove}
          disabled={approving}
          className={cn(
            'bg-accent text-[#0d0d0d] text-[10px] font-bold px-[18px] py-2.5 rounded-[7px] hover:bg-accent-hover transition-all active:scale-95 cursor-pointer',
            approving && 'opacity-50 cursor-not-allowed',
          )}
        >
          {approving ? 'Sending…' : 'Approve & Send →'}
        </button>
      </div>

      {toast && (
        <Toast message={toast.message} type={toast.type} onDismiss={() => setToast(null)} />
      )}
    </div>
  );
};
