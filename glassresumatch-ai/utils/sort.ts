import { JobWithEvaluation, FilterOptions } from '../types';

/**
 * Sort jobs based on filter criteria.
 * Implements "Smart Sort" for score-based ordering.
 */
export const sortJobs = (
    jobs: JobWithEvaluation[],
    sortBy: FilterOptions['sortBy'],
    sortOrder: FilterOptions['sortOrder'],
    evaluatingJobId: string | null
): JobWithEvaluation[] => {
    return [...jobs].sort((a, b) => {
        const multiplier = sortOrder === 'asc' ? 1 : -1;

        // Smart Sort specific logic when sorting by 'score' (default)
        if (sortBy === 'score') {
            const now = Date.now();
            const NEW_THRESHOLD = 5 * 60 * 1000; // 5 minutes

            const aTime = new Date(a.updated_at || a.posted_at || 0).getTime();
            const bTime = new Date(b.updated_at || b.posted_at || 0).getTime();

            const aIsAnalyzing = a.id === evaluatingJobId;
            const bIsAnalyzing = b.id === evaluatingJobId;
            // "New" only applies to unevaluated jobs
            const aIsNew = !a.isEvaluated && (now - aTime) < NEW_THRESHOLD;
            const bIsNew = !b.isEvaluated && (now - bTime) < NEW_THRESHOLD;

            const aPinned = aIsAnalyzing || aIsNew;
            const bPinned = bIsAnalyzing || bIsNew;

            // Tier 1: Pinned (Analyzing or Just Imported)
            if (aPinned && !bPinned) return -1;
            if (!aPinned && bPinned) return 1;
            if (aPinned && bPinned) return bTime - aTime; // Newest pinned first

            // Tier 2: Evaluated (Score desc) vs Unevaluated
            const aHasEval = a.isEvaluated && a.evaluation?.job_match_score != null;
            const bHasEval = b.isEvaluated && b.evaluation?.job_match_score != null;

            if (aHasEval && !bHasEval) return -1 * multiplier;
            if (!aHasEval && bHasEval) return 1 * multiplier;

            if (aHasEval && bHasEval) {
                // Both evaluated: Sort by Score
                const scoreA = a.evaluation?.job_match_score || 0;
                const scoreB = b.evaluation?.job_match_score || 0;
                if (scoreA !== scoreB) return (scoreB - scoreA) * multiplier;
            }

            // Tier 3: Both Unevaluated (or same score) -> Sort by Time
            return (bTime - aTime) * multiplier;
        }

        // Standard sorts for other columns
        switch (sortBy) {
            case 'company':
                return ((a.company_name || '').localeCompare(b.company_name || '')) * multiplier;
            case 'date':
                return ((b.posted_at || '').localeCompare(a.posted_at || '')) * multiplier;
            default:
                return 0;
        }
    });
};
