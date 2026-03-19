import React from 'react';

interface ToastProps {
    message: string;
    type: 'error' | 'success';
    onDismiss: () => void;
    /** When provided, renders a "Retry" button alongside dismiss. Used for rollback pattern. */
    onRetry?: () => void;
}

export const Toast: React.FC<ToastProps> = ({ message, type, onDismiss, onRetry }) => (
    <div
        className={`fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg text-[13px] font-medium ${
            type === 'error'
                ? 'bg-semantic-red/10 border border-semantic-red/20 text-semantic-red'
                : 'bg-semantic-green/10 border border-semantic-green/20 text-semantic-green'
        }`}
    >
        {message}
        {onRetry && (
            <button
                onClick={onRetry}
                className="underline underline-offset-2 opacity-80 hover:opacity-100 ml-1"
            >
                Retry
            </button>
        )}
        <button onClick={onDismiss} className="text-current opacity-50 hover:opacity-100 ml-1">✕</button>
    </div>
);
