import { useState, useCallback, useEffect } from 'react';
import {
    fetchJobsWithEvaluations,
    fetchEvaluations,
    getEvaluationStats,
    JobWithEvaluation
} from '../services/jobService';
import { EvaluationStats } from '../services/apiClient';
import { ViewMode, FilterOptions } from '../types';

const ITEMS_PER_PAGE = 9;

export const useJobs = (viewMode: ViewMode, filters: FilterOptions) => {
    const [jobs, setJobs] = useState<JobWithEvaluation[]>([]);
    const [stats, setStats] = useState<EvaluationStats | null>(null);
    const [totalJobs, setTotalJobs] = useState(0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [currentPage, setCurrentPage] = useState(1);

    const loadData = useCallback(async (silent = false) => {
        if (viewMode === 'resume') return;

        if (!silent) setLoading(true);
        setError(null);
        try {
            const statsResult = await getEvaluationStats().catch(() => null);
            setStats(statsResult);

            // Determine if we should use Evaluation-first strategy
            const isActionFilter = filters.action !== 'all';
            const isVerdictFilter = filters.verdict !== 'all';
            const useEvalStrategy = viewMode === 'evaluated' || isActionFilter || isVerdictFilter;

            if (useEvalStrategy) {
                const actionFilter = filters.action !== 'all' ? filters.action : undefined;
                const verdictFilter = filters.verdict !== 'all' ? filters.verdict : undefined;
                const searchQuery = filters.searchQuery ? filters.searchQuery : undefined;

                const evaluationsResult = await fetchEvaluations(
                    currentPage,
                    ITEMS_PER_PAGE,
                    actionFilter as any,
                    verdictFilter as any,
                    searchQuery
                );

                const jobsWithEvals: JobWithEvaluation[] = evaluationsResult.data.map((e: any) => ({
                    id: e.job_id,
                    title: e.title_role,
                    company_name: e.company_name,
                    location: null,
                    posted_at: null,
                    applicants_count: null,
                    job_url: e.job_url,
                    company_website: e.company_website,
                    evaluation: e,
                    isEvaluated: true,
                }));

                setJobs(jobsWithEvals);
                setTotalJobs(evaluationsResult.total);
            } else {
                const isEvaluatedFilter = viewMode === 'pending' ? false : undefined;
                const companyFilter = filters.searchQuery ? filters.searchQuery : undefined;

                const jobsResult = await fetchJobsWithEvaluations(currentPage, ITEMS_PER_PAGE, companyFilter, isEvaluatedFilter);
                setJobs(jobsResult.data);
                setTotalJobs(jobsResult.total);
            }
        } catch (err) {
            console.error('Failed to load data:', err);
            setError('Failed to load jobs. Make sure the API server is running.');
        } finally {
            if (!silent) setLoading(false);
        }
    }, [currentPage, viewMode, filters.action, filters.verdict, filters.searchQuery]);

    useEffect(() => {
        loadData();
    }, [loadData]);

    return {
        jobs,
        stats,
        totalJobs,
        loading,
        error,
        currentPage,
        setCurrentPage,
        refresh: loadData
    };
};
