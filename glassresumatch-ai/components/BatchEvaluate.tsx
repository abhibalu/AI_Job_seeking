import React, { useState, useEffect } from 'react';
import { GlassCard } from './GlassCard';
import { X, Zap, Loader2, CheckCircle, Building2 } from 'lucide-react';
import { startBatchEvaluation, getTaskStatus } from '../services/jobService';
import { TaskStatus } from '../services/apiClient';

interface BatchEvaluateProps {
    isOpen: boolean;
    onClose: () => void;
    onComplete: () => void;
}

export const BatchEvaluate: React.FC<BatchEvaluateProps> = ({ isOpen, onClose, onComplete }) => {
    const [maxJobs, setMaxJobs] = useState(10);
    const [onlyUnevaluated, setOnlyUnevaluated] = useState(true);
    const [companyFilter, setCompanyFilter] = useState('');
    const [isRunning, setIsRunning] = useState(false);
    const [taskId, setTaskId] = useState<string | null>(null);
    const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);

    // Poll task status
    useEffect(() => {
        if (!taskId || !isRunning) return;

        const pollInterval = setInterval(async () => {
            try {
                const status = await getTaskStatus(taskId);
                setTaskStatus(status);

                if (status.status === 'completed' || status.status === 'failed') {
                    setIsRunning(false);
                    if (status.status === 'completed') {
                        setTimeout(() => {
                            onComplete();
                            handleClose();
                        }, 1500);
                    }
                }
            } catch (error) {
                console.error('Failed to get task status:', error);
            }
        }, 2000);

        return () => clearInterval(pollInterval);
    }, [taskId, isRunning, onComplete]);

    const handleClose = () => {
        if (!isRunning) {
            setTaskId(null);
            setTaskStatus(null);
            onClose();
        }
    };

    const handleStart = async () => {
        setIsRunning(true);
        try {
            const response = await startBatchEvaluation(
                maxJobs,
                onlyUnevaluated,
                companyFilter || undefined
            );
            if (response.task_id) {
                setTaskId(response.task_id);
            }
        } catch (error) {
            console.error('Failed to start batch evaluation:', error);
            setIsRunning(false);
        }
    };

    if (!isOpen) return null;

    const progress = taskStatus?.progress;
    const progressPercent = progress ? Math.round((progress.completed / progress.total) * 100) : 0;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div
                className="absolute inset-0 bg-slate-900/20 backdrop-blur-sm"
                onClick={handleClose}
            />

            <GlassCard className="w-full max-w-md p-6 z-20 bg-white/95 shadow-2xl">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-xl font-bold text-slate-900 flex items-center">
                        <Zap className="w-5 h-5 mr-2 text-purple-600" />
                        Batch Evaluation
                    </h2>
                    {!isRunning && (
                        <button
                            onClick={handleClose}
                            className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400"
                        >
                            <X className="w-5 h-5" />
                        </button>
                    )}
                </div>

                {!isRunning && !taskStatus ? (
                    <>
                        {/* Configuration */}
                        <div className="space-y-5">
                            {/* Max Jobs Slider */}
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-2">
                                    Maximum Jobs to Evaluate: <span className="text-blue-600 font-bold">{maxJobs}</span>
                                </label>
                                <input
                                    type="range"
                                    min="1"
                                    max="50"
                                    value={maxJobs}
                                    onChange={(e) => setMaxJobs(Number(e.target.value))}
                                    className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                                />
                                <div className="flex justify-between text-xs text-slate-400 mt-1">
                                    <span>1</span>
                                    <span>25</span>
                                    <span>50</span>
                                </div>
                            </div>

                            {/* Only Unevaluated Toggle */}
                            <div className="flex items-center justify-between">
                                <label className="text-sm font-medium text-slate-700">
                                    Only unevaluated jobs
                                </label>
                                <button
                                    onClick={() => setOnlyUnevaluated(!onlyUnevaluated)}
                                    className={`w-12 h-6 rounded-full transition-colors ${onlyUnevaluated ? 'bg-blue-600' : 'bg-slate-300'
                                        }`}
                                >
                                    <div className={`w-5 h-5 bg-white rounded-full shadow-md transform transition-transform ${onlyUnevaluated ? 'translate-x-6' : 'translate-x-0.5'
                                        }`} />
                                </button>
                            </div>

                            {/* Company Filter */}
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-2">
                                    <Building2 className="w-4 h-4 inline mr-1" />
                                    Company Filter (optional)
                                </label>
                                <input
                                    type="text"
                                    value={companyFilter}
                                    onChange={(e) => setCompanyFilter(e.target.value)}
                                    placeholder="e.g., Google, Microsoft"
                                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                            </div>
                        </div>

                        {/* Start Button */}
                        <button
                            onClick={handleStart}
                            className="w-full mt-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-xl font-medium transition-all shadow-lg hover:shadow-xl flex items-center justify-center"
                        >
                            <Zap className="w-4 h-4 mr-2" />
                            Start Evaluation
                        </button>
                    </>
                ) : (
                    <>
                        {/* Progress View */}
                        <div className="text-center py-6">
                            {taskStatus?.status === 'completed' ? (
                                <>
                                    <CheckCircle className="w-16 h-16 text-emerald-500 mx-auto mb-4" />
                                    <h3 className="text-lg font-semibold text-slate-900">Completed!</h3>
                                    <p className="text-slate-500 mt-1">
                                        Evaluated {progress?.completed || 0} jobs
                                    </p>
                                </>
                            ) : taskStatus?.status === 'failed' ? (
                                <>
                                    <X className="w-16 h-16 text-rose-500 mx-auto mb-4" />
                                    <h3 className="text-lg font-semibold text-slate-900">Failed</h3>
                                    <p className="text-rose-500 mt-1 text-sm">
                                        {taskStatus.error || 'Unknown error'}
                                    </p>
                                </>
                            ) : (
                                <>
                                    <Loader2 className="w-16 h-16 text-purple-500 mx-auto mb-4 animate-spin" />
                                    <h3 className="text-lg font-semibold text-slate-900">Evaluating Jobs...</h3>
                                    <p className="text-slate-500 mt-1">
                                        {progress?.completed || 0} of {progress?.total || maxJobs} completed
                                    </p>

                                    {/* Progress Bar */}
                                    <div className="mt-4 w-full bg-slate-200 rounded-full h-3 overflow-hidden">
                                        <div
                                            className="h-full bg-gradient-to-r from-purple-500 to-blue-500 transition-all duration-300"
                                            style={{ width: `${progressPercent}%` }}
                                        />
                                    </div>
                                    <p className="text-sm text-slate-400 mt-2">{progressPercent}%</p>
                                </>
                            )}
                        </div>
                    </>
                )}
            </GlassCard>
        </div>
    );
};
