import React from 'react';
import { Search, Filter, SortAsc, SortDesc } from 'lucide-react';
import { FilterOptions, ViewMode } from '../types';

interface FilterBarProps {
    viewMode: ViewMode;
    onViewModeChange: (mode: ViewMode) => void;
    filters: FilterOptions;
    onFiltersChange: (filters: FilterOptions) => void;
}

export const FilterBar: React.FC<FilterBarProps> = ({
    viewMode,
    onViewModeChange,
    filters,
    onFiltersChange
}) => {
    return (
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200/60 p-4 mb-6 shadow-sm">
            <div className="flex flex-wrap items-center gap-4">

                {/* View Mode Tabs */}
                <div className="flex bg-slate-100 rounded-lg p-1">
                    {(['all', 'evaluated', 'pending'] as ViewMode[]).map((mode) => (
                        <button
                            key={mode}
                            onClick={() => onViewModeChange(mode)}
                            className={`px-4 py-2 rounded-md text-sm font-medium transition-all capitalize ${viewMode === mode
                                    ? 'bg-white text-slate-900 shadow-sm'
                                    : 'text-slate-500 hover:text-slate-700'
                                }`}
                        >
                            {mode === 'pending' ? 'To Evaluate' : mode}
                        </button>
                    ))}
                </div>

                {/* Search */}
                <div className="flex-1 min-w-[200px]">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <input
                            type="text"
                            placeholder="Search company or title..."
                            value={filters.searchQuery}
                            onChange={(e) => onFiltersChange({ ...filters, searchQuery: e.target.value })}
                            className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                    </div>
                </div>

                {/* Verdict Filter */}
                <select
                    value={filters.verdict}
                    onChange={(e) => onFiltersChange({ ...filters, verdict: e.target.value as FilterOptions['verdict'] })}
                    className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                    <option value="all">All Verdicts</option>
                    <option value="Strong Match">Strong Match</option>
                    <option value="Moderate Match">Moderate Match</option>
                    <option value="Weak Match">Weak Match</option>
                </select>

                {/* Action Filter */}
                <select
                    value={filters.action}
                    onChange={(e) => onFiltersChange({ ...filters, action: e.target.value as FilterOptions['action'] })}
                    className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                    <option value="all">All Actions</option>
                    <option value="apply">Apply</option>
                    <option value="tailor">Tailor</option>
                    <option value="skip">Skip</option>
                </select>

                {/* Sort */}
                <div className="flex items-center space-x-2">
                    <select
                        value={filters.sortBy}
                        onChange={(e) => onFiltersChange({ ...filters, sortBy: e.target.value as FilterOptions['sortBy'] })}
                        className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="score">Score</option>
                        <option value="company">Company</option>
                        <option value="date">Date</option>
                    </select>
                    <button
                        onClick={() => onFiltersChange({
                            ...filters,
                            sortOrder: filters.sortOrder === 'asc' ? 'desc' : 'asc'
                        })}
                        className="p-2 bg-slate-50 border border-slate-200 rounded-lg hover:bg-slate-100 transition-colors"
                    >
                        {filters.sortOrder === 'asc' ? (
                            <SortAsc className="w-4 h-4 text-slate-600" />
                        ) : (
                            <SortDesc className="w-4 h-4 text-slate-600" />
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
};
