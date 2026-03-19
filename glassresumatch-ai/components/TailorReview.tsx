import React, { useState, useEffect, useCallback } from 'react';
import { TailoredResume, ResumeChange, apiClient } from '../services/apiClient';
import { ResumePreview } from './ResumePreview';
import {
    CheckCircle, XCircle, Download, FileText, ArrowLeft,
    Eye, ExternalLink, Loader2, RotateCcw, Check,
} from 'lucide-react';

interface TailorReviewProps {
    baseResume: any;
    tailoredResume: TailoredResume;
    evaluation: any;
    onClose: () => void;
    onStatusChange: () => void;
}

// ── Per-change card ──────────────────────────────────────────────────────────

const ACTION_TYPE_STYLE: Record<string, string> = {
    rephrase: 'bg-blue-50 text-blue-600',
    add:      'bg-emerald-50 text-emerald-600',
    remove:   'bg-rose-50 text-rose-600',
};

const REVIEW_BADGE: Record<string, { label: string; cls: string }> = {
    accept:        { label: 'Accepted',      cls: 'bg-emerald-50 text-emerald-700' },
    reject:        { label: 'Rejected',      cls: 'bg-rose-50 text-rose-600' },
    keep_original: { label: 'Kept original', cls: 'bg-amber-50 text-amber-600' },
};

interface ChangeCardProps {
    change: ResumeChange;
    onAction: (id: string, action: 'accept' | 'reject' | 'keep_original') => Promise<void>;
}

const ChangeCard: React.FC<ChangeCardProps> = ({ change, onAction }) => {
    const [pending, setPending] = useState<string | null>(null);

    const handle = async (action: 'accept' | 'reject' | 'keep_original') => {
        setPending(action);
        await onAction(change.id, action);
        setPending(null);
    };

    const reviewed = change.review_action !== null;
    const badge = change.review_action ? REVIEW_BADGE[change.review_action] : null;

    return (
        <div className={`rounded-xl border p-4 transition-colors ${reviewed ? 'bg-slate-50 border-slate-100' : 'bg-white border-slate-200'}`}>
            {/* Meta row */}
            <div className="flex items-center gap-2 mb-2.5 flex-wrap">
                <span className="font-mono text-[10px] text-slate-400 truncate max-w-[140px]" title={change.location}>
                    {change.location}
                </span>
                <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${ACTION_TYPE_STYLE[change.action_type] ?? 'bg-slate-100 text-slate-500'}`}>
                    {change.action_type}
                </span>
                {badge && (
                    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${badge.cls}`}>
                        {badge.label}
                    </span>
                )}
                {change.confidence !== null && (
                    <span className="text-[10px] text-slate-300 ml-auto">
                        {Math.round(change.confidence * 100)}% conf
                    </span>
                )}
            </div>

            {/* Text diff */}
            {change.original_text && change.action_type !== 'add' && (
                <p className={`text-[12px] leading-relaxed mb-1 ${
                    change.review_action === 'keep_original'
                        ? 'text-slate-700'
                        : 'text-slate-400 line-through'
                }`}>
                    {change.original_text}
                </p>
            )}
            {change.tailored_text && (
                <p className={`text-[12px] leading-relaxed ${
                    change.review_action === 'reject' || change.review_action === 'keep_original'
                        ? 'text-slate-300 line-through'
                        : 'text-slate-800'
                }`}>
                    {change.tailored_text}
                </p>
            )}

            {/* Reason */}
            {change.reason && (
                <p className="text-[11px] text-slate-400 italic mt-2">{change.reason}</p>
            )}

            {/* Action buttons — hidden once reviewed */}
            {!reviewed && (
                <div className="flex gap-1.5 mt-3">
                    <button
                        onClick={() => handle('accept')}
                        disabled={!!pending}
                        className="flex items-center gap-1 px-2.5 py-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 text-[11px] font-medium rounded-md transition-colors disabled:opacity-50"
                    >
                        {pending === 'accept'
                            ? <Loader2 className="w-3 h-3 animate-spin" />
                            : <Check className="w-3 h-3" />}
                        Accept
                    </button>
                    <button
                        onClick={() => handle('reject')}
                        disabled={!!pending}
                        className="flex items-center gap-1 px-2.5 py-1 bg-rose-50 hover:bg-rose-100 text-rose-600 text-[11px] font-medium rounded-md transition-colors disabled:opacity-50"
                    >
                        {pending === 'reject'
                            ? <Loader2 className="w-3 h-3 animate-spin" />
                            : <XCircle className="w-3 h-3" />}
                        Reject
                    </button>
                    <button
                        onClick={() => handle('keep_original')}
                        disabled={!!pending}
                        className="flex items-center gap-1 px-2.5 py-1 bg-amber-50 hover:bg-amber-100 text-amber-600 text-[11px] font-medium rounded-md transition-colors disabled:opacity-50"
                    >
                        {pending === 'keep_original'
                            ? <Loader2 className="w-3 h-3 animate-spin" />
                            : <RotateCcw className="w-3 h-3" />}
                        Keep original
                    </button>
                </div>
            )}
        </div>
    );
};

// ── Main component ───────────────────────────────────────────────────────────

export const TailorReview: React.FC<TailorReviewProps> = ({
    baseResume, tailoredResume, evaluation, onClose, onStatusChange,
}) => {
    const [status, setStatus] = useState<'pending' | 'approved' | 'rejected' | 'needs_review'>(
        tailoredResume?.status || 'pending'
    );
    const [viewMode, setViewMode] = useState<'diff' | 'final'>('diff');
    const [isUpdating, setIsUpdating] = useState(false);
    const [isDownloading, setIsDownloading] = useState(false);
    const [isExportingDoc, setIsExportingDoc] = useState(false);
    const [exportedDocUrl, setExportedDocUrl] = useState<string | null>(null);

    // Per-change review state
    const [changes, setChanges] = useState<ResumeChange[]>([]);
    const [changesLoading, setChangesLoading] = useState(true);
    const [bulkAccepting, setBulkAccepting] = useState(false);

    // Cover letter state
    const [coverLetter, setCoverLetter] = useState(tailoredResume?.cover_letter ?? '');
    const [savingCL, setSavingCL] = useState(false);

    // Fetch changes on mount
    useEffect(() => {
        setChangesLoading(true);
        apiClient.getResumeChanges(tailoredResume.id)
            .then(setChanges)
            .catch(() => {})
            .finally(() => setChangesLoading(false));
    }, [tailoredResume.id]);

    const handleChangeAction = useCallback(async (
        changeId: string,
        action: 'accept' | 'reject' | 'keep_original',
    ) => {
        await apiClient.applyChangeAction(tailoredResume.id, changeId, action);
        setChanges(prev => prev.map(c =>
            c.id === changeId
                ? {
                    ...c,
                    review_action: action,
                    accepted_text: action === 'keep_original' ? c.original_text : c.tailored_text,
                  }
                : c
        ));
    }, [tailoredResume.id]);

    const handleBulkAccept = async () => {
        setBulkAccepting(true);
        try {
            await apiClient.applyBulkChangeAction(tailoredResume.id, 'accept', 'remaining');
            // Refresh changes to reflect server state
            const updated = await apiClient.getResumeChanges(tailoredResume.id);
            setChanges(updated);
        } catch {}
        finally { setBulkAccepting(false); }
    };

    const handleCoverLetterBlur = async () => {
        setSavingCL(true);
        try {
            await apiClient.updateCoverLetter(tailoredResume.id, coverLetter);
        } catch {}
        finally { setSavingCL(false); }
    };

    const handleUpdateStatus = async (newStatus: 'approved' | 'rejected') => {
        setIsUpdating(true);
        try {
            await apiClient.updateTailoredStatus(tailoredResume.id, newStatus);
            setStatus(newStatus);
            onStatusChange();
        } catch {}
        finally { setIsUpdating(false); }
    };

    const handleDownload = async () => {
        setIsDownloading(true);
        try {
            const company = evaluation?.company_name || 'Tailored';
            const blob = await apiClient.generatePdf(tailoredResume.content, 'modern');
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Resume_${company.replace(/\s+/g, '_')}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch {}
        finally { setIsDownloading(false); }
    };

    const handleExportToDoc = async () => {
        setIsExportingDoc(true);
        try {
            const result = await apiClient.exportToGoogleDocs(tailoredResume.job_id);
            if (result.url) {
                setExportedDocUrl(result.url);
                window.open(result.url, '_blank');
            }
        } catch {}
        finally { setIsExportingDoc(false); }
    };

    const remainingCount = changes.filter(c => c.review_action === null).length;

    return (
        <div className="fixed inset-0 z-[60] bg-white flex flex-col animate-in fade-in duration-200">
            {/* Header */}
            <div className="h-16 border-b border-gray-100 flex items-center justify-between px-6 bg-white flex-shrink-0">
                <div className="flex items-center space-x-4">
                    <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full transition-colors">
                        <ArrowLeft className="w-5 h-5 text-slate-900" />
                    </button>
                    <div>
                        <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                            Tailoring Review
                            <span className="text-xs font-normal px-2 py-0.5 bg-gray-100 rounded text-slate-600 border border-gray-200">
                                V{tailoredResume?.version || 1}
                            </span>
                            {status === 'approved' && (
                                <span className="text-xs font-bold px-2 py-0.5 bg-slate-900 text-white rounded flex items-center gap-1">
                                    <CheckCircle className="w-3 h-3" /> Approved
                                </span>
                            )}
                            {status === 'rejected' && (
                                <span className="text-xs font-bold px-2 py-0.5 bg-white border border-slate-200 text-slate-500 rounded flex items-center gap-1">
                                    <XCircle className="w-3 h-3" /> Rejected
                                </span>
                            )}
                        </h2>
                        <p className="text-xs text-slate-500">
                            {evaluation?.title_role} · {evaluation?.company_name}
                        </p>
                    </div>
                </div>

                <div className="flex items-center space-x-3">
                    {/* Preview toggle */}
                    <div className="flex items-center bg-gray-100 rounded-lg p-1 border border-gray-200">
                        <button
                            onClick={() => setViewMode('diff')}
                            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all flex items-center ${viewMode === 'diff' ? 'bg-white text-black shadow-sm' : 'text-slate-500 hover:text-black'}`}
                        >
                            <Eye className="w-4 h-4 mr-2" />Diff
                        </button>
                        <button
                            onClick={() => setViewMode('final')}
                            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all flex items-center ${viewMode === 'final' ? 'bg-white text-black shadow-sm' : 'text-slate-500 hover:text-black'}`}
                        >
                            <FileText className="w-4 h-4 mr-2" />Final
                        </button>
                    </div>

                    {status === 'approved' ? (
                        <>
                            {exportedDocUrl ? (
                                <a
                                    href={exportedDocUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="px-4 py-2 bg-white border border-slate-300 text-slate-900 rounded-md text-sm font-medium flex items-center hover:bg-slate-50 transition-colors"
                                >
                                    <ExternalLink className="w-4 h-4 mr-2" />Open Google Doc
                                </a>
                            ) : (
                                <button
                                    onClick={handleExportToDoc}
                                    disabled={isExportingDoc}
                                    className="px-4 py-2 bg-white border border-slate-300 text-slate-900 rounded-md text-sm font-medium flex items-center hover:bg-slate-50 transition-colors disabled:opacity-50"
                                >
                                    {isExportingDoc ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <FileText className="w-4 h-4 mr-2" />}
                                    {isExportingDoc ? 'Exporting…' : 'Export to Google Docs'}
                                </button>
                            )}
                            <button
                                onClick={handleDownload}
                                disabled={isDownloading}
                                className="px-4 py-2 bg-black hover:bg-slate-800 text-white rounded-md text-sm font-medium flex items-center shadow-sm disabled:opacity-50 border border-black"
                            >
                                {isDownloading
                                    ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
                                    : <Download className="w-4 h-4 mr-2" />}
                                Download PDF
                            </button>
                        </>
                    ) : (
                        <>
                            <button
                                onClick={() => handleUpdateStatus('rejected')}
                                disabled={isUpdating}
                                className="px-4 py-2 border border-slate-300 text-slate-700 hover:bg-gray-50 rounded-md text-sm font-medium flex items-center disabled:opacity-50"
                            >
                                <XCircle className="w-4 h-4 mr-2" />Reject
                            </button>
                            <button
                                onClick={() => handleUpdateStatus('approved')}
                                disabled={isUpdating}
                                className="px-4 py-2 bg-black hover:bg-slate-800 text-white rounded-md text-sm font-medium flex items-center shadow-sm disabled:opacity-50 border border-black"
                            >
                                <CheckCircle className="w-4 h-4 mr-2" />Approve
                            </button>
                        </>
                    )}
                </div>
            </div>

            {/* Body: changes panel + resume preview */}
            <div className="flex-1 flex overflow-hidden">

                {/* Left: per-change review + cover letter */}
                <div className="w-[420px] flex-shrink-0 flex flex-col border-r border-slate-100 overflow-hidden">

                    {/* Changes list — scrollable */}
                    <div className="flex-1 overflow-y-auto p-4 space-y-3">
                        {changesLoading ? (
                            <div className="flex items-center justify-center py-12 text-slate-300">
                                <Loader2 className="w-5 h-5 animate-spin mr-2" />
                                <span className="text-sm">Loading changes…</span>
                            </div>
                        ) : changes.length === 0 ? (
                            <div className="py-12 text-center text-slate-400 text-sm">
                                No per-change records for this resume.
                            </div>
                        ) : (
                            <>
                                <p className="text-[11px] text-slate-400 font-medium uppercase tracking-wider px-1">
                                    {changes.length} change{changes.length !== 1 ? 's' : ''} · {remainingCount} pending
                                </p>
                                {changes.map(c => (
                                    <ChangeCard key={c.id} change={c} onAction={handleChangeAction} />
                                ))}
                            </>
                        )}

                        {/* Cover letter */}
                        <div className="mt-6 pb-2">
                            <div className="flex items-center justify-between mb-1.5">
                                <label className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">
                                    Cover Letter
                                </label>
                                {savingCL && (
                                    <span className="text-[10px] text-slate-300 flex items-center gap-1">
                                        <Loader2 className="w-3 h-3 animate-spin" /> Saving…
                                    </span>
                                )}
                            </div>
                            <textarea
                                className="w-full min-h-[200px] text-[12px] leading-relaxed text-slate-700 bg-white border border-slate-200 rounded-xl p-3 resize-y focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400 transition-colors placeholder:text-slate-300"
                                placeholder="AI-generated cover letter will appear here…"
                                value={coverLetter}
                                onChange={e => setCoverLetter(e.target.value)}
                                onBlur={handleCoverLetterBlur}
                            />
                        </div>
                    </div>

                    {/* Sticky footer: bulk accept */}
                    <div className="border-t border-slate-100 px-4 py-3 flex items-center justify-between bg-white flex-shrink-0">
                        <span className="text-[11px] text-slate-400">
                            {remainingCount > 0 ? `${remainingCount} unreviewed` : 'All reviewed'}
                        </span>
                        <button
                            onClick={handleBulkAccept}
                            disabled={bulkAccepting || remainingCount === 0}
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 hover:bg-slate-700 text-white text-[12px] font-medium rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                            {bulkAccepting
                                ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                : <Check className="w-3.5 h-3.5" />}
                            Accept all remaining →
                        </button>
                    </div>
                </div>

                {/* Right: resume preview */}
                <div className="flex-1 overflow-y-auto bg-slate-100 p-8 flex justify-center">
                    <div className="transform scale-[0.85] origin-top">
                        <ResumePreview
                            data={{
                                ...tailoredResume.content,
                                skills: tailoredResume.content.skills?.map((s: any) => {
                                    if (typeof s === 'string') return s;
                                    return s.keywords?.length > 0
                                        ? `${s.name}: ${s.keywords.join(', ')}`
                                        : s.name;
                                }) || [],
                            }}
                            originalData={viewMode === 'diff' ? baseResume : undefined}
                            template="ats_friendly"
                        />
                    </div>
                </div>
            </div>
        </div>
    );
};
