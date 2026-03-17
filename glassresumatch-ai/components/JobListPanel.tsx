import React, { useRef, useEffect, useState } from 'react';
import { JobWithEvaluation, fetchEvaluations } from '../services/jobService';
import { JobListItem } from './JobListItem';
import { Loader2, Trash2 } from 'lucide-react';

const ACTION_ORDER: Record<string, number> = {
    apply: 0,
    tailor: 1,
    pending: 2,
    skip: 3,
};

const SECTION_LABELS: Record<string, string> = {
    apply: 'Apply now',
    tailor: 'Tailor first',
    pending: 'Evaluating',
    skip: 'Low match',
};

const SECTION_DOT: Record<string, string> = {
    apply: 'bg-green-500',
    tailor: 'bg-amber-500',
    pending: 'border-[1.5px] border-slate-300',
    skip: 'bg-slate-200',
};

interface RecruiterJob {
    id: string;
    title: string;
    company: string;
    email: string;
}

interface JobListPanelProps {
    jobs: JobWithEvaluation[];
    totalJobs: number;
    loading: boolean;
    loadingMore: boolean;
    hasMore: boolean;
    loadMore: () => void;
    showSectionHeaders?: boolean; // false when a tab already communicates the section
    activeAction?: 'apply' | 'tailor' | 'skip' | 'all'; // scopes recruiter contacts to current tab
    selectedJobId: string | null;
    selectedIds: Set<string>;
    isDeleting: boolean;
    onJobClick: (job: JobWithEvaluation) => void;
    onToggleSelect: (id: string) => void;
    onToggleSelectAll: () => void;
    onDeleteSelected: () => void;
}

export const JobListPanel: React.FC<JobListPanelProps> = ({
    jobs, totalJobs, loading, loadingMore, hasMore, loadMore,
    showSectionHeaders = true,
    activeAction = 'all',
    selectedJobId, selectedIds, isDeleting,
    onJobClick, onToggleSelect, onToggleSelectAll, onDeleteSelected,
}) => {
    const sentinelRef = useRef<HTMLDivElement>(null);
    const feedRef = useRef<HTMLDivElement>(null);
    const [recruiterModalOpen, setRecruiterModalOpen] = useState(false);
    const [recruiterJobs, setRecruiterJobs] = useState<RecruiterJob[]>([]);
    const [actionedIds, setActionedIds] = useState<Set<string>>(new Set());

    // Sort by actionability, then score desc within each group
    const sortedJobs = [...jobs].sort((a, b) => {
        const aOrder = ACTION_ORDER[a.evaluation?.recommended_action ?? 'pending'] ?? 2;
        const bOrder = ACTION_ORDER[b.evaluation?.recommended_action ?? 'pending'] ?? 2;
        if (aOrder !== bOrder) return aOrder - bOrder;
        return (b.evaluation?.job_match_score ?? 0) - (a.evaluation?.job_match_score ?? 0);
    });

    // Fetch recruiter contacts for the active tab — re-runs when tab changes
    useEffect(() => {
        const action = activeAction === 'all' ? undefined : activeAction;
        fetchEvaluations(1, 500, action).then(result => {
            const contacts = result.data
                .filter((e: any) => e.recruiter_email && e.recruiter_email !== 'Unknown')
                .map((e: any) => ({
                    id: e.job_id,
                    title: e.title_role ?? 'Unknown role',
                    company: e.company_name ?? 'Unknown',
                    email: e.recruiter_email,
                }));
            setRecruiterJobs(contacts);
        }).catch(() => {});
    }, [activeAction]);

    // Infinite scroll observer
    useEffect(() => {
        if (!sentinelRef.current || !hasMore) return;
        const obs = new IntersectionObserver(
            ([entry]) => { if (entry.isIntersecting) loadMore(); },
            { root: feedRef.current, threshold: 0.1 }
        );
        obs.observe(sentinelRef.current);
        return () => obs.disconnect();
    }, [hasMore, loadMore]);

    // Group by action for section headers
    const grouped: { action: string; items: JobWithEvaluation[] }[] = [];
    let lastAction = '';
    for (const job of sortedJobs) {
        const action = job.evaluation?.recommended_action ?? 'pending';
        if (action !== lastAction) {
            grouped.push({ action, items: [] });
            lastAction = action;
        }
        grouped[grouped.length - 1].items.push(job);
    }

    const recruiterCount = recruiterJobs.length;
    const newRecruiterCount = recruiterJobs.filter(r => !actionedIds.has(r.id)).length;

    const toggleActioned = (id: string) => {
        setActionedIds(prev => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center h-full text-slate-400">
                <Loader2 className="w-8 h-8 animate-spin mb-3 text-slate-200" />
                <p className="text-[12px] animate-pulse">Loading jobs…</p>
            </div>
        );
    }

    return (
        <>
            {/* List header */}
            <div className="px-3.5 py-2.5 border-b border-slate-50 bg-slate-50/50 flex items-center justify-between flex-shrink-0 h-11">
                <div className="flex items-center gap-2">
                    <input
                        type="checkbox"
                        // Select-all checks against loaded jobs, not API total
                        checked={jobs.length > 0 && selectedIds.size === jobs.length}
                        onChange={onToggleSelectAll}
                        className="w-3.5 h-3.5 rounded border-slate-300 text-slate-900 cursor-pointer"
                    />
                    <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
                        {selectedIds.size > 0 ? `${selectedIds.size} selected` : `${totalJobs} jobs`}
                    </span>
                </div>

                <div className="flex items-center gap-2">
                    {/* Recruiter pill */}
                    {recruiterCount > 0 && (
                        <button
                            onClick={() => setRecruiterModalOpen(true)}
                            className="flex items-center gap-1.5 text-[11px] font-medium border border-slate-200 bg-white text-slate-700 px-2.5 py-1 rounded-full hover:border-slate-400 transition-colors relative"
                        >
                            <div className={`w-1.5 h-1.5 rounded-full ${newRecruiterCount > 0 ? 'bg-amber-400 animate-pulse' : 'bg-slate-300'}`} />
                            {recruiterCount}
                            {newRecruiterCount > 0 && (
                                <span className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-slate-900 text-white rounded-full text-[9px] font-bold flex items-center justify-center">
                                    {newRecruiterCount}
                                </span>
                            )}
                        </button>
                    )}

                    {selectedIds.size > 0 && (
                        <button
                            onClick={onDeleteSelected}
                            disabled={isDeleting}
                            className="flex items-center gap-1 text-[11px] font-medium text-rose-500 hover:text-rose-700 bg-rose-50 hover:bg-rose-100 px-2 py-1 rounded transition-colors"
                        >
                            {isDeleting ? <Loader2 className="w-3 h-3 animate-spin" /> : <Trash2 className="w-3 h-3" />}
                            Delete
                        </button>
                    )}
                </div>
            </div>

            {/* Job feed */}
            <div ref={feedRef} className="flex-1 overflow-y-auto min-h-0">
                {sortedJobs.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full py-16 text-slate-400">
                        <p className="text-[12px]">No jobs</p>
                    </div>
                ) : (
                    grouped.map(({ action, items }) => (
                        <React.Fragment key={action}>
                            {/* Section header — hidden when tab already communicates the section */}
                            {showSectionHeaders && (
                                <div className="flex items-center gap-1.5 px-3.5 py-1.5 bg-slate-50/80 border-b border-slate-50 sticky top-0 z-10">
                                    <div className={`w-[5px] h-[5px] rounded-full ${SECTION_DOT[action] ?? 'bg-slate-200'}`} />
                                    <span className="text-[10px] font-medium text-slate-400 uppercase tracking-[0.07em]">
                                        {SECTION_LABELS[action] ?? action}
                                    </span>
                                </div>
                            )}
                            {items.map(job => (
                                <JobListItem
                                    key={job.id}
                                    job={job}
                                    isActive={selectedJobId === job.id}
                                    isSelected={selectedIds.has(job.id)}
                                    onToggleSelect={() => onToggleSelect(job.id)}
                                    onClick={() => onJobClick(job)}
                                />
                            ))}
                        </React.Fragment>
                    ))
                )}

                {/* Infinite scroll sentinel */}
                {hasMore && (
                    <div ref={sentinelRef} className="py-3 text-center">
                        {loadingMore
                            ? <Loader2 className="w-4 h-4 animate-spin text-slate-300 mx-auto" />
                            : <span className="text-[11px] text-slate-200">· · ·</span>
                        }
                    </div>
                )}

                {!hasMore && sortedJobs.length > 0 && (
                    <div className="py-4 text-center text-[11px] text-slate-200">
                        {totalJobs} jobs loaded
                    </div>
                )}
            </div>

            {/* Recruiter modal */}
            {recruiterModalOpen && (
                <div
                    className="fixed inset-0 z-50 flex items-center justify-center bg-black/25 backdrop-blur-[2px]"
                    onClick={() => setRecruiterModalOpen(false)}
                >
                    <div
                        className="bg-white rounded-2xl shadow-2xl w-[400px] max-h-[70vh] overflow-y-auto p-6"
                        onClick={e => e.stopPropagation()}
                    >
                        <div className="flex items-start justify-between mb-1">
                            <div>
                                <h2 className="text-[14px] font-medium text-slate-900">Recruiter contacts</h2>
                                <p className="text-[12px] text-slate-400 mt-0.5">Reach out directly — skips the queue</p>
                            </div>
                            <button
                                onClick={() => setRecruiterModalOpen(false)}
                                className="text-[12px] text-slate-400 hover:text-slate-600"
                            >✕</button>
                        </div>

                        <div className="mt-4 space-y-0 divide-y divide-slate-50">
                            {recruiterJobs.map(rj => (
                                <div key={rj.id} className="flex items-center gap-3 py-2.5">
                                    <div className="w-8 h-8 rounded-lg bg-slate-900 text-white text-[11px] font-semibold flex items-center justify-center shrink-0">
                                        {rj.company.charAt(0)}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-[12px] font-medium text-slate-900 truncate">
                                            {rj.title} · {rj.company}
                                        </p>
                                        <p className="text-[11px] text-blue-600 truncate">{rj.email}</p>
                                    </div>
                                    <button
                                        onClick={() => toggleActioned(rj.id)}
                                        className={`text-[10px] font-medium px-2 py-1 rounded flex-shrink-0 transition-colors ${
                                            actionedIds.has(rj.id)
                                                ? 'bg-slate-100 text-slate-400'
                                                : 'bg-amber-50 text-amber-700 hover:bg-amber-100'
                                        }`}
                                    >
                                        {actionedIds.has(rj.id) ? 'Done' : 'New'}
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </>
    );
};
