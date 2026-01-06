import React from 'react';
import { EvaluationStats } from '../services/apiClient';
import { BarChart3, Target, TrendingUp, CheckCircle, Edit3, XCircle } from 'lucide-react';

interface StatsCardProps {
    stats: EvaluationStats | null;
    totalJobs: number;
}

export const StatsCard: React.FC<StatsCardProps> = ({ stats, totalJobs }) => {
    if (!stats) return null;

    const getActionIcon = (action: string) => {
        switch (action) {
            case 'apply': return <CheckCircle className="w-4 h-4 text-emerald-500" />;
            case 'tailor': return <Edit3 className="w-4 h-4 text-amber-500" />;
            case 'skip': return <XCircle className="w-4 h-4 text-rose-500" />;
            default: return null;
        }
    };

    const getActionColor = (action: string) => {
        switch (action) {
            case 'apply': return 'bg-emerald-50 border-emerald-100 text-emerald-700';
            case 'tailor': return 'bg-amber-50 border-amber-100 text-amber-700';
            case 'skip': return 'bg-rose-50 border-rose-100 text-rose-700';
            default: return 'bg-slate-50 border-slate-100 text-slate-700';
        }
    };

    return (
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200/60 p-6 mb-6 shadow-sm">
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider mb-4 flex items-center">
                <BarChart3 className="w-4 h-4 mr-2" />
                Dashboard Stats
            </h3>

            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                {/* Total Jobs */}
                <div className="bg-slate-50 rounded-xl p-4 border border-slate-100">
                    <div className="text-2xl font-bold text-slate-900">{totalJobs}</div>
                    <div className="text-xs text-slate-500 mt-1">Total Jobs</div>
                </div>

                {/* Evaluated */}
                <div className="bg-blue-50 rounded-xl p-4 border border-blue-100">
                    <div className="text-2xl font-bold text-blue-600">{stats.total_evaluated}</div>
                    <div className="text-xs text-blue-500 mt-1">Evaluated</div>
                </div>

                {/* Average Score */}
                <div className="bg-purple-50 rounded-xl p-4 border border-purple-100">
                    <div className="flex items-baseline">
                        <span className="text-2xl font-bold text-purple-600">{stats.average_score.toFixed(0)}</span>
                        <span className="text-sm text-purple-400 ml-1">%</span>
                    </div>
                    <div className="text-xs text-purple-500 mt-1 flex items-center">
                        <TrendingUp className="w-3 h-3 mr-1" />
                        Avg Score
                    </div>
                </div>

                {/* Actions Breakdown */}
                {Object.entries(stats.by_action).map(([action, count]) => (
                    <div
                        key={action}
                        className={`rounded-xl p-4 border ${getActionColor(action)}`}
                    >
                        <div className="flex items-center justify-between">
                            <div className="text-2xl font-bold">{count}</div>
                            {getActionIcon(action)}
                        </div>
                        <div className="text-xs mt-1 capitalize">{action}</div>
                    </div>
                ))}
            </div>
        </div>
    );
};
