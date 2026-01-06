import React from 'react';
import { Sparkles, Plus, BarChart3, Zap, FileText, Briefcase } from 'lucide-react';
import { ViewMode } from '../types';

interface HeaderProps {
  onAddJob: () => void;
  onBatchEvaluate?: () => void;
  totalJobs?: number;
  evaluatedCount?: number;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
}

export const Header: React.FC<HeaderProps> = ({
  onAddJob,
  onBatchEvaluate,
  totalJobs = 0,
  evaluatedCount = 0,
  viewMode,
  onViewModeChange
}) => {
  return (
    <header className="sticky top-0 z-40 backdrop-blur-xl bg-white/70 border-b border-slate-200/60">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-purple-600 flex items-center justify-center shadow-lg">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-900">TailorAI</h1>
              <p className="text-xs text-slate-500">Job Match & Resume Tailor</p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="hidden md:flex bg-slate-100/50 p-1 rounded-xl border border-slate-200/60">
            <button
              onClick={() => onViewModeChange('all')}
              className={`flex items-center px-4 py-2 rounded-lg text-sm font-medium transition-all ${viewMode !== 'resume'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
                }`}
            >
              <Briefcase className="w-4 h-4 mr-2" />
              Jobs
            </button>
            <button
              onClick={() => onViewModeChange('resume')}
              className={`flex items-center px-4 py-2 rounded-lg text-sm font-medium transition-all ${viewMode === 'resume'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
                }`}
            >
              <FileText className="w-4 h-4 mr-2" />
              My Resume
            </button>
          </div>

          {/* Stats Badges */}
          <div className="hidden md:flex items-center space-x-4">
            <div className="flex items-center bg-slate-100 rounded-lg px-3 py-1.5">
              <BarChart3 className="w-4 h-4 text-slate-500 mr-2" />
              <span className="text-sm font-medium text-slate-700">
                {totalJobs} Jobs
              </span>
            </div>
            <div className="flex items-center bg-emerald-50 rounded-lg px-3 py-1.5">
              <Zap className="w-4 h-4 text-emerald-500 mr-2" />
              <span className="text-sm font-medium text-emerald-700">
                {evaluatedCount} Evaluated
              </span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center space-x-3">
            {onBatchEvaluate && (
              <button
                onClick={onBatchEvaluate}
                className="flex items-center px-4 py-2.5 bg-purple-600 hover:bg-purple-700 text-white rounded-xl font-medium text-sm transition-all shadow-md hover:shadow-lg"
              >
                <Zap className="w-4 h-4 mr-2" />
                Batch Evaluate
              </button>
            )}
            <button
              onClick={onAddJob}
              className="flex items-center px-4 py-2.5 bg-slate-900 hover:bg-slate-800 text-white rounded-xl font-medium text-sm transition-all shadow-md hover:shadow-lg"
            >
              <Plus className="w-4 h-4 mr-2" />
              Analyze New JD
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};