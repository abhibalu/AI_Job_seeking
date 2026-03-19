import React, { useState, useEffect, useCallback } from 'react';
import { cn } from '../lib/utils';
import { apiClient } from '../services/apiClient';
import { formatTimeAgo } from '../utils/format';
import type { Application } from '../types';

const statusColors: Record<string, string> = {
  applied: 'bg-semantic-green/10 text-semantic-green border-semantic-green/20',
  ghosting: 'bg-semantic-amber/10 text-semantic-amber border-semantic-amber/20',
  replied: 'bg-teal-500/10 text-teal-400 border-teal-500/20',
  interview: 'bg-accent/10 text-accent border-accent/20',
  rejected: 'bg-semantic-red/10 text-semantic-red border-semantic-red/20',
  offer: 'bg-semantic-green/10 text-semantic-green border-semantic-green/20 animate-pulse',
};

const allStatuses: Application['status'][] = ['applied', 'replied', 'interview', 'rejected', 'ghosting'];

function getGhostCommentary(appliedAt: string): string {
  const days = Math.floor((Date.now() - new Date(appliedAt).getTime()) / (1000 * 60 * 60 * 24));
  if (days <= 1) return 'Just sent. Deep breaths.';
  if (days <= 3) return 'Probably just busy. Totally normal.';
  if (days <= 7) return "It's only been a week. Chill.";
  if (days <= 14) return "At this point we're assuming they lost it.";
  if (days <= 30) return "They don't deserve you. Moving on.";
  return 'Ghost confirmed. Next.';
}

export const ApplicationTracker: React.FC = () => {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);

  useEffect(() => {
    apiClient.getApplications()
      .then(apps => {
        setApplications(apps);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const handleStatusChange = useCallback(async (appId: string, status: Application['status']) => {
    setOpenDropdown(null);
    // Optimistic
    setApplications(prev => prev.map(a =>
      a.id === appId ? { ...a, status } : a
    ));
    try {
      await apiClient.updateApplicationStatus(appId, status);
    } catch {
      // Rollback on error
      setApplications(prev => prev.map(a =>
        a.id === appId ? { ...a, status: a.status } : a
      ));
    }
  }, []);

  const applied = applications.filter(a => a.status === 'applied').length;
  const inProgress = applications.filter(a => ['replied', 'interview'].includes(a.status)).length;
  const ghosting = applications.filter(a => a.status === 'ghosting').length;

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="w-5 h-5 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-3xl mx-auto p-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-100 mb-2">Applications</h1>
          <div className="text-sm font-mono text-gray-500">
            {applied} applied · {inProgress} in progress · {ghosting} ghosting
          </div>
        </div>

        {/* Applications list */}
        {applications.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-gray-600 font-mono">No applications yet. That changes today.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {applications.map(app => (
              <div
                key={app.id}
                className="border border-white/5 bg-surface rounded-xl p-5 flex items-start gap-4"
              >
                {/* Company initial */}
                <div className="w-10 h-10 rounded-lg bg-surface-hover flex items-center justify-center flex-shrink-0">
                  <span className="text-sm font-bold text-gray-400">
                    {(app.company_name || '?')[0].toUpperCase()}
                  </span>
                </div>

                {/* Job info */}
                <div className="flex-1 min-w-0">
                  <div className="text-white font-semibold truncate">{app.job_title || 'Untitled'}</div>
                  <div className="text-gray-500 font-mono text-sm truncate">
                    {app.company_name}
                  </div>
                  <div className="text-gray-600 text-xs mt-1">
                    Sent {formatTimeAgo(app.applied_at)}
                    {app.cv_version && (
                      <span className="ml-2 text-[9px] font-mono px-1.5 py-0.5 rounded bg-white/5 text-gray-500">
                        {app.cv_version}
                      </span>
                    )}
                  </div>
                </div>

                {/* Status badge + dropdown */}
                <div className="relative flex-shrink-0">
                  <button
                    onClick={() => setOpenDropdown(openDropdown === app.id ? null : app.id)}
                    className={cn(
                      'text-[9px] font-bold uppercase rounded-md px-2 py-1 border cursor-pointer',
                      statusColors[app.status] || statusColors.applied
                    )}
                  >
                    {app.status}
                  </button>

                  {openDropdown === app.id && (
                    <div className="absolute right-0 top-full mt-1 bg-surface border border-white/10 rounded-lg z-20 py-1 min-w-[120px]">
                      {allStatuses.map(s => (
                        <button
                          key={s}
                          onClick={() => handleStatusChange(app.id, s)}
                          className={cn(
                            'w-full text-left px-3 py-1.5 text-[10px] font-mono hover:bg-surface-hover transition-colors cursor-pointer capitalize',
                            s === app.status ? 'text-accent' : 'text-gray-400'
                          )}
                        >
                          {s}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Ghost commentary */}
                <div className="text-xs font-mono text-gray-600 italic text-right min-w-[140px] flex-shrink-0">
                  {getGhostCommentary(app.applied_at)}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
