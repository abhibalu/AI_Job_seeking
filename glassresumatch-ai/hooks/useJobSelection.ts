import { useState } from 'react';
import { deleteJobs, getAllJobIds } from '../services/jobService';
import { FilterOptions, JobWithEvaluation } from '../types'; // Adjust imports if types are elsewhere

export const useJobSelection = (
    totalJobs: number,
    jobs: JobWithEvaluation[], // Current page jobs
    filters: FilterOptions,
    onDeleteSuccess: () => void
) => {
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
    const [isDeleting, setIsDeleting] = useState(false);

    const toggleSelectJob = (id: string) => {
        const newSelected = new Set(selectedIds);
        if (newSelected.has(id)) {
            newSelected.delete(id);
        } else {
            newSelected.add(id);
        }
        setSelectedIds(newSelected);
    };

    const toggleSelectAll = async () => {
        if (selectedIds.size === totalJobs && totalJobs > 0) {
            setSelectedIds(new Set());
        } else {
            try {
                if (filters.searchQuery) {
                    // Select currently visible (or filtered set logic?)
                    // App logic was: setSelectedIds(new Set(filteredJobs.map(j => j.id)));
                    // We need 'filteredJobs' or simpler logic. Assuming 'jobs' passed is the filtered list?
                    // Actually App passed 'filteredJobs' to the UI.
                    // But here we rely on what is passed.
                    setSelectedIds(new Set(jobs.map(j => j.id)));
                } else {
                    const allIds = await getAllJobIds();
                    setSelectedIds(new Set(allIds));
                }
            } catch (err) {
                console.error("Failed to select all", err);
                alert("Failed to select all jobs");
            }
        }
    };

    const handleDeleteSelected = async () => {
        if (selectedIds.size === 0) return;
        if (!confirm(`Are you sure you want to delete ${selectedIds.size} jobs?`)) return;

        setIsDeleting(true);
        try {
            await deleteJobs(Array.from(selectedIds));
            setSelectedIds(new Set());
            onDeleteSuccess();
        } catch (err) {
            console.error('Failed to delete jobs:', err);
            alert('Failed to delete jobs');
        } finally {
            setIsDeleting(false);
        }
    };

    return {
        selectedIds,
        isDeleting,
        toggleSelectJob,
        toggleSelectAll,
        handleDeleteSelected
    };
};
