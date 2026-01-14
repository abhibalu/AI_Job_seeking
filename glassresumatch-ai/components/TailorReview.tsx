import React, { useState, useEffect } from 'react';
import { TailoredResume, apiClient } from '../services/apiClient';
import { ResumePreview } from './ResumePreview';
import { CheckCircle, XCircle, Download, FileText, ArrowLeft, Eye, EyeOff } from 'lucide-react';

interface TailorReviewProps {
    baseResume: any;
    tailoredResume: TailoredResume;
    evaluation: any;
    onClose: () => void;
    onStatusChange: () => void;
}

export const TailorReview: React.FC<TailorReviewProps> = ({ baseResume, tailoredResume, evaluation, onClose, onStatusChange }) => {
    const [status, setStatus] = useState<'pending' | 'approved' | 'rejected'>(tailoredResume.status);
    const [viewMode, setViewMode] = useState<'diff' | 'final'>('diff');
    const [isUpdating, setIsUpdating] = useState(false);
    const [isDownloading, setIsDownloading] = useState(false);

    const handleUpdateStatus = async (newStatus: 'approved' | 'rejected') => {
        setIsUpdating(true);
        try {
            await apiClient.updateTailoredStatus(tailoredResume.id, newStatus);
            setStatus(newStatus);
            onStatusChange();
        } catch (error) {
            console.error("Failed to update status:", error);
        } finally {
            setIsUpdating(false);
        }
    };

    const handleDownload = async () => {
        setIsDownloading(true);
        try {
            // Use the tailored company name for filename if available, else 'Tailored'
            const company = evaluation?.company_name || 'Tailored';
            const blob = await apiClient.generatePdf(tailoredResume.content, 'modern'); // Default to modern for now
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Abhijith_Sivadas_${company.replace(/\s+/g, '_')}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            console.error("Download failed:", error);
        } finally {
            setIsDownloading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-[60] bg-white flex flex-col animate-in fade-in duration-200">
            {/* Header */}
            <div className="h-16 border-b border-gray-100 flex items-center justify-between px-6 bg-white">
                <div className="flex items-center space-x-4">
                    <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full transition-colors">
                        <ArrowLeft className="w-5 h-5 text-slate-900" />
                    </button>
                    <div>
                        <h2 className="text-lg font-bold text-slate-900 flex items-center">
                            Tailored Resume
                            <span className="ml-3 text-xs font-normal px-2 py-0.5 bg-gray-100 rounded text-slate-600 border border-gray-200">
                                V{tailoredResume.version}
                            </span>
                            {status === 'approved' && (
                                <span className="ml-2 text-xs font-bold px-2 py-0.5 bg-slate-900 text-white rounded flex items-center">
                                    <CheckCircle className="w-3 h-3 mr-1" /> Approved
                                </span>
                            )}
                            {status === 'rejected' && (
                                <span className="ml-2 text-xs font-bold px-2 py-0.5 bg-white border border-slate-200 text-slate-500 rounded flex items-center">
                                    <XCircle className="w-3 h-3 mr-1" /> Rejected
                                </span>
                            )}
                        </h2>
                        <p className="text-xs text-slate-500">
                            For {evaluation?.title_role} at {evaluation?.company_name}
                        </p>
                    </div>
                </div>

                <div className="flex items-center space-x-3">
                    {/* View Toggle */}
                    <div className="flex items-center bg-gray-100 rounded-lg p-1 mr-4 border border-gray-200">
                        <button
                            onClick={() => setViewMode('diff')}
                            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all flex items-center ${viewMode === 'diff' ? 'bg-white text-black shadow-sm' : 'text-slate-500 hover:text-black'}`}
                        >
                            <Eye className="w-4 h-4 mr-2" />
                            Diff View
                        </button>
                        <button
                            onClick={() => setViewMode('final')}
                            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all flex items-center ${viewMode === 'final' ? 'bg-white text-black shadow-sm' : 'text-slate-500 hover:text-black'}`}
                        >
                            <FileText className="w-4 h-4 mr-2" />
                            Final Preview
                        </button>
                    </div>

                    {status === 'approved' ? (
                        <button
                            onClick={handleDownload}
                            disabled={isDownloading}
                            className="px-4 py-2 bg-black hover:bg-slate-800 text-white rounded-md text-sm font-medium flex items-center shadow-sm disabled:opacity-50 border border-black"
                        >
                            {isDownloading ? (
                                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
                            ) : (
                                <Download className="w-4 h-4 mr-2" />
                            )}
                            Download PDF
                        </button>
                    ) : (
                        <>
                            <button
                                onClick={() => handleUpdateStatus('rejected')}
                                disabled={isUpdating}
                                className="px-4 py-2 border border-slate-300 text-slate-700 hover:bg-gray-50 rounded-md text-sm font-medium flex items-center disabled:opacity-50"
                            >
                                <XCircle className="w-4 h-4 mr-2" />
                                Reject
                            </button>
                            <button
                                onClick={() => handleUpdateStatus('approved')}
                                disabled={isUpdating}
                                className="px-4 py-2 bg-black hover:bg-slate-800 text-white rounded-md text-sm font-medium flex items-center shadow-sm disabled:opacity-50 border border-black"
                            >
                                <CheckCircle className="w-4 h-4 mr-2" />
                                Approve
                            </button>
                        </>
                    )}
                </div>
            </div>

            {/* Content Preview */}
            <div className="flex-1 overflow-y-auto bg-slate-100 p-8 flex justify-center">
                <div className="transform scale-[0.85] origin-top">
                    {/* 
                        If Diff View: pass originalData 
                        If Final View: pass undefined originalData (so no highlights)
                    */}
                    <ResumePreview
                        data={tailoredResume.content}
                        originalData={viewMode === 'diff' ? baseResume : undefined}
                    />
                </div>
            </div>
        </div>
    );
};
