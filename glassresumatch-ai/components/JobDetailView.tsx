import React, { useState, useEffect } from 'react';
import { Evaluation, ParseResult, TailoredResume, apiClient } from '../services/apiClient';
import { parseJobDescription, getParsedJD, evaluateJob } from '../services/jobService';
import {
    CheckCircle, AlertTriangle, XCircle, FileText,
    Lightbulb, Target, MessageSquare, Sparkles, ChevronDown, ChevronUp,
    BookOpen, Zap, HelpCircle, ExternalLink, RefreshCw, Wand2,
    Share2, Bookmark, MapPin, Clock, Download, Loader2
} from 'lucide-react';
import { TailorReview } from './TailorReview';
import { ResumePreview } from './ResumePreview';
import { JobWithEvaluation } from '../services/jobService';
import { formatTimeAgo } from '../utils/format';

import { logger } from '../utils/logger';

interface JobDetailViewProps {
    job: JobWithEvaluation;
    onEvaluate?: () => void;
}

export const JobDetailView: React.FC<JobDetailViewProps> = ({ job, onEvaluate }) => {
    const [parsedJD, setParsedJD] = useState<ParseResult | null>(null);
    const [isParsing, setIsParsing] = useState(false);
    const [showInterviewTips, setShowInterviewTips] = useState(true); // Default open in detail view
    const [showSuggestions, setShowSuggestions] = useState(true);
    const [isReEvaluating, setIsReEvaluating] = useState(false);
    const [isTailoring, setIsTailoring] = useState(false);
    const [tailoredResume, setTailoredResume] = useState<TailoredResume | null>(null);
    const [baseResume, setBaseResume] = useState<any>(null);

    // Simulation State
    const [isSimulatedModalOpen, setIsSimulatedModalOpen] = useState(false);
    const [isReviewOpen, setIsReviewOpen] = useState(false); // Controls TailorReview visibility
    const [isGeneratingResume, setIsGeneratingResume] = useState(false);
    const [hasGeneratedResume, setHasGeneratedResume] = useState(false);
    const [simulationStatus, setSimulationStatus] = useState<'pending' | 'approved'>('pending');
    const [viewMode, setViewMode] = useState<'diff' | 'final'>('diff');

    const evaluation = job.evaluation;
    const isEvaluated = job.isEvaluated && !!evaluation;

    // Reset states when job changes
    useEffect(() => {
        logger.info('JobDetailView', 'Job selected/changed', { jobId: job.id, title: job.title });

        setParsedJD(null);
        setTailoredResume(null);
        setHasGeneratedResume(false);
        setIsGeneratingResume(false);
        setSimulationStatus('pending');
        setViewMode('diff');
        setIsReEvaluating(false);
        setIsReviewOpen(false); // Fix: Ensure modal is closed by default

        // Check for existing tailored resume in Supabase
        const checkExistingTailored = async () => {
            try {
                logger.debug('JobDetailView', 'Checking for existing tailored resumes', { jobId: job.id });
                const versions = await apiClient.getTailoredVersions(job.id);
                if (versions && versions.length > 0) {
                    logger.info('JobDetailView', 'Found existing tailored resume', { version: versions[0].version });
                    // Use the most recent version
                    const latest = versions[0];
                    setTailoredResume(latest);
                    setHasGeneratedResume(true);

                    // Also fetch base resume for diff view
                    const base = await apiClient.getMasterResume();
                    setBaseResume(base);
                } else {
                    logger.debug('JobDetailView', 'No tailored resume found');
                }
            } catch (e) {
                // No existing tailored resume, that's fine
                logger.warn('JobDetailView', 'Error checking tailored resumes', e);
            }
        };

        if (job.id) {
            checkExistingTailored();
        }
    }, [job.id]);



    const handleTailorJob = async () => {
        logger.info('JobDetailView', 'Tailor resume requested', { jobId: job.id });
        setIsGeneratingResume(true);
        // Ensure we have base resume for Diff View
        if (!baseResume) {
            try {
                const base = await apiClient.getMasterResume();
                setBaseResume(base);
            } catch (e) {
                logger.error('JobDetailView', "Could not fetch base resume", e);
            }
        }

        try {
            const result = await apiClient.tailorResume(job.id);
            logger.info('JobDetailView', 'Tailoring successful', { id: result.id, version: result.version });
            setTailoredResume(result);
            setHasGeneratedResume(true);
            setIsReviewOpen(true); // Open the review modal
        } catch (error: any) {
            logger.error('JobDetailView', "Tailoring failed", error);
            // Try to get error message from API response
            const errorMessage = error?.message || error?.detail || "Failed to tailor resume. Please check the backend.";
            alert(errorMessage);
        } finally {
            setIsGeneratingResume(false);
        }
    };

    // Check for existing tailored versions logic
    // (Simplified: we just let them tailor if recommended)

    const handleTailor = async () => {
        setIsTailoring(true);
        try {
            let base = baseResume;
            if (!base) {
                base = await apiClient.getMasterResume();
                setBaseResume(base);
            }
            const result = await apiClient.tailorResume(job.id);
            setTailoredResume(result);
        } catch (error) {
            console.error("Tailoring failed:", error);
            alert("Failed to tailor resume. See console.");
        } finally {
            setIsTailoring(false);
        }
    };

    const handleReEvaluate = async () => {
        if (!job.id) return;
        setIsReEvaluating(true);
        try {
            await evaluateJob(job.id, true);
            onEvaluate?.();
        } catch (error) {
            console.error('Failed to re-evaluate:', error);
        } finally {
            setIsReEvaluating(false);
        }
    };

    const handleEvaluateFresh = async () => {
        setIsReEvaluating(true); // Reuse loading state
        try {
            await evaluateJob(job.id);
            onEvaluate?.();
        } catch (error) {
            console.error("Evaluation failed", error);
        } finally {
            setIsReEvaluating(false);
        }
    };

    const handleParseJD = async () => {
        if (!job.id) return;
        setIsParsing(true);
        try {
            await parseJobDescription(job.id, false);
            const result = await getParsedJD(job.id);
            setParsedJD(result);
        } catch (error) {
            console.error('Failed to parse JD:', error);
        } finally {
            setIsParsing(false);
        }
    };

    const getScoreColor = (score: number | null) => {
        if (!score) return 'text-slate-400';
        if (score >= 80) return 'text-emerald-600';
        if (score >= 50) return 'text-amber-600';
        return 'text-rose-600';
    };

    const getLogoColor = (name: string = '') => {
        const colors = [
            'from-blue-400 to-blue-600',
            'from-emerald-400 to-emerald-600',
            'from-purple-400 to-purple-600',
            'from-amber-400 to-amber-600',
            'from-rose-400 to-rose-600',
            'from-indigo-400 to-indigo-600',
        ];
        let hash = 0;
        for (let i = 0; i < name.length; i++) {
            hash = name.charCodeAt(i) + ((hash << 5) - hash);
        }
        return colors[Math.abs(hash) % colors.length];
    };

    return (
        <div className="h-full flex flex-col bg-white">
            {isReviewOpen && tailoredResume && baseResume && evaluation && (
                <TailorReview
                    baseResume={baseResume}
                    tailoredResume={tailoredResume}
                    evaluation={evaluation}
                    onClose={() => setIsReviewOpen(false)}
                    onStatusChange={() => { }}
                />
            )}

            {/* Header / Hero */}
            <div className="px-6 pt-6 pb-4 border-b border-gray-100 sticky top-0 bg-white z-10 shadow-sm animate-in slide-in-from-top-2">
                <div className="flex items-start justify-between">
                    <div className="flex gap-4">
                        <div className="w-16 h-16 rounded-lg bg-slate-900 flex items-center justify-center text-white font-bold text-3xl shadow-sm shrink-0 border border-slate-900">
                            {job.company_name?.charAt(0) || 'C'}
                        </div>
                        <div>
                            {job.job_url ? (
                                <a
                                    href={job.job_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="hover:underline hover:text-blue-700 transition-colors flex items-center gap-2 group"
                                >
                                    <h1 className="text-2xl font-bold text-slate-900 leading-tight group-hover:text-blue-700">{job.title}</h1>
                                    <ExternalLink className="w-5 h-5 text-slate-400 group-hover:text-blue-600 opacity-0 group-hover:opacity-100 transition-all" />
                                </a>
                            ) : (
                                <h1 className="text-2xl font-bold text-slate-900 leading-tight">{job.title}</h1>
                            )}
                            <div className="flex items-center flex-wrap gap-2 text-slate-600 mt-1 text-sm">
                                {job.company_website ? (
                                    <a
                                        href={job.company_website}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="font-medium hover:underline cursor-pointer text-slate-900 decoration-slate-400 decoration-1 underline-offset-2 transition-all hover:text-black flex items-center gap-1 group"
                                        title="Visit Company Website"
                                    >
                                        {job.company_name}
                                        <ExternalLink className="w-3 h-3 text-slate-400 group-hover:text-black" />
                                    </a>
                                ) : (
                                    <span className="font-medium text-slate-900">{job.company_name}</span>
                                )}
                                <span>•</span>
                                <span className="flex items-center gap-1"><MapPin className="w-3.5 h-3.5" /> {job.location || 'Location not specified'}</span>
                                <span>•</span>
                                {job.posted_at && (
                                    <span className="text-slate-600 font-medium flex items-center gap-1">
                                        <Clock size={12} />
                                        {formatTimeAgo(job.posted_at)}
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>

                    <div className="flex gap-3">
                        <button className="p-2 text-slate-500 hover:bg-gray-100 rounded-full transition-colors" title="Share">
                            <Share2 className="w-5 h-5" />
                        </button>
                        <button className="p-2 text-slate-500 hover:bg-gray-100 rounded-full transition-colors" title="Save">
                            <Bookmark className="w-5 h-5" />
                        </button>
                    </div>
                </div>

                {/* Action Bar */}
                <div className="flex items-center gap-3 mt-6">
                    {isEvaluated && evaluation?.recommended_action === 'tailor' && (
                        <button
                            onClick={() => hasGeneratedResume ? setIsReviewOpen(true) : handleTailorJob()}
                            disabled={isGeneratingResume}
                            className="px-6 py-2 bg-white hover:bg-slate-50 text-black font-semibold rounded-md transition-colors flex items-center gap-2 shadow-sm disabled:opacity-70 border border-black"
                        >
                            {isGeneratingResume ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    Generating...
                                </>
                            ) : hasGeneratedResume ? (
                                <>
                                    <FileText className="w-4 h-4" />
                                    View Resume
                                </>
                            ) : (
                                <>
                                    <Wand2 className="w-4 h-4" />
                                    Tailor Resume
                                </>
                            )}
                        </button>
                    )}

                    {evaluation?.job_url && (
                        <a
                            href={evaluation.job_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="px-6 py-2 border border-black text-black font-medium rounded-md hover:bg-gray-50 transition-colors flex items-center gap-2"
                        >
                            Apply Now
                            <ExternalLink className="w-4 h-4" />
                        </a>
                    )}

                    {!isEvaluated && (
                        <button
                            onClick={handleEvaluateFresh}
                            disabled={isReEvaluating}
                            className="px-6 py-2 bg-black hover:bg-slate-800 text-white font-medium rounded-md transition-colors flex items-center gap-2"
                        >
                            {isReEvaluating ? 'Evaluating...' : 'Analyze Match'}
                            <Sparkles className="w-4 h-4" />
                        </button>
                    )}
                </div>
            </div>

            {/* Scrollable Content */}
            <div className="flex-1 overflow-y-auto px-6 py-6 space-y-8 bg-white">

                {/* Match Analysis Section (The Core Value) */}
                {isEvaluated && evaluation ? (
                    <section className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm animate-in fade-in duration-500">
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                                <Target className="w-5 h-5 text-slate-900" />
                                AI Match Analysis
                            </h2>
                            <button
                                onClick={handleReEvaluate}
                                disabled={isReEvaluating}
                                className="text-xs text-slate-400 hover:text-black flex items-center gap-1"
                            >
                                <RefreshCw size={12} className={isReEvaluating ? 'animate-spin' : ''} />
                                Re-evaluate
                            </button>
                        </div>

                        <div className="flex flex-col md:flex-row items-start gap-6">
                            {/* Score Radial/Box */}
                            <div className="flex-shrink-0 flex flex-col items-center justify-center bg-slate-50 border border-slate-200 rounded-xl p-4 w-32">
                                <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider mb-1">Match Score</span>
                                <span className="text-4xl font-extrabold text-slate-900">
                                    {evaluation.job_match_score}%
                                </span>
                                <span className="mt-2 px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-white border border-slate-200 text-slate-900">
                                    {evaluation.verdict}
                                </span>
                            </div>

                            {/* Text Analysis */}
                            <div className="flex-1 min-w-0">
                                <p className="text-slate-800 leading-relaxed text-sm">
                                    {evaluation.summary}
                                </p>

                                {/* Action Recommendation */}
                                <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <span className="text-sm font-semibold text-slate-500">Recommendation:</span>
                                        {evaluation.recommended_action === 'tailor' ? (
                                            <span className="flex items-center text-sm font-bold text-slate-900 bg-slate-50 px-2 py-1 rounded border border-slate-200">
                                                <FileText className="w-3.5 h-3.5 mr-1.5" />
                                                Tailor Resume
                                            </span>
                                        ) : evaluation.recommended_action === 'apply' ? (
                                            <span className="flex items-center text-sm font-bold text-slate-900 bg-slate-50 px-2 py-1 rounded border border-slate-200">
                                                <CheckCircle className="w-3.5 h-3.5 mr-1.5" />
                                                Apply Immediately
                                            </span>
                                        ) : (
                                            <span className="flex items-center text-sm font-bold text-slate-900 bg-slate-50 px-2 py-1 rounded border border-slate-200">
                                                <AlertTriangle className="w-3.5 h-3.5 mr-1.5" />
                                                Skip Opportunity
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Gaps Grid */}
                        <div className="flex flex-col space-y-3 mt-6">
                            <div className="bg-slate-50 rounded-lg p-3 border border-slate-200">
                                <h4 className="text-xs font-bold text-slate-900 uppercase mb-2">Technical Gaps</h4>
                                <ul className="space-y-1">
                                    {evaluation.gaps?.technical?.length ? (
                                        evaluation.gaps.technical.map((gap, i) => (
                                            <li key={i} className="text-xs text-slate-700 flex items-start">
                                                <span className="mr-1 text-slate-400">•</span> {gap}
                                            </li>
                                        ))
                                    ) : <li className="text-xs text-slate-400">None detected</li>}
                                </ul>
                            </div>
                            <div className="bg-slate-50 rounded-lg p-3 border border-slate-200">
                                <h4 className="text-xs font-bold text-slate-900 uppercase mb-2">Domain Gaps</h4>
                                <ul className="space-y-1">
                                    {evaluation.gaps?.domain?.length ? (
                                        evaluation.gaps.domain.map((gap, i) => (
                                            <li key={i} className="text-xs text-slate-700 flex items-start">
                                                <span className="mr-1 text-slate-400">•</span> {gap}
                                            </li>
                                        ))
                                    ) : <li className="text-xs text-slate-400">None detected</li>}
                                </ul>
                            </div>
                            <div className="bg-slate-50 rounded-lg p-3 border border-slate-200">
                                <h4 className="text-xs font-bold text-slate-900 uppercase mb-2">Soft Skill Gaps</h4>
                                <ul className="space-y-1">
                                    {evaluation.gaps?.soft_skills?.length ? (
                                        evaluation.gaps.soft_skills.map((gap, i) => (
                                            <li key={i} className="text-xs text-slate-700 flex items-start">
                                                <span className="mr-1 text-slate-400">•</span> {gap}
                                            </li>
                                        ))
                                    ) : <li className="text-xs text-slate-400">None detected</li>}
                                </ul>
                            </div>
                        </div>

                    </section>
                ) : (
                    <div className="bg-white rounded-xl p-8 border border-slate-200 shadow-sm text-center">
                        <Sparkles className="w-12 h-12 text-blue-200 mx-auto mb-4" />
                        <h3 className="text-lg font-semibold text-slate-900 mb-2">Ready to Analyze</h3>
                        <p className="text-slate-500 mb-6 max-w-md mx-auto">
                            Click the analyze button above to have AI evaluate this job description against your resume and find gaps.
                        </p>
                        <button
                            onClick={handleEvaluateFresh}
                            disabled={isReEvaluating}
                            className="px-6 py-2 bg-slate-900 hover:bg-slate-800 text-white font-medium rounded-full inline-flex items-center gap-2"
                        >
                            {isReEvaluating ? 'Analyzing...' : 'Analyze Match'}
                        </button>
                    </div>
                )}

                {/* Actionable Suggestions (If Evaluated) */}
                {isEvaluated && evaluation && (
                    <section className="space-y-4">
                        <div className="flex items-center justify-between">
                            <h2 className="text-lg font-bold text-slate-900">How to Improve</h2>
                        </div>

                        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
                            {/* Interview Tips Toggle */}
                            <button
                                onClick={() => setShowInterviewTips(!showInterviewTips)}
                                className="w-full p-4 flex items-center justify-between bg-white hover:bg-slate-50 transition-colors border-b border-slate-100"
                            >
                                <h3 className="font-semibold text-slate-900 flex items-center gap-2">
                                    <Lightbulb className="w-5 h-5 text-slate-900" />
                                    Interview Preparation
                                </h3>
                                {showInterviewTips ? <ChevronUp className="w-5 h-5 text-slate-400" /> : <ChevronDown className="w-5 h-5 text-slate-400" />}
                            </button>

                            {showInterviewTips && evaluation.interview_tips && (
                                <div className="p-4 space-y-4 animate-in slide-in-from-top-2">
                                    {evaluation.interview_tips.high_priority_topics?.map((topic, i) => (
                                        <div key={i} className="flex gap-3">
                                            <div className="w-1 h-full min-h-[40px] bg-slate-900 rounded-full"></div>
                                            <div>
                                                <p className="font-bold text-slate-900 text-sm">{topic.topic}</p>
                                                <p className="text-xs text-slate-500 mt-1 mb-1">{topic.why}</p>
                                                <p className="text-xs text-slate-900 font-medium bg-slate-100 inline-block px-2 py-1 rounded">Study: {topic.prep}</p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </section>
                )}

                {/* Job Description (Rich Text) */}
                <section>
                    <h2 className="text-lg font-bold text-slate-900 mb-4">About the Job</h2>
                    <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
                        {job.description_html ? (
                            <div
                                className="prose prose-slate max-w-none text-sm text-slate-700
                             prose-headings:font-bold prose-headings:text-slate-900 
                             prose-a:text-slate-900 prose-a:underline hover:prose-a:text-black
                             prose-strong:text-slate-900 prose-strong:font-bold
                             prose-ul:list-disc prose-ul:pl-5 prose-ul:space-y-1
                             prose-ol:list-decimal prose-ol:pl-5 prose-ol:space-y-1
                             prose-li:marker:text-slate-400"
                                dangerouslySetInnerHTML={{ __html: job.description_html }}
                            />
                        ) : (
                            <div className="whitespace-pre-wrap text-sm text-slate-700 leading-relaxed font-sans">
                                {job.description_text || "No description available."}
                            </div>
                        )}
                    </div>
                </section>

                {/* Parsed JD Section */}
                <section>
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-bold text-slate-900">Job Description Analysis</h2>
                        <button
                            onClick={handleParseJD}
                            disabled={isParsing}
                            className="text-xs text-slate-900 font-medium hover:underline flex items-center gap-1"
                        >
                            {isParsing ? 'Parsing...' : 'Extract Signals'}
                            <Sparkles size={12} />
                        </button>
                    </div>

                    <div className="bg-white border border-slate-200 rounded-xl p-6">
                        {parsedJD ? (
                            <div className="space-y-6 animate-in fade-in">
                                <div>
                                    <h4 className="text-xs font-bold text-slate-400 uppercase mb-2">Must Haves</h4>
                                    <div className="flex flex-wrap gap-2">
                                        {parsedJD.must_haves?.map((req, i) => (
                                            <span key={i} className="px-2 py-1 bg-slate-100 text-slate-700 text-xs font-medium rounded">
                                                {req}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                                <div>
                                    <h4 className="text-xs font-bold text-slate-400 uppercase mb-2">ATS Keywords</h4>
                                    <div className="flex flex-wrap gap-2">
                                        {parsedJD.ats_keywords?.map((kw, i) => (
                                            <span key={i} className="px-2 py-1 bg-white text-slate-900 text-xs font-medium rounded border border-slate-200 shadow-sm">
                                                {kw}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="text-center py-8 text-slate-400 text-sm">
                                No detailed signals extracted yet.
                            </div>
                        )}
                    </div>
                </section>

            </div>

            {/* Simulated Tailor Resume Modal */}
            {isSimulatedModalOpen && (
                <div className="absolute inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
                    <div className="bg-white w-full max-w-5xl h-[95%] rounded-xl shadow-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
                        {/* Modal Header */}
                        <div className="h-16 border-b border-gray-100 flex items-center justify-between px-6 bg-white shrink-0">
                            <div className="flex items-center gap-4">
                                <h3 className="font-bold text-lg flex items-center gap-2 text-slate-900">
                                    <FileText className="w-5 h-5 text-slate-900" />
                                    Tailored Resume
                                    <span className="text-xs font-normal px-2 py-0.5 bg-gray-100 rounded text-slate-600 border border-gray-200 ml-2">
                                        Preview
                                    </span>
                                </h3>

                                {/* View Toggle */}
                                <div className="flex items-center bg-gray-100 rounded-lg p-1 border border-gray-200 h-8">
                                    <button
                                        onClick={() => setViewMode('diff')}
                                        className={`px-3 text-xs font-medium rounded-md transition-all flex items-center h-full ${viewMode === 'diff' ? 'bg-white text-black shadow-sm' : 'text-slate-500 hover:text-black'}`}
                                    >
                                        Diff View
                                    </button>
                                    <button
                                        onClick={() => setViewMode('final')}
                                        className={`px-3 text-xs font-medium rounded-md transition-all flex items-center h-full ${viewMode === 'final' ? 'bg-white text-black shadow-sm' : 'text-slate-500 hover:text-black'}`}
                                    >
                                        Final Preview
                                    </button>
                                </div>
                            </div>

                            <button onClick={() => setIsSimulatedModalOpen(false)} className="p-2 hover:bg-gray-100 rounded-full transition-colors text-slate-500 hover:text-black">
                                <XCircle className="w-5 h-5" />
                            </button>
                        </div>

                        {/* Modal Body */}
                        <div className="flex-1 overflow-y-auto p-8 bg-slate-50 flex justify-center">
                            <div className="transform scale-[0.85] origin-top bg-white shadow-xl min-h-[297mm]">
                                <ResumePreview
                                    data={tailoredResume || (baseResume as any) || {}}
                                    originalData={viewMode === 'diff' ? baseResume : undefined}
                                    template="ats_friendly"
                                />
                            </div>
                        </div>

                        {/* Modal Footer */}
                        <div className="p-4 border-t border-gray-100 bg-white flex justify-end gap-3 z-10 shrink-0">
                            <button
                                onClick={() => setIsSimulatedModalOpen(false)}
                                className="px-4 py-2 text-sm font-semibold hover:bg-gray-100 rounded-md transition-colors text-slate-900 border border-transparent hover:border-gray-200"
                            >
                                Close
                            </button>

                            {simulationStatus === 'approved' ? (
                                <button className="px-6 py-2 bg-black text-white text-sm font-semibold rounded-md flex items-center gap-2 hover:bg-slate-800 transition-all shadow-md border border-black animate-in slide-in-from-bottom-2">
                                    <Download className="w-4 h-4" />
                                    Download PDF
                                </button>
                            ) : (
                                <button
                                    onClick={() => {
                                        setSimulationStatus('approved');
                                        setViewMode('final'); // Auto-switch to final view on approve
                                    }}
                                    className="px-6 py-2 bg-black text-white text-sm font-semibold rounded-md flex items-center gap-2 hover:bg-slate-800 transition-all shadow-md border border-black"
                                >
                                    <CheckCircle className="w-4 h-4" />
                                    Approve Resume
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};
