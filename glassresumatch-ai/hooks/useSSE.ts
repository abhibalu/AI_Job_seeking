import { useEffect, useRef } from 'react';

const API_BASE_URL = 'http://localhost:8000';

export interface SSEProgressEvent {
    task_id: string;
    status: 'queued' | 'running';
    progress: { completed: number; total: number; failed?: number } | null;
}

export interface SSERunCompleteEvent {
    task_id: string;
    status: 'completed' | 'failed';
    progress?: { completed: number; total: number; failed?: number } | null;
    error?: string | null;
}

interface UseSSEHandlers {
    onProgress?: (event: SSEProgressEvent) => void;
    onRunComplete?: (event: SSERunCompleteEvent) => void;
    onError?: (err: Event) => void;
}

/**
 * Subscribe to SSE progress stream for a task.
 * Opens EventSource when taskId is non-null, closes on cleanup or run_complete.
 * Native EventSource auto-reconnects on transient errors (ADR-0009).
 */
export function useSSE(taskId: string | null, handlers: UseSSEHandlers) {
    // Stable ref so effect doesn't re-run when handler identity changes
    const handlersRef = useRef(handlers);
    useEffect(() => { handlersRef.current = handlers; }, [handlers]);

    useEffect(() => {
        if (!taskId) return;

        const url = `${API_BASE_URL}/api/events/stream?task_id=${encodeURIComponent(taskId)}`;
        const es = new EventSource(url);

        es.addEventListener('progress', (e) => {
            try {
                const data = JSON.parse((e as MessageEvent).data) as SSEProgressEvent;
                handlersRef.current.onProgress?.(data);
            } catch {}
        });

        es.addEventListener('run_complete', (e) => {
            try {
                const data = JSON.parse((e as MessageEvent).data) as SSERunCompleteEvent;
                handlersRef.current.onRunComplete?.(data);
            } catch {}
            es.close();
        });

        es.onerror = (err) => {
            handlersRef.current.onError?.(err);
            // EventSource reconnects automatically — do not close here
        };

        return () => {
            es.close();
        };
    }, [taskId]); // re-open only when taskId changes
}
