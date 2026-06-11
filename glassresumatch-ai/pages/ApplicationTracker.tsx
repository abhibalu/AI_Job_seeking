/**
 * ApplicationTracker.tsx — OotoCV reference layout, wired to /api/applications.
 *
 * Backend `Application` carries lowercase statuses (`applied | replied |
 * interview | rejected | ghosting | offer`); the reference uses
 * title-case. We render the backend value capitalised at the edge.
 *
 * `ghost_commentary` and `days_since_update` come from the server (Cache-
 * Control: no-store; see ADR-0023-adjacent R5). The two expandable
 * states (Interview prep, Ghosting follow-up) use the reference visuals
 * verbatim — both are local-only (no backend writes).
 */
import React, { useCallback, useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import {
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  ExternalLink,
  Ghost,
  Mail,
  Send,
  XCircle,
} from 'lucide-react';

import { cn } from '../lib/utils';
import { apiClient } from '../services/apiClient';
import type { Application, ApplicationStatus } from '../services/apiClient';

// Title-case display labels, keyed by lowercase backend value.
const statusLabel: Record<ApplicationStatus, string> = {
  applied:   'Applied',
  ghosting:  'Ghosting',
  replied:   'Replied',
  interview: 'Interview',
  rejected:  'Rejected',
  offer:     'Offer',
};

const statusStyles: Record<ApplicationStatus, { icon: React.ElementType; class: string }> = {
  applied:   { icon: Clock,        class: 'text-gray-400 bg-white/5 border-white/10' },
  ghosting:  { icon: Ghost,        class: 'text-semantic-slate bg-semantic-slate/10 border-semantic-slate/20' },
  replied:   { icon: Mail,         class: 'text-semantic-amber bg-semantic-amber/10 border-semantic-amber/20' },
  interview: { icon: CheckCircle2, class: 'text-accent bg-accent/10 border-accent/20' },
  rejected:  { icon: XCircle,      class: 'text-semantic-red bg-semantic-red/10 border-semantic-red/20' },
  // 'offer' uses the green palette with a pulse hint via animate-pulse-slow.
  offer:     { icon: CheckCircle2, class: 'text-semantic-green bg-semantic-green/10 border-semantic-green/20 animate-pulse-slow' },
};

// Client fallback when the backend response predates server-computed ghost_commentary.
function fallbackCommentary(appliedAt: string, status: ApplicationStatus): string {
  if (status === 'offer')     return "Don't ruin it.";
  if (status === 'interview') return 'They actually replied. Prep.';
  if (status === 'rejected')  return "They don't deserve you.";
  const days = Math.floor((Date.now() - new Date(appliedAt).getTime()) / 86400000);
  if (days <= 3)  return 'Probably just busy.';
  if (days <= 7)  return 'Still nothing. Rude, but fine.';
  if (days <= 14) return "At this point we're assuming they lost it.";
  return "They don't deserve you.";
}

// ── Expansion: Interview prep ────────────────────────────────────────────────

const InterviewExpanded: React.FC<{ app: Application }> = ({ app }) => {
  const [prepared, setPrepared] = useState(false);
  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      className="overflow-hidden"
    >
      <div className="mt-4 pt-4 border-t border-accent/10 space-y-4">
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: 'Re-read the JD',        sub: 'Look for exact phrases you can echo back.' },
            { label: 'Prepare one story',     sub: 'STAR format. Keep it under 2 minutes. Seriously.' },
            { label: 'Ask one good question', sub: '"What does success look like in 6 months?" Always works.' },
          ].map((tip, i) => (
            <div key={i} className="p-3 rounded-lg border border-accent/10 bg-accent/5 space-y-1">
              <p className="text-xs font-mono text-accent font-semibold">{tip.label}</p>
              <p className="text-xs text-gray-400 font-sans leading-relaxed">{tip.sub}</p>
            </div>
          ))}
        </div>
        <div className="flex items-center gap-3 justify-end">
          {app.job_id && (
            <a
              href={`/job/${app.job_id}`}
              className="flex items-center gap-1.5 text-xs font-mono text-gray-400 hover:text-white transition-colors"
            >
              <BookOpen className="w-3.5 h-3.5" />
              Re-read JD
            </a>
          )}
          <button
            onClick={() => setPrepared(true)}
            disabled={prepared}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-mono font-medium transition-colors',
              prepared
                ? 'bg-semantic-green/10 text-semantic-green border border-semantic-green/20 cursor-default'
                : 'bg-accent/10 border border-accent/20 text-accent hover:bg-accent/20',
            )}
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            {prepared ? 'Marked ready' : 'Mark as prepared'}
          </button>
        </div>
      </div>
    </motion.div>
  );
};

// ── Expansion: Ghosting follow-up ────────────────────────────────────────────

const GhostingExpanded: React.FC<{ app: Application; onWriteOff: () => void }> = ({ app, onWriteOff }) => {
  const [showTemplate, setShowTemplate] = useState(false);
  const [sent, setSent] = useState(false);

  const role = app.job_title ?? 'this role';
  const sinceLabel = typeof app.days_since_update === 'number'
    ? `${app.days_since_update} days ago`
    : 'some time ago';

  const followUpTemplate = `Hi [hiring manager name],

I wanted to follow up on my application for the ${role} role I submitted ${sinceLabel}. I'm still very interested in the position and would love to chat if there's an opportunity.

No pressure — just wanted to make sure this didn't get lost in the shuffle.

Best,
[Your name]`;

  const past14 = (app.days_since_update ?? 0) >= 14;

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      className="overflow-hidden"
    >
      <div className="mt-4 pt-4 border-t border-semantic-slate/10 space-y-3">
        {!showTemplate ? (
          <div className="flex items-center gap-3">
            <p className="text-xs font-mono text-gray-500 flex-1">
              {past14
                ? '14 days is the industry write-off point. One nudge, then move on.'
                : '7 days is early. One follow-up is professional. Two is desperate.'}
            </p>
            <button
              onClick={() => setShowTemplate(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-semantic-slate/10 border border-semantic-slate/20 text-semantic-slate text-xs font-mono font-medium hover:bg-semantic-slate/20 transition-colors"
            >
              <Mail className="w-3.5 h-3.5" />
              Write a follow-up
            </button>
            {past14 && (
              <button
                onClick={onWriteOff}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-semantic-red/5 border border-semantic-red/10 text-semantic-red text-xs font-mono font-medium hover:bg-semantic-red/10 transition-colors"
              >
                <XCircle className="w-3.5 h-3.5" />
                Write them off
              </button>
            )}
          </div>
        ) : sent ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-2 text-semantic-green text-xs font-mono py-2"
          >
            <CheckCircle2 className="w-4 h-4" />
            Follow-up sent. Ball's in their court now.
          </motion.div>
        ) : (
          <div className="space-y-3">
            <pre className="text-xs font-mono text-gray-300 bg-base/50 border border-white/5 rounded-lg p-4 whitespace-pre-wrap leading-relaxed">
              {followUpTemplate}
            </pre>
            <div className="flex items-center justify-end gap-3">
              <button
                onClick={() => setShowTemplate(false)}
                className="text-xs font-mono text-gray-500 hover:text-gray-300 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  try { await navigator.clipboard.writeText(followUpTemplate); } catch { /* swallow */ }
                  setSent(true);
                }}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-semantic-slate/10 border border-semantic-slate/20 text-semantic-slate text-xs font-mono font-medium hover:bg-semantic-slate/20 transition-colors"
              >
                <Send className="w-3.5 h-3.5" />
                Copy & mark sent
              </button>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
};

// ── Main ─────────────────────────────────────────────────────────────────────

export const ApplicationTracker: React.FC = () => {
  const [apps, setApps] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    apiClient.getApplications()
      .then(data => { if (!cancelled) { setApps(data); setLoading(false); } })
      .catch(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const toggleExpand = useCallback((id: string) => {
    setExpandedId(prev => (prev === id ? null : id));
  }, []);

  const writeOff = useCallback(async (id: string) => {
    // Optimistic remove + persist as 'rejected' (operator-friendly default).
    const prev = apps;
    setApps(p => p.filter(a => a.id !== id));
    try {
      await apiClient.updateApplicationStatus(id, 'rejected');
    } catch {
      setApps(prev);  // roll back
    }
  }, [apps]);

  const hasExpandable = (app: Application) =>
    app.status === 'interview' || app.status === 'ghosting';

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-6 h-6 rounded-full border-2 border-accent/40 border-t-accent animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex-1 p-8 overflow-y-auto max-w-5xl mx-auto w-full">
      <header className="mb-10 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-sans font-bold tracking-tight text-white mb-2">Tracker</h1>
          <p className="text-gray-400 font-mono text-sm">
            {apps.length} application{apps.length !== 1 ? 's' : ''} tracked.
          </p>
        </div>
        <div className="flex items-center gap-2 text-semantic-green bg-semantic-green/5 px-3 py-1.5 rounded-lg border border-semantic-green/10">
          <div className="w-2 h-2 rounded-full bg-semantic-green animate-pulse" />
          <span className="font-mono text-xs font-medium">Live</span>
        </div>
      </header>

      <div className="space-y-3">
        {apps.map((app, idx) => {
          const StatusIcon = statusStyles[app.status].icon;
          const isExpanded = expandedId === app.id;
          const expandable = hasExpandable(app);
          const commentary = app.ghost_commentary ?? fallbackCommentary(app.applied_at, app.status);
          const appliedAtLabel = new Date(app.applied_at).toLocaleDateString([], {
            month: 'short', day: 'numeric',
          });

          return (
            <motion.div
              key={app.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ delay: idx * 0.04 }}
              layout
              className="group px-5 py-4 rounded-xl border border-white/5 bg-surface hover:bg-surface-hover transition-colors"
            >
              {/* Main row */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-5">
                  <div className={cn('w-10 h-10 rounded-full flex items-center justify-center border shrink-0', statusStyles[app.status].class)}>
                    <StatusIcon className="w-4 h-4" />
                  </div>

                  <div>
                    <h3 className="font-sans font-semibold text-white flex items-center gap-2">
                      {app.job_title ?? 'Untitled role'}
                      {app.job_id && (
                        <a
                          href={`/job/${app.job_id}`}
                          onClick={e => e.stopPropagation()}
                          className="opacity-0 group-hover:opacity-100 transition-opacity text-gray-500 hover:text-white"
                          title="View the original JD"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      )}
                    </h3>
                    <div className="flex items-center gap-3 mt-0.5 text-sm text-gray-400">
                      <span className="font-medium">{app.company_name ?? 'Unknown company'}</span>
                      <span>•</span>
                      <span className="font-mono text-xs">Applied {appliedAtLabel}</span>
                      {app.cv_version && (
                        <>
                          <span>•</span>
                          <span className="font-mono text-[10px] uppercase tracking-wider text-gray-500">
                            {app.cv_version} CV
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <div className={cn('px-3 py-1 rounded-md border text-xs font-mono font-medium whitespace-nowrap', statusStyles[app.status].class)}>
                      {statusLabel[app.status]}
                    </div>
                    <div className="text-xs font-sans italic text-gray-500 mt-1 max-w-[220px] truncate text-right">
                      "{commentary}"
                    </div>
                  </div>

                  {expandable && (
                    <button
                      onClick={() => toggleExpand(app.id)}
                      className={cn(
                        'p-1.5 rounded-lg border transition-colors shrink-0',
                        isExpanded
                          ? 'bg-surface-active border-white/10 text-white'
                          : 'border-transparent text-gray-500 hover:text-white hover:border-white/10',
                      )}
                    >
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                  )}
                </div>
              </div>

              {/* Expanded content */}
              <AnimatePresence>
                {isExpanded && app.status === 'interview' && (
                  <InterviewExpanded key="interview" app={app} />
                )}
                {isExpanded && app.status === 'ghosting' && (
                  <GhostingExpanded key="ghosting" app={app} onWriteOff={() => writeOff(app.id)} />
                )}
              </AnimatePresence>
            </motion.div>
          );
        })}
      </div>

      {apps.length === 0 && (
        <div className="mt-16 text-center">
          <p className="text-gray-500 font-mono text-sm">
            Nothing tracked yet. Apply to something first.
          </p>
        </div>
      )}
    </div>
  );
};
