import React, { useState, useEffect, useCallback } from 'react';
import {
    ExternalLink, MapPin, Clock, Loader2,
    Wand2, FileText, Sparkles, RefreshCw, CheckCircle, ArrowLeft
} from 'lucide-react';
import { Evaluation, TailoredResume, Application, apiClient } from '../services/apiClient';
import { evaluateJob } from '../services/jobService';
import { JobWithEvaluation } from '../services/jobService';
import { TailorReview } from './TailorReview';
import { Toast } from './Toast';
import { formatTimeAgo } from '../utils/format';
import { logger } from '../utils/logger';

// ─── Types ────────────────────────────────────────────────────────────────────

type VerdictState = 'tailor' | 'apply' | 'skip' | 'applied' | 'interview';

interface StepConfig {
    label: string;
    state: 'done' | 'active' | 'waiting' | 'interview' | 'idle';
}

interface JobDetailViewProps {
    job: JobWithEvaluation;
    onEvaluate?: () => void;
    tailoringJobId?: string | null;
    onTailorStart?: (jobId: string) => void;
    onTailorEnd?: () => void;
    /** When true: read-only "what you sent" mode — auto-opens TailorReview, hides all action CTAs */
    sentMode?: boolean;
    /** The application record (for cv_version + applied_at) when sentMode=true */
    sentApplication?: Application;
    onBack?: () => void;
}

// ─── Wit lines ────────────────────────────────────────────────────────────────

function getWitLine(action: string, score: number, witLine?: string | null): string {
    if (witLine) return witLine;
    if (action === 'apply') return score >= 90 ? 'This is yours — send it' : 'Strong fit — go for it';
    if (action === 'tailor') {
        if (score >= 70) return 'Close — polish it';
        return 'Worth the effort — tailor it';
    }
    if (action === 'skip') return 'Not your circus — for now';
    return 'Let\'s see what we\'ve got';
}

// ─── Step Indicator ───────────────────────────────────────────────────────────

const StepIndicator: React.FC<{ steps: StepConfig[] }> = ({ steps }) => {
    const dotClass = (state: StepConfig['state']) => {
        const base = 'w-[18px] h-[18px] rounded-full border flex items-center justify-center text-[9px] shrink-0 transition-all';
        if (state === 'done') return `${base} bg-slate-900 border-slate-900 text-white`;
        if (state === 'active') return `${base} border-slate-900 text-slate-900 font-semibold bg-white`;
        if (state === 'waiting') return `${base} bg-amber-400 border-amber-400 text-white`;
        if (state === 'interview') return `${base} bg-violet-500 border-violet-500 text-white`;
        return `${base} border-slate-200 text-slate-300 bg-white`;
    };

    const labelClass = (state: StepConfig['state']) => {
        const base = 'text-[11px] whitespace-nowrap';
        if (state === 'done' || state === 'active') return `${base} text-slate-900 font-medium`;
        return `${base} text-slate-400`;
    };

    return (
        <div className="flex items-center mb-4">
            {steps.map((step, i) => (
                <React.Fragment key={i}>
                    <div className="flex items-center gap-1.5">
                        <div className={dotClass(step.state)}>
                            {step.state === 'done' ? '✓' : i + 1}
                        </div>
                        <span className={labelClass(step.state)}>{step.label}</span>
                    </div>
                    {i < steps.length - 1 && (
                        <div className={`flex-1 h-px mx-1.5 min-w-[12px] transition-all ${step.state === 'done' ? 'bg-slate-900' : 'bg-slate-200'}`} />
                    )}
                </React.Fragment>
            ))}
        </div>
    );
};

// ─── Action Row ───────────────────────────────────────────────────────────────

interface ActionRowProps {
    verdictState: VerdictState;
    isGenerating: boolean;
    hasGeneratedResume: boolean;
    jobUrl?: string;
    onTailor: () => void;
    onViewResume: () => void;
    onReEvaluate: () => void;
    isReEvaluating: boolean;
}

const ActionRow: React.FC<ActionRowProps> = ({
    verdictState, isGenerating, hasGeneratedResume,
    jobUrl, onTailor, onViewResume, onReEvaluate, isReEvaluating
}) => {
    const PrimaryBtn: React.FC<{ onClick?: () => void; href?: string; disabled?: boolean; children: React.ReactNode }> = ({
        onClick, href, disabled, children
    }) => {
        const cls = 'flex items-center gap-1.5 px-[18px] py-2 rounded-[7px] bg-slate-900 text-white text-[13px] font-medium hover:bg-slate-700 transition-colors disabled:opacity-50 whitespace-nowrap';
        if (href) return <a href={href} target="_blank" rel="noopener noreferrer" className={cls}>{children}</a>;
        return <button onClick={onClick} disabled={disabled} className={cls}>{children}</button>;
    };

    const SecondaryBtn: React.FC<{ onClick?: () => void; href?: string; children: React.ReactNode }> = ({
        onClick, href, children
    }) => {
        const cls = 'flex items-center gap-1.5 px-[13px] py-[7px] rounded-[7px] border border-slate-200 bg-white text-slate-600 text-[12px] hover:border-slate-400 hover:text-slate-900 transition-colors whitespace-nowrap';
        if (href) return <a href={href} target="_blank" rel="noopener noreferrer" className={cls}>{children}</a>;
        return <button onClick={onClick} className={cls}>{children}</button>;
    };

    const GhostBtn: React.FC<{ onClick: () => void; disabled?: boolean; children: React.ReactNode }> = ({
        onClick, disabled, children
    }) => (
        <button
            onClick={onClick}
            disabled={disabled}
            className="flex items-center gap-1.5 px-[13px] py-[7px] rounded-[7px] text-slate-400 text-[12px] hover:text-slate-700 transition-colors whitespace-nowrap disabled:opacity-50"
        >
            {children}
        </button>
    );

    const Divider = () => <div className="w-px h-[18px] bg-slate-100 mx-0.5" />;

    if (verdictState === 'tailor') return (
        <div>
            <div className="flex items-center gap-2">
                <PrimaryBtn onClick={hasGeneratedResume ? onViewResume : onTailor} disabled={isGenerating}>
                    {isGenerating ? (
                        <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Tailoring...</>
                    ) : hasGeneratedResume ? (
                        <><FileText className="w-3.5 h-3.5" /> View resume</>
                    ) : (
                        <><Wand2 className="w-3.5 h-3.5" /> Tailor resume</>
                    )}
                </PrimaryBtn>
                <Divider />
                <GhostBtn onClick={() => jobUrl && window.open(jobUrl, '_blank')}>
                    Apply without tailoring
                </GhostBtn>
                <GhostBtn onClick={onReEvaluate} disabled={isReEvaluating}>
                    <RefreshCw className={`w-3 h-3 ${isReEvaluating ? 'animate-spin' : ''}`} />
                    Re-evaluate
                </GhostBtn>
            </div>
            <p className="text-[11px] text-slate-400 mt-1.5">↳ AI recommends tailoring before applying</p>
        </div>
    );

    if (verdictState === 'apply') return (
        <div>
            <div className="flex items-center gap-2">
                {jobUrl
                    ? <PrimaryBtn href={jobUrl}>Apply now <ExternalLink className="w-3.5 h-3.5" /></PrimaryBtn>
                    : <PrimaryBtn onClick={() => {}}>Apply now ↗</PrimaryBtn>
                }
                <Divider />
                <SecondaryBtn onClick={hasGeneratedResume ? onViewResume : onTailor}>
                    Tailor anyway
                </SecondaryBtn>
                <GhostBtn onClick={onReEvaluate} disabled={isReEvaluating}>
                    <RefreshCw className={`w-3 h-3 ${isReEvaluating ? 'animate-spin' : ''}`} />
                    Re-evaluate
                </GhostBtn>
            </div>
            <p className="text-[11px] text-slate-400 mt-1.5">↳ Strong fit — tailoring is optional here</p>
        </div>
    );

    if (verdictState === 'skip') return (
        <div>
            <div className="flex items-center gap-2">
                <button className="flex items-center gap-1.5 px-[18px] py-2 rounded-[7px] border-[1.5px] border-dashed border-slate-200 bg-white text-slate-300 text-[13px] font-medium whitespace-nowrap">
                    Archive job
                </button>
                <Divider />
                <GhostBtn onClick={() => jobUrl && window.open(jobUrl, '_blank')}>
                    Apply anyway
                </GhostBtn>
                <GhostBtn onClick={onReEvaluate} disabled={isReEvaluating}>
                    <RefreshCw className={`w-3 h-3 ${isReEvaluating ? 'animate-spin' : ''}`} />
                    Re-evaluate
                </GhostBtn>
            </div>
            <p className="text-[11px] text-slate-200 mt-1.5">↳ Requirements are in another universe — give this one a miss</p>
        </div>
    );

    if (verdictState === 'applied') return (
        <div>
            <div className="flex items-center gap-2">
                <SecondaryBtn onClick={onViewResume}>View tailored resume</SecondaryBtn>
                <GhostBtn onClick={() => {}}>Mark rejected</GhostBtn>
                <GhostBtn onClick={() => {}}>Mark interview ↑</GhostBtn>
            </div>
            <p className="text-[11px] text-slate-400 mt-1.5">↳ Keep applying elsewhere while you wait</p>
        </div>
    );

    if (verdictState === 'interview') return (
        <div>
            <div className="flex items-center gap-2">
                <PrimaryBtn onClick={() => {}}>View interview prep</PrimaryBtn>
                <Divider />
                <SecondaryBtn onClick={onViewResume}>View tailored resume</SecondaryBtn>
            </div>
            <p className="text-[11px] text-slate-400 mt-1.5">↳ Interview confirmed — prep the topics below</p>
        </div>
    );

    return null;
};

// ─── Keywords Section ─────────────────────────────────────────────────────────

const KeywordsSection: React.FC<{ matched: string[]; missing: string[]; showMissing: boolean }> = ({
    matched, missing, showMissing
}) => {
    const total = matched.length + missing.length;
    if (total === 0) return null;

    const havePercent = Math.round((matched.length / total) * 100);
    const missPercent = 100 - havePercent;

    return (
        <div>
            <p className="text-[10px] font-medium text-slate-400 uppercase tracking-[0.08em] mb-3">Keywords</p>
            <div className="flex gap-0.5 h-1 rounded-sm overflow-hidden mb-4">
                {havePercent > 0 && (
                    <div className="h-full rounded-l-sm bg-amber-600 transition-all" style={{ width: `${havePercent}%` }} />
                )}
                {showMissing && missPercent > 0 && (
                    <div className="h-full rounded-r-sm bg-blue-400 transition-all" style={{ width: `${missPercent}%` }} />
                )}
            </div>
            <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-medium text-slate-400 uppercase tracking-[0.07em]">Already yours</span>
                    <span className="text-[11px] text-slate-400">{matched.length} of {total}</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                    {matched.map((kw, i) => (
                        <span key={i} className="inline-flex items-center gap-1 text-[12px] font-medium text-amber-800 bg-amber-50 px-2.5 py-1 rounded-[5px]">
                            ✓ {kw}
                        </span>
                    ))}
                </div>
            </div>
            {showMissing && missing.length > 0 && (
                <div>
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-[10px] font-medium text-slate-400 uppercase tracking-[0.07em]">Room to grow</span>
                        <span className="text-[11px] text-slate-400">{missing.length} gaps</span>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                        {missing.map((kw, i) => (
                            <span key={i} className="inline-flex items-center gap-1 text-[12px] font-medium text-blue-700 bg-blue-50 px-2.5 py-1 rounded-[5px] cursor-default hover:bg-blue-100 transition-colors">
                                + {kw}
                            </span>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

// ─── Gap + Fix Row ────────────────────────────────────────────────────────────

interface GapFixRowProps {
    category: string;
    value: string;
    fix?: { location: string; locationSub: string; suggestion: string; approvedRef: string };
    readonly?: boolean;
    badgeColor?: 'amber' | 'violet';
    defaultOpen?: boolean;
}

const GapFixRow: React.FC<GapFixRowProps> = ({
    category, value, fix, readonly, badgeColor = 'amber', defaultOpen = false
}) => {
    const [open, setOpen] = useState(defaultOpen);

    const badgeCls = badgeColor === 'violet'
        ? 'text-violet-600 bg-violet-50 border-violet-200'
        : 'text-amber-600 bg-amber-50 border-amber-200';

    return (
        <div className="border border-slate-100 rounded-[9px] overflow-hidden mb-1.5 bg-white">
            <div
                className={`flex items-start gap-2.5 p-[11px_14px] ${fix && !readonly ? 'cursor-pointer hover:bg-amber-50/40 transition-colors' : ''}`}
                onClick={() => fix && !readonly && setOpen(o => !o)}
            >
                <div className="flex-1 min-w-0">
                    <div className="text-[10px] font-medium text-slate-400 uppercase tracking-[0.06em] mb-0.5">{category}</div>
                    <div className={`text-[12px] leading-relaxed ${readonly && !value.includes('None') ? 'text-slate-600' : 'text-slate-400 italic'}`}>
                        {value}
                    </div>
                </div>
                {fix && !readonly && (
                    <div className="flex items-center gap-1.5 shrink-0 pt-3.5">
                        <span className={`text-[10px] font-medium border px-1.5 py-0.5 rounded ${badgeCls}`}>
                            {badgeColor === 'violet' ? 'Prep ↓' : 'AI fix ↓'}
                        </span>
                        <span className="text-[9px] text-slate-300 transition-transform duration-200" style={{ transform: open ? 'rotate(90deg)' : 'none' }}>▶</span>
                    </div>
                )}
            </div>
            {fix && open && (
                <div className="px-3.5 pb-3 pt-0 border-t border-slate-50 bg-amber-50/30">
                    <p className="text-[12px] text-slate-700 leading-relaxed pt-2.5 mb-1.5">{fix.suggestion}</p>
                    <p className="text-[11px] text-slate-400">
                        ↳ Source: <span className="text-slate-500 font-medium">{fix.approvedRef}</span>
                    </p>
                </div>
            )}
        </div>
    );
};

// ─── Dynamic Middle Section ───────────────────────────────────────────────────

interface DynamicSectionProps {
    verdictState: VerdictState;
    evaluation: Evaluation;
    onExpandAll: () => void;
    allOpen: boolean;
    onTailor: () => void;
}

const DynamicSection: React.FC<DynamicSectionProps> = ({
    verdictState, evaluation, onExpandAll, allOpen, onTailor
}) => {
    const gaps = evaluation.gaps ?? { technical: [], domain: [], soft_skills: [] };
    const edits = evaluation.improvement_suggestions?.resume_edits ?? [];
    const tips = evaluation.interview_tips?.high_priority_topics ?? [];

    const technicalEdit = edits[0];
    const domainEdit = edits[1];

    if (verdictState === 'tailor') {
        const fixCount = [gaps.technical.length > 0, gaps.domain.length > 0].filter(Boolean).length;

        return (
            <div>
                <p className="text-[10px] font-medium text-slate-400 uppercase tracking-[0.08em] mb-3">
                    Gaps & how the AI will address them
                </p>

                {gaps.technical.length > 0 && (
                    <GapFixRow
                        category="Technical"
                        value={gaps.technical.join(' · ')}
                        fix={technicalEdit ? {
                            location: technicalEdit.area.split('.').slice(0, 2).join(' · '),
                            locationSub: technicalEdit.area,
                            suggestion: technicalEdit.suggestion,
                            approvedRef: technicalEdit.approved_reference,
                        } : undefined}
                        defaultOpen={true}
                    />
                )}

                {gaps.domain.length > 0 && (
                    <GapFixRow
                        category="Domain"
                        value={gaps.domain.join(' · ')}
                        fix={domainEdit ? {
                            location: domainEdit.area.split('.').slice(0, 2).join(' · '),
                            locationSub: domainEdit.area,
                            suggestion: domainEdit.suggestion,
                            approvedRef: domainEdit.approved_reference,
                        } : undefined}
                    />
                )}

                {gaps.soft_skills.length > 0 ? (
                    <GapFixRow category="Soft skills" value={gaps.soft_skills.join(' · ')} />
                ) : (
                    <GapFixRow category="Soft skills" value="None identified — you're fine here" readonly />
                )}

                {/* CTA bar */}
                <div className="mt-4 bg-slate-900 rounded-[10px] p-[14px_18px] flex items-center justify-between">
                    <button onClick={onExpandAll} className="text-left cursor-pointer">
                        <div className="flex items-center gap-1.5 mb-0.5">
                            <span className="text-[13px] font-medium text-amber-300 border-b border-dashed border-amber-300">
                                {fixCount} {fixCount === 1 ? 'fix' : 'fixes'} planned
                            </span>
                            <span className="text-[10px] text-slate-500">
                                · click to {allOpen ? 'collapse' : 'expand'} all
                            </span>
                        </div>
                        <p className="text-[11px] text-slate-500">
                            {allOpen ? 'All fixes visible above' : 'Review changes before tailoring'}
                        </p>
                    </button>
                    <button
                        onClick={onTailor}
                        className="text-[12px] font-medium bg-white text-slate-900 border-none px-[18px] py-[7px] rounded-[6px] whitespace-nowrap hover:bg-slate-100 transition-colors"
                    >
                        Tailor resume ↗
                    </button>
                </div>
            </div>
        );
    }

    if (verdictState === 'apply') {
        return (
            <div className="flex items-start gap-2.5 bg-green-50 border border-green-200 rounded-[9px] p-[14px_16px]">
                <CheckCircle className="w-4 h-4 text-green-600 shrink-0 mt-0.5" />
                <p className="text-[13px] text-green-800 leading-relaxed">
                    No meaningful gaps detected. Your experience maps directly to what they need — send this one without overthinking it.
                </p>
            </div>
        );
    }

    if (verdictState === 'skip') {
        return (
            <div>
                <p className="text-[10px] font-medium text-slate-400 uppercase tracking-[0.08em] mb-3">
                    Why it doesn't fit — for reference
                </p>
                {gaps.technical.length > 0 && (
                    <GapFixRow category="Technical" value={gaps.technical.join(' · ')} readonly />
                )}
                {gaps.domain.length > 0 && (
                    <GapFixRow category="Domain" value={gaps.domain.join(' · ')} readonly />
                )}
                <p className="text-[12px] text-slate-400 text-center py-3.5 italic">
                    Bookmark this one — revisit when you've closed the gap
                </p>
            </div>
        );
    }

    if (verdictState === 'applied') {
        if (edits.length === 0) return null;
        return (
            <div>
                <p className="text-[10px] font-medium text-slate-400 uppercase tracking-[0.08em] mb-3">What was changed</p>
                {edits.map((edit, i) => (
                    <div key={i} className="border border-slate-100 rounded-[9px] overflow-hidden mb-1.5 bg-slate-50">
                        <div className="flex items-start justify-between gap-2.5 p-[11px_14px]">
                            <div className="flex-1 min-w-0">
                                <div className="text-[10px] font-medium text-slate-400 uppercase tracking-[0.06em] mb-0.5">
                                    {edit.area.split('.').slice(0, 2).join(' · ')}
                                </div>
                                <div className="text-[12px] text-slate-600 leading-relaxed">{edit.suggestion}</div>
                            </div>
                            <span className="text-[10px] text-slate-400 shrink-0 pt-3.5">Applied</span>
                        </div>
                    </div>
                ))}
            </div>
        );
    }

    if (verdictState === 'interview') {
        if (tips.length === 0) return null;
        return (
            <div>
                <p className="text-[10px] font-medium text-slate-400 uppercase tracking-[0.08em] mb-3">
                    Your prep agenda — based on the gaps
                </p>
                {tips.map((tip, i) => (
                    <GapFixRow
                        key={i}
                        category={tip.topic}
                        value={tip.why}
                        fix={{
                            location: tip.topic,
                            locationSub: '',
                            suggestion: tip.prep,
                            approvedRef: 'Your angle — transferable experience',
                        }}
                        badgeColor="violet"
                        defaultOpen={i === 0}
                    />
                ))}
            </div>
        );
    }

    return null;
};

// ─── Main Component ───────────────────────────────────────────────────────────

export const JobDetailView: React.FC<JobDetailViewProps> = ({
    job, onEvaluate, tailoringJobId, onTailorStart, onTailorEnd,
    sentMode = false, sentApplication, onBack,
}) => {
    const [isReEvaluating, setIsReEvaluating] = useState(false);
    const [isGeneratingResume, setIsGeneratingResume] = useState(false);
    const [tailoredResume, setTailoredResume] = useState<TailoredResume | null>(null);
    const [baseResume, setBaseResume] = useState<any>(null);
    const [isReviewOpen, setIsReviewOpen] = useState(false);
    const [hasGeneratedResume, setHasGeneratedResume] = useState(false);
    const [allGapsOpen, setAllGapsOpen] = useState(true);
    const [toast, setToast] = useState<{ message: string; type: 'error' | 'success' } | null>(null);

    const evaluation = job.evaluation;
    const isEvaluated = job.isEvaluated && !!evaluation;
    const isGenerating = (tailoringJobId === job.id) || isGeneratingResume;

    const getVerdictState = (): VerdictState => {
        if (!isEvaluated || !evaluation) return 'tailor';
        const action = evaluation.recommended_action;
        if (action === 'apply') return 'apply';
        if (action === 'skip') return 'skip';
        return 'tailor';
    };

    const verdictState = getVerdictState();

    const getSteps = (): StepConfig[] => {
        if (verdictState === 'tailor') return [
            { label: 'Evaluated', state: 'done' },
            { label: 'Tailor', state: 'active' },
            { label: 'Apply', state: 'idle' },
        ];
        if (verdictState === 'apply') return [
            { label: 'Evaluated', state: 'done' },
            { label: 'Apply', state: 'active' },
            { label: 'Done', state: 'idle' },
        ];
        if (verdictState === 'skip') return [
            { label: 'Evaluated', state: 'done' },
            { label: 'Skipped', state: 'idle' },
        ];
        if (verdictState === 'applied') return [
            { label: 'Evaluated', state: 'done' },
            { label: 'Tailored', state: 'done' },
            { label: 'Applied', state: 'done' },
            { label: 'Waiting…', state: 'waiting' },
        ];
        if (verdictState === 'interview') return [
            { label: 'Evaluated', state: 'done' },
            { label: 'Tailored', state: 'done' },
            { label: 'Applied', state: 'done' },
            { label: 'Interview', state: 'interview' },
        ];
        return [];
    };

    const showKeywords = ['tailor', 'apply'].includes(verdictState);
    const showMissingKeywords = verdictState === 'tailor';

    const barColor = () => {
        if (verdictState === 'apply') return 'bg-green-500';
        if (verdictState === 'skip') return 'bg-slate-200';
        return 'bg-amber-500';
    };

    // Reset state when job changes
    useEffect(() => {
        setTailoredResume(null);
        setHasGeneratedResume(false);
        setIsGeneratingResume(false);
        setIsReEvaluating(false);
        setIsReviewOpen(false);
        setAllGapsOpen(true);

        const checkExisting = async () => {
            try {
                const versions = await apiClient.getTailoredVersions(job.id);
                if (versions?.length > 0) {
                    setTailoredResume(versions[0]);
                    setHasGeneratedResume(true);
                    const base = await apiClient.getMasterResume();
                    setBaseResume(base);
                    // sentMode: auto-open the review so user sees what was sent
                    if (sentMode) setIsReviewOpen(true);
                }
            } catch {
                // No existing tailored resume
            }
        };

        if (job.id) checkExisting();
    }, [job.id]);

    const showToast = useCallback((message: string, type: 'error' | 'success') => {
        setToast({ message, type });
        setTimeout(() => setToast(null), 4000);
    }, []);

    const handleTailor = async () => {
        if (onTailorStart) onTailorStart(job.id);
        else setIsGeneratingResume(true);

        if (!baseResume) {
            try {
                const base = await apiClient.getMasterResume();
                setBaseResume(base);
            } catch {
                logger.error('JobDetailView', 'Could not fetch base resume');
            }
        }

        try {
            const result = await apiClient.tailorResume(job.id);
            setTailoredResume(result);
            setHasGeneratedResume(true);
            setIsReviewOpen(true);
        } catch (error: any) {
            const msg = error?.message || error?.detail || 'Failed to tailor resume. Please try again.';
            showToast(msg, 'error');
        } finally {
            if (onTailorEnd) onTailorEnd();
            else setIsGeneratingResume(false);
        }
    };

    const handleReEvaluate = async () => {
        if (!job.id) return;
        setIsReEvaluating(true);
        try {
            await evaluateJob(job.id, true);
            onEvaluate?.();
        } catch {
            showToast('Re-evaluation failed. Please try again.', 'error');
        } finally {
            setIsReEvaluating(false);
        }
    };

    const handleEvaluateFresh = async () => {
        setIsReEvaluating(true);
        try {
            await evaluateJob(job.id);
            onEvaluate?.();
        } catch {
            showToast('Evaluation failed. Please try again.', 'error');
        } finally {
            setIsReEvaluating(false);
        }
    };

    const toggleAllGaps = useCallback(() => setAllGapsOpen(o => !o), []);

    const witLine = isEvaluated && evaluation
        ? getWitLine(evaluation.recommended_action ?? '', evaluation.job_match_score ?? 0, evaluation.wit_line)
        : 'Waiting for analysis';

    const [witBefore, witAfter] = witLine.includes(' — ')
        ? witLine.split(' — ')
        : [witLine, ''];

    const score = evaluation?.job_match_score ?? 0;
    const matched = evaluation?.matched_keywords ?? [];
    const missing = evaluation?.missing_keywords ?? [];
    const hasRecruiter = evaluation?.recruiter_email && evaluation.recruiter_email !== 'Unknown';

    return (
        <div className="h-full flex flex-col bg-white">
            {/* sentMode: "What you sent" banner */}
            {sentMode && (
                <div className="flex items-center gap-3 px-6 py-3 bg-slate-50 border-b border-slate-100 flex-shrink-0">
                    {onBack && (
                        <button onClick={onBack} className="p-1.5 hover:bg-slate-200 rounded-lg transition-colors">
                            <ArrowLeft className="w-4 h-4 text-slate-500" />
                        </button>
                    )}
                    <div className="flex-1 min-w-0">
                        <p className="text-[12px] font-medium text-slate-700">
                            What you sent
                            {sentApplication && (
                                <span className={`ml-2 text-[10px] font-medium px-2 py-0.5 rounded-full border ${
                                    sentApplication.cv_version === 'tailored'
                                        ? 'bg-purple-50 text-purple-700 border-purple-200'
                                        : 'bg-slate-100 text-slate-500 border-slate-200'
                                }`}>
                                    {sentApplication.cv_version === 'tailored' ? 'tailored CV' : 'base CV'}
                                </span>
                            )}
                        </p>
                        {sentApplication?.applied_at && (
                            <p className="text-[11px] text-slate-400">Applied {formatTimeAgo(sentApplication.applied_at)}</p>
                        )}
                    </div>
                </div>
            )}

            {isReviewOpen && tailoredResume && baseResume && evaluation && (
                <TailorReview
                    baseResume={baseResume}
                    tailoredResume={tailoredResume}
                    evaluation={evaluation}
                    onClose={() => setIsReviewOpen(false)}
                    onStatusChange={() => {}}
                />
            )}

            {toast && (
                <Toast message={toast.message} type={toast.type} onDismiss={() => setToast(null)} />
            )}

            {/* Sticky header */}
            <div className="px-6 pt-5 pb-4 border-b border-slate-100 sticky top-0 bg-white z-10">
                <div className="flex items-start gap-3 mb-4">
                    <div className="w-9 h-9 rounded-lg bg-slate-900 text-white text-sm font-semibold flex items-center justify-center shrink-0">
                        {job.company_name?.charAt(0) ?? 'C'}
                    </div>
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                            {job.job_url ? (
                                <a
                                    href={job.job_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-[16px] font-medium text-slate-900 hover:text-blue-700 transition-colors flex items-center gap-1.5 group"
                                >
                                    {job.title}
                                    <ExternalLink className="w-3.5 h-3.5 text-slate-300 group-hover:text-blue-500 opacity-0 group-hover:opacity-100 transition-all" />
                                </a>
                            ) : (
                                <h1 className="text-[16px] font-medium text-slate-900">{job.title}</h1>
                            )}
                        </div>
                        <div className="flex items-center flex-wrap gap-1.5 text-[12px] text-slate-500 mt-0.5">
                            <span className="font-medium text-slate-700">{job.company_name}</span>
                            {job.location && (
                                <><span className="text-slate-300">·</span>
                                    <span className="flex items-center gap-0.5"><MapPin className="w-3 h-3" />{job.location}</span></>
                            )}
                            {job.posted_at && (
                                <><span className="text-slate-300">·</span>
                                    <span className="flex items-center gap-0.5"><Clock className="w-3 h-3" />{formatTimeAgo(job.posted_at)}</span></>
                            )}
                        </div>
                        {hasRecruiter && (
                            <div className="inline-flex items-center gap-1.5 text-[11px] text-amber-600 mt-1">
                                ✉ {evaluation!.recruiter_email}
                            </div>
                        )}
                    </div>
                </div>

                {isEvaluated && <StepIndicator steps={getSteps()} />}

                {isEvaluated ? (
                    <ActionRow
                        verdictState={verdictState}
                        isGenerating={isGenerating}
                        hasGeneratedResume={hasGeneratedResume}
                        jobUrl={evaluation?.job_url && evaluation.job_url !== 'Unknown' ? evaluation.job_url : job.job_url ?? undefined}
                        onTailor={handleTailor}
                        onViewResume={() => setIsReviewOpen(true)}
                        onReEvaluate={handleReEvaluate}
                        isReEvaluating={isReEvaluating}
                    />
                ) : (
                    <button
                        onClick={handleEvaluateFresh}
                        disabled={isReEvaluating}
                        className="flex items-center gap-2 px-5 py-2 bg-slate-900 hover:bg-slate-700 text-white text-[13px] font-medium rounded-[7px] transition-colors"
                    >
                        {isReEvaluating
                            ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Analysing…</>
                            : <><Sparkles className="w-3.5 h-3.5" /> Analyse match</>
                        }
                    </button>
                )}
            </div>

            {/* Scrollable content */}
            <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6 bg-white">
                {!isEvaluated && (
                    <div className="flex flex-col items-center justify-center py-16 text-center">
                        <Sparkles className="w-10 h-10 text-slate-200 mb-4" />
                        <h3 className="text-[15px] font-medium text-slate-700 mb-1.5">Ready to analyse</h3>
                        <p className="text-[13px] text-slate-400 max-w-xs">
                            Click the button above to have AI evaluate this job against your resume.
                        </p>
                    </div>
                )}

                {isEvaluated && evaluation && (
                    <>
                        {/* Score + wit */}
                        <section>
                            <div className="flex items-start gap-5 mb-3">
                                <div className="text-[52px] font-light text-slate-900 leading-none tracking-tight shrink-0">
                                    {score}<sup className="text-[18px] text-slate-300 font-light tracking-normal">/100</sup>
                                </div>
                                <div className="flex-1 pt-1">
                                    <div className="text-[20px] font-light text-slate-900 leading-snug mb-1.5 tracking-tight">
                                        <em style={{ fontStyle: 'italic' }}>{witBefore}</em>
                                        {witAfter && <> — {witAfter}</>}
                                    </div>
                                    <div className="flex items-center gap-2 flex-wrap">
                                        <span className="text-[11px] text-slate-400">{evaluation.required_exp ?? 'Experience unknown'}</span>
                                        <span className="text-slate-200">·</span>
                                        <span className="text-[11px] text-slate-400">
                                            {verdictState === 'tailor' && 'Tailor to improve your odds'}
                                            {verdictState === 'apply' && 'Strong fit, no gaps blocking you'}
                                            {verdictState === 'skip' && 'Experience gap is too wide'}
                                            {verdictState === 'applied' && 'No response yet'}
                                            {verdictState === 'interview' && 'Your gap analysis is your prep agenda'}
                                        </span>
                                    </div>
                                </div>
                            </div>
                            <div className="h-0.5 bg-slate-100 rounded-sm overflow-hidden mb-3">
                                <div className={`h-full rounded-sm transition-all duration-700 ${barColor()}`} style={{ width: `${score}%` }} />
                            </div>
                            <p className="text-[13px] text-slate-500 leading-relaxed">{evaluation.summary}</p>
                        </section>

                        {/* Keywords */}
                        {showKeywords && (matched.length > 0 || missing.length > 0) && (
                            <section className="pt-5 border-t border-slate-50">
                                <KeywordsSection matched={matched} missing={missing} showMissing={showMissingKeywords} />
                            </section>
                        )}

                        {/* Dynamic section */}
                        <section className="pt-5 border-t border-slate-50">
                            <DynamicSection
                                verdictState={verdictState}
                                evaluation={evaluation}
                                onExpandAll={toggleAllGaps}
                                allOpen={allGapsOpen}
                                onTailor={handleTailor}
                            />
                        </section>

                        {/* Job description */}
                        <section className="pt-5 border-t border-slate-50">
                            <p className="text-[10px] font-medium text-slate-400 uppercase tracking-[0.08em] mb-3">About the job</p>
                            {job.description_html ? (
                                <div
                                    className="prose prose-slate max-w-none text-[13px] text-slate-600
                                        prose-headings:font-medium prose-headings:text-slate-800
                                        prose-a:text-slate-700 prose-a:underline
                                        prose-strong:text-slate-800 prose-strong:font-medium
                                        prose-ul:list-disc prose-ul:pl-4 prose-ul:space-y-0.5
                                        prose-li:marker:text-slate-300"
                                    dangerouslySetInnerHTML={{ __html: job.description_html }}
                                />
                            ) : (
                                <p className="text-[13px] text-slate-500 leading-relaxed whitespace-pre-wrap">
                                    {job.description_text ?? 'No description available.'}
                                </p>
                            )}
                        </section>
                    </>
                )}
            </div>
        </div>
    );
};
