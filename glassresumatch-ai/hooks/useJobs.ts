import { useState, useEffect, useCallback, useRef } from 'react';
import {
    fetchJobsWithEvaluations,
    fetchEvaluations,
    getEvaluationStats,
    JobWithEvaluation
} from '../services/jobService';
import { EvaluationStats } from '../services/apiClient';
import { ViewMode, FilterOptions } from '../types';

const ITEMS_PER_PAGE = 20;

interface UseJobsResult {
    jobs: JobWithEvaluation[];
    /** Unactioned jobs — filter pills apply to this partition */
    activeJobs: JobWithEvaluation[];
    /** Jobs the user has applied to — always rendered below, dimmed */
    actionedJobs: JobWithEvaluation[];
    markActioned: (id: string) => void;
    /** Undo markActioned — call on API failure to roll back optimistic update */
    unmarkActioned: (id: string) => void;
    stats: EvaluationStats | null;
    totalJobs: number;
    loading: boolean;
    loadingMore: boolean;
    error: string | null;
    hasMore: boolean;
    loadMore: () => void;
    refresh: (silent?: boolean) => void;
    // Legacy — kept for compatibility during transition
    currentPage: number;
    setCurrentPage: (page: number) => void;
}

export function useJobs(viewMode: ViewMode, filters: FilterOptions): UseJobsResult {
    const [jobs, setJobs] = useState<JobWithEvaluation[]>([]);
    const [actionedIds, setActionedIds] = useState<Set<string>>(new Set());
    const [stats, setStats] = useState<EvaluationStats | null>(null);
    const [totalJobs, setTotalJobs] = useState(0);
    const [loading, setLoading] = useState(true);
    const [loadingMore, setLoadingMore] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [currentPage, setCurrentPage] = useState(1);

    const hasMore = jobs.length < totalJobs;
    const requestId = useRef(0);

    const fetchPage = useCallback(async (page: number) => {
        if (viewMode === 'resume' || viewMode === 'tracker') return { jobs: [] as JobWithEvaluation[], total: 0, stats: null };

        const statsResult = await getEvaluationStats().catch(() => null);

        const isActionFilter = filters.action !== 'all';
        const isVerdictFilter = filters.verdict !== 'all';
        const useEvalStrategy = viewMode === 'evaluated' || isActionFilter || isVerdictFilter;

        if (useEvalStrategy) {
            const actionFilter = filters.action !== 'all' ? filters.action : undefined;
            const verdictFilter = filters.verdict !== 'all' ? filters.verdict : undefined;
            const searchQuery = filters.searchQuery || undefined;

            const result = await fetchEvaluations(
                page, ITEMS_PER_PAGE,
                actionFilter as any,
                verdictFilter as any,
                searchQuery
            );

            const mapped: JobWithEvaluation[] = result.data.map((e: any) => ({
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

            return { jobs: mapped, total: result.total, stats: statsResult };
        } else {
            const isEvaluatedFilter = viewMode === 'pending' ? false : undefined;
            const companyFilter = filters.searchQuery || undefined;
            const result = await fetchJobsWithEvaluations(page, ITEMS_PER_PAGE, companyFilter, isEvaluatedFilter);
            return { jobs: result.data, total: result.total, stats: statsResult };
        }
    }, [viewMode, filters.action, filters.verdict, filters.searchQuery]);

    const load = useCallback(async (page: number, silent = false, replace = false) => {
        const thisRequest = ++requestId.current;

        if (page === 1 && !silent) setLoading(true);
        if (page > 1) setLoadingMore(true);
        setError(null);

        try {
            const result = await fetchPage(page);
            if (thisRequest !== requestId.current) return;

            if (result.stats) setStats(result.stats);
            setTotalJobs(result.total);

            if (replace || page === 1) {
                setJobs(result.jobs);
            } else {
                setJobs(prev => {
                    const existing = new Set(prev.map(j => j.id));
                    const fresh = result.jobs.filter(j => !existing.has(j.id));
                    return [...prev, ...fresh];
                });
            }
        } catch (err: any) {
            if (thisRequest !== requestId.current) return;
            setError(err?.message ?? 'Failed to load jobs. Make sure the API server is running.');
        } finally {
            if (thisRequest !== requestId.current) return;
            setLoading(false);
            setLoadingMore(false);
        }
    }, [fetchPage]);

    // Reset and reload on filter/view change
    useEffect(() => {
        if (viewMode === 'resume' || viewMode === 'tracker') return;
        setCurrentPage(1);
        setJobs([]);
        setTotalJobs(0); // reset so hasMore goes false→true, re-triggering the scroll observer
        load(1, false, true);
    }, [viewMode, filters.action, filters.verdict, filters.searchQuery]);

    const loadMore = useCallback(() => {
        if (loadingMore || !hasMore) return;
        const next = currentPage + 1;
        setCurrentPage(next);
        load(next);
    }, [loadingMore, hasMore, currentPage, load]);

    const refresh = useCallback((silent = false) => {
        setCurrentPage(1);
        setJobs([]);
        load(1, silent, true);
    }, [load]);

    const markActioned = useCallback((id: string) => {
        setActionedIds(prev => new Set([...prev, id]));
    }, []);

    const unmarkActioned = useCallback((id: string) => {
        setActionedIds(prev => {
            const next = new Set(prev);
            next.delete(id);
            return next;
        });
    }, []);

    // Partition: filter pills (server-side) apply to unactioned jobs only.
    // Actioned jobs are always surfaced separately for the dimmed-below section.
    const activeJobs = jobs.filter(j => !actionedIds.has(j.id));
    const actionedJobs = jobs.filter(j => actionedIds.has(j.id));

    return {
        jobs,
        activeJobs,
        actionedJobs,
        markActioned,
        unmarkActioned,
        stats,
        totalJobs,
        loading,
        loadingMore,
        error,
        hasMore,
        loadMore,
        refresh,
        currentPage,
        setCurrentPage,
    };
}
