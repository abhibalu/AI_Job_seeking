import React from 'react';
import { JobWithEvaluation } from '../services/jobService';
import { Building2, XCircle, CheckCircle2, Clock } from 'lucide-react';
import { formatTimeAgo } from '../utils/format';

interface JobListItemProps {
    job: JobWithEvaluation;
    isActive: boolean;
    onClick: () => void;
}

export const JobListItem: React.FC<JobListItemProps> = ({ job, isActive, onClick }) => {
    const score = job.evaluation?.job_match_score || 0;

    // Logo is now strict black/dark theme
    const getLogoColor = () => 'bg-slate-900';

    const getBgColor = () => {
        if (isActive) return 'bg-gray-50 border-l-4 border-l-black';
        return 'bg-white hover:bg-gray-50/80 border-l-4 border-l-transparent';
    };

    return (
        <div
            onClick={onClick}
            className={`
        w-full p-4 border-b border-gray-100 cursor-pointer transition-all duration-200 relative
        ${getBgColor()}
      `}
        >
            <div className="flex gap-3">
                {/* Logo */}
                <div className={`w-12 h-12 min-w-[3rem] rounded-md ${getLogoColor()} flex items-center justify-center text-white font-bold text-lg shadow-sm border border-slate-900`}>
                    {job.company_name?.charAt(0) || 'C'}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                    <h3 className={`text-base font-semibold truncate ${isActive ? 'text-black' : 'text-slate-900'}`}>
                        {job.title}
                    </h3>
                    <div className="text-sm text-slate-600 truncate font-medium">
                        {job.company_name}
                    </div>
                    <div className="flex items-center text-xs text-slate-500 mt-1 mb-2">
                        <span className="truncate">{job.location || 'Remote'}</span>
                        <span className="mx-1">•</span>
                        {job.posted_at && (
                            <span className="text-slate-600 font-medium flex items-center gap-1">
                                <Clock size={10} />
                                {formatTimeAgo(job.posted_at)}
                            </span>
                        )}
                    </div>

                    {job.isEvaluated && job.evaluation ? (
                        <div className="flex items-center gap-2 mt-2">
                            {/* Match Badge - Monochrome */}
                            <div className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border bg-white text-slate-900 border-slate-200 shadow-sm">
                                {score}% Match
                            </div>

                            {/* Status Badge (Tailor/Skip) */}
                            <div className="flex items-center gap-1">
                                {job.evaluation.recommended_action === 'skip' ? (
                                    <XCircle className="w-3 h-3 text-slate-400" />
                                ) : job.evaluation.recommended_action === 'tailor' ? (
                                    <CheckCircle2 className="w-3 h-3 text-slate-900" />
                                ) : (
                                    <Clock className="w-3 h-3 text-slate-400" />
                                )}
                                <span className="text-xs text-slate-600 capitalize">{job.evaluation.recommended_action}</span>
                            </div>
                        </div>
                    ) : (
                        <div className="mt-2 text-xs text-slate-400 italic">
                            Click to Analyze
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
