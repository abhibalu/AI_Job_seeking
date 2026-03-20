import React, { useState, useEffect, useCallback } from 'react';
import { Application, apiClient } from '../services/apiClient';
import { Loader2, Briefcase, ExternalLink, ChevronRight } from 'lucide-react';
import { formatTimeAgo } from '../utils/format';

// ─── Timeline dots ─────────────────────────────────────────────────────────

const TIMELINE_STEPS: Array<{ key: Application['status']; label: string }> = [
    { key: 'applied',   label: 'Applied' },
    { key: 'replied',   label: 'Replied' },
    { key: 'interview', label: 'Interview' },
    { key: 'rejected',  label: 'Rejected' },
];

const STATUS_ORDER = ['applied', 'replied', 'interview', 'rejected', 'ghosting'];

function stepState(app: Application, stepKey: string): 'done' | 'active' | 'idle' {
    const currentIdx = STATUS_ORDER.indexOf(app.status);
    const stepIdx    = STATUS_ORDER.indexOf(stepKey);
    if (stepIdx < currentIdx) return 'done';
    if (stepIdx === currentIdx) return 'active';
    return 'idle';
}

const TimelineDots: React.FC<{ app: Application }> = ({ app }) => (
    <div className="flex items-center gap-0 mt-3">
        {TIMELINE_STEPS.map((step, i) => {
            const state = stepState(app, step.key);
            const dotCls =
                state === 'done'   ? 'w-2 h-2 rounded-full bg-slate-900' :
                state === 'active' ? 'w-2 h-2 rounded-full bg-amber-500 ring-2 ring-amber-200' :
                                     'w-2 h-2 rounded-full bg-slate-200';
            const labelCls =
                state === 'idle' ? 'text-slate-300' :
                state === 'done' ? 'text-slate-500' : 'text-slate-700 font-medium';
            return (
                <React.Fragment key={step.key}>
                    <div className="flex flex-col items-center gap-1">
                        <div className={dotCls} />
                        <span className={`text-[10px] ${labelCls} whitespace-nowrap`}>{step.label}</span>
                    </div>
                    {i < TIMELINE_STEPS.length - 1 && (
                        <div className={`w-8 h-px mb-[14px] mx-0.5 ${
                            stepState(app, TIMELINE_STEPS[i + 1].key) !== 'idle' ? 'bg-slate-300' : 'bg-slate-100'
                        }`} />
                    )}
                </React.Fragment>
            );
        })}
    </div>
);

// ─── Status action chips ───────────────────────────────────────────────────

const NEXT_STATUSES: Partial<Record<Application['status'], Array<{ status: Application['status']; label: string }>>> = {
    applied:   [{ status: 'replied',   label: 'Mark replied'   }, { status: 'ghosting', label: 'Ghosted' }, { status: 'rejected', label: 'Rejected' }],
    replied:   [{ status: 'interview', label: 'Got interview'  }, { status: 'rejected', label: 'Rejected' }],
    interview: [{ status: 'rejected',  label: 'Rejected'       }],
};

// ─── Application card ──────────────────────────────────────────────────────

interface CardProps {
    app: Application;
    onStatusUpdate: (id: string, status: Application['status']) => void;
    onViewSent: (app: Application) => void;
}

const ApplicationCard: React.FC<CardProps> = ({ app, onStatusUpdate, onViewSent }) => {
    const [updating, setUpdating] = useState(false);

    const handleStatus = async (status: Application['status']) => {
        setUpdating(true);
        await onStatusUpdate(app.id, status);
        setUpdating(false);
    };

    const nextSteps = NEXT_STATUSES[app.status] ?? [];
    const initial = (app.company_name ?? app.job_id).charAt(0).toUpperCase();

    return (
        <div className="bg-white border border-slate-100 rounded-xl p-5 hover:border-slate-200 transition-colors">
            <div className="flex items-start justify-between gap-3">
                {/* Left: identity */}
                <div className="flex items-start gap-3 flex-1 min-w-0">
                    <div className="w-9 h-9 rounded-lg bg-slate-900 text-white text-sm font-semibold flex items-center justify-center shrink-0">
                        {initial}
                    </div>
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-[14px] font-medium text-slate-900 truncate">
                                {app.job_title ?? 'Untitled role'}
                            </span>
                            <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full border ${
                                app.cv_version === 'tailored'
                                    ? 'bg-purple-50 text-purple-700 border-purple-200'
                                    : 'bg-slate-50 text-slate-500 border-slate-200'
                            }`}>
                                {app.cv_version === 'tailored' ? 'tailored CV' : 'base CV'}
                            </span>
                        </div>
                        <div className="text-[12px] text-slate-500 mt-0.5">
                            {app.company_name ?? app.job_id}
                            {app.applied_at && (
                                <span className="text-slate-300 ml-1.5">· {formatTimeAgo(app.applied_at)}</span>
                            )}
                        </div>
                    </div>
                </div>

                {/* Right: view sent */}
                <button
                    onClick={() => onViewSent(app)}
                    className="flex items-center gap-1 text-[12px] text-slate-500 hover:text-slate-900 transition-colors whitespace-nowrap shrink-0"
                >
                    View what you sent
                    <ChevronRight className="w-3.5 h-3.5" />
                </button>
            </div>

            {/* Timeline */}
            <TimelineDots app={app} />

            {/* Status actions */}
            {nextSteps.length > 0 && (
                <div className="flex items-center gap-1.5 mt-3 pt-3 border-t border-slate-50">
                    {updating ? (
                        <Loader2 className="w-3.5 h-3.5 text-slate-300 animate-spin" />
                    ) : (
                        nextSteps.map(s => (
                            <button
                                key={s.status}
                                onClick={() => handleStatus(s.status)}
                                className="text-[11px] text-slate-500 hover:text-slate-900 px-2.5 py-1 rounded-md border border-slate-100 hover:border-slate-300 transition-colors"
                            >
                                {s.label}
                            </button>
                        ))
                    )}
                </div>
            )}
        </div>
    );
};

// ─── Main tracker ──────────────────────────────────────────────────────────

interface ApplicationTrackerProps {
    onViewSent: (app: Application) => void;
}

export const ApplicationTracker: React.FC<ApplicationTrackerProps> = ({ onViewSent }) => {
    const [applications, setApplications] = useState<Application[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const data = await apiClient.getApplications();
            setApplications(data);
        } catch {
            setError('Failed to load applications.');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    const handleStatusUpdate = useCallback(async (id: string, status: Application['status']) => {
        try {
            const updated = await apiClient.updateApplicationStatus(id, status);
            setApplications(prev => prev.map(a => a.id === id ? updated : a));
        } catch {
            // Silent — no rollback needed for non-optimistic update
        }
    }, []);

    if (loading) return (
        <div className="flex items-center justify-center py-24">
            <Loader2 className="w-6 h-6 text-slate-300 animate-spin" />
        </div>
    );

    if (error) return (
        <div className="text-center py-20 text-rose-500 text-sm">{error}</div>
    );

    if (applications.length === 0) return (
        <div className="flex flex-col items-center justify-center py-24 text-center">
            <div className="w-14 h-14 bg-slate-100 rounded-full flex items-center justify-center mb-4">
                <Briefcase className="w-7 h-7 text-slate-300" />
            </div>
            <h3 className="text-[15px] font-medium text-slate-700 mb-1">No applications yet</h3>
            <p className="text-[13px] text-slate-400 max-w-xs">
                When you click Apply in a job card, it will appear here so you can track its progress.
            </p>
        </div>
    );

    return (
        <div className="max-w-2xl mx-auto py-8 px-4 space-y-3">
            <div className="flex items-center justify-between mb-6">
                <h2 className="text-[15px] font-semibold text-slate-900">
                    Applications
                    <span className="ml-2 text-[12px] font-normal text-slate-400">{applications.length}</span>
                </h2>
            </div>

            {applications.map(app => (
                <ApplicationCard
                    key={app.id}
                    app={app}
                    onStatusUpdate={handleStatusUpdate}
                    onViewSent={onViewSent}
                />
            ))}
        </div>
    );
};
