import React from 'react';
import { AlertTriangle } from 'lucide-react';

interface AutoSendModalProps {
    /** The threshold value (1–4) the slider was moved to. */
    threshold: number;
    onConfirm: () => void;
    onCancel: () => void;
}

/**
 * Consent modal shown when auto_send_threshold slider moves above 0.
 * Per ADR-0012: slider alone is not consent. Modal forces deliberate confirmation.
 */
export const AutoSendModal: React.FC<AutoSendModalProps> = ({ threshold, onConfirm, onCancel }) => (
    <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/20 backdrop-blur-sm"
        onClick={onCancel}
    >
        <div
            className="bg-white rounded-2xl shadow-xl w-[440px] p-6 border border-slate-200"
            onClick={e => e.stopPropagation()}
        >
            <div className="flex items-start gap-3 mb-4">
                <div className="w-9 h-9 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center flex-shrink-0">
                    <AlertTriangle className="w-4.5 h-4.5 text-amber-600" />
                </div>
                <div>
                    <h2 className="text-[15px] font-bold text-slate-900">Enable auto-send?</h2>
                    <p className="text-[12px] text-slate-500 mt-0.5">This requires your explicit confirmation</p>
                </div>
            </div>

            <p className="text-[13px] text-slate-600 leading-relaxed mb-6">
                CVs will be sent to employers <strong>without your review</strong> for jobs
                scoring <strong>{threshold}/4 or above</strong>. You can disable auto-send at
                any time from Settings.
            </p>

            <div className="flex justify-end gap-2.5">
                <button
                    onClick={onCancel}
                    className="px-4 py-2 text-[13px] font-medium text-slate-600 hover:text-slate-900 border border-slate-200 hover:border-slate-300 rounded-lg transition-colors"
                >
                    Cancel — keep at 0
                </button>
                <button
                    onClick={onConfirm}
                    className="px-4 py-2 text-[13px] font-medium bg-amber-500 hover:bg-amber-600 text-white rounded-lg transition-colors shadow-sm"
                >
                    Confirm — enable auto-send
                </button>
            </div>
        </div>
    </div>
);
