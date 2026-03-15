import React from 'react';
import { JobWithEvaluation } from '../services/jobService';
import { formatTimeAgo } from '../utils/format';

interface JobListItemProps {
    job: JobWithEvaluation;
    isActive: boolean;
    isSelected: boolean;
    onToggleSelect: () => void;
    onClick: () => void;
}

export const JobListItem: React.FC<JobListItemProps> = ({
    job, isActive, isSelected, onToggleSelect, onClick
}) => {
    const action = job.evaluation?.recommended_action ?? 'pending';
    const score = job.evaluation?.job_match_score;
    const hasRecruiter =
        job.evaluation?.recruiter_email &&
        job.evaluation.recruiter_email !== 'Unknown';

    const edgeColor = () => {
        if (action === 'apply') return 'bg-green-500';
        if (action === 'tailor') return 'bg-amber-500';
        if (action === 'skip') return 'bg-slate-200';
        return 'transparent';
    };

    const rowBg = () => {
        if (isActive) return 'bg-slate-100';
        if (action === 'apply') return 'bg-gradient-to-r from-green-50/40 to-transparent';
        if (action === 'tailor') return 'bg-gradient-to-r from-amber-50/40 to-transparent';
        return '';
    };

    const verdictColor = () => {
        if (action === 'apply') return 'text-green-600';
        if (action === 'tailor') return 'text-amber-600';
        if (action === 'skip') return 'text-slate-300';
        return 'text-slate-300';
    };

    const verdictLabel = () => {
        if (action === 'apply') return 'Apply';
        if (action === 'tailor') return 'Tailor';
        if (action === 'skip') return 'Skip';
        return '—';
    };

    const isSkip = action === 'skip';

    return (
        <div
            className={`relative flex items-start gap-2.5 pl-4 pr-3.5 py-2.5 cursor-pointer border-b border-slate-50 transition-all ${rowBg()} ${isSkip ? 'opacity-40' : ''}`}
            onClick={onClick}
        >
            {/* Left edge accent */}
            <div className={`absolute left-0 top-0 bottom-0 w-[3px] rounded-r-sm ${edgeColor()}`} />

            {/* Checkbox */}
            <div className="pt-0.5 shrink-0" onClick={e => { e.stopPropagation(); onToggleSelect(); }}>
                <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={onToggleSelect}
                    className="w-3.5 h-3.5 rounded border-slate-300 text-slate-900 focus:ring-slate-500 cursor-pointer"
                />
            </div>

            {/* Main content */}
            <div className="flex-1 min-w-0">
                <div className="text-[12px] font-medium text-slate-900 whitespace-nowrap overflow-hidden text-ellipsis mb-0.5">
                    {job.title}
                </div>
                <div className="text-[11px] text-slate-400">
                    {job.company_name}
                    {job.posted_at && <> · {formatTimeAgo(job.posted_at)}</>}
                </div>
            </div>

            {/* Right: score + verdict + recruiter dot */}
            <div className="flex flex-col items-end gap-0.5 shrink-0">
                {score !== undefined && score !== null && (
                    <span className="text-[12px] font-medium text-slate-900">{score}</span>
                )}
                <span className={`text-[10px] font-medium ${verdictColor()}`}>
                    {verdictLabel()}
                </span>
                {hasRecruiter && (
                    <div className="w-1.5 h-1.5 rounded-full bg-amber-400 mt-0.5" title="Recruiter contact available" />
                )}
            </div>
        </div>
    );
};
