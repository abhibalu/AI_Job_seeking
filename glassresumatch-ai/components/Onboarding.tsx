import React, { useState, useRef, useEffect } from 'react';
import { Loader2, Upload, Sparkles, ArrowRight } from 'lucide-react';
import apiClient from '../services/apiClient';

// ─── Mock feed data (Step 0 preview) ──────────────────────────────────────

const MOCK_JOBS = [
    { id: '1', title: 'Staff Software Engineer', company: 'Linear',      score: 94, action: 'apply',  witLine: 'This is yours — send it'     },
    { id: '2', title: 'Senior Backend Engineer', company: 'Stripe',      score: 87, action: 'tailor', witLine: 'Close — polish it'           },
    { id: '3', title: 'Platform Engineer',       company: 'Vercel',      score: 72, action: 'tailor', witLine: 'Worth the effort — tailor it' },
];

const ACTION_BADGE: Record<string, { label: string; cls: string }> = {
    apply:  { label: 'Apply now',    cls: 'bg-green-50  text-green-700  border-green-200'  },
    tailor: { label: 'Tailor first', cls: 'bg-amber-50  text-amber-700  border-amber-200'  },
    skip:   { label: 'Skip',         cls: 'bg-slate-50  text-slate-500  border-slate-200'  },
};

const MockJobCard: React.FC<{ job: typeof MOCK_JOBS[0]; delay: number }> = ({ job, delay }) => {
    const [visible, setVisible] = useState(false);
    useEffect(() => {
        const t = setTimeout(() => setVisible(true), delay);
        return () => clearTimeout(t);
    }, [delay]);

    const badge = ACTION_BADGE[job.action] ?? ACTION_BADGE.skip;
    const scoreColor = job.score >= 90 ? 'text-green-600' : job.score >= 75 ? 'text-amber-600' : 'text-slate-400';

    return (
        <div
            className={`bg-white border border-slate-100 rounded-xl p-4 transition-all duration-500 ${
                visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'
            }`}
        >
            <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-lg bg-slate-900 text-white text-sm font-semibold flex items-center justify-center shrink-0">
                        {job.company.charAt(0)}
                    </div>
                    <div>
                        <p className="text-[13px] font-medium text-slate-900">{job.title}</p>
                        <p className="text-[11px] text-slate-400 mt-0.5">{job.company}</p>
                    </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                    <span className={`text-[22px] font-light leading-none ${scoreColor}`}>{job.score}</span>
                    <span className="text-[10px] text-slate-300">/100</span>
                </div>
            </div>
            <div className="flex items-center justify-between mt-3">
                <p className="text-[11px] text-slate-500 italic">{job.witLine}</p>
                <span className={`text-[10px] font-medium px-2 py-0.5 rounded border ${badge.cls}`}>
                    {badge.label}
                </span>
            </div>
        </div>
    );
};

// ─── Onboarding steps ──────────────────────────────────────────────────────

interface OnboardingProps {
    onComplete: () => void;
}

export const Onboarding: React.FC<OnboardingProps> = ({ onComplete }) => {
    const [step, setStep] = useState<0 | 1>(0);
    const [isUploading, setIsUploading] = useState(false);
    const [uploadDone, setUploadDone] = useState(false);
    const [uploadError, setUploadError] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Progressive save — preserve partial progress across refreshes
    useEffect(() => {
        const saved = localStorage.getItem('onboarding_step');
        if (saved === '1') setStep(1);
    }, []);

    const goToStep1 = () => {
        localStorage.setItem('onboarding_step', '1');
        setStep(1);
    };

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        // Progressive save — user has started upload
        localStorage.setItem('onboarding_step', '1');

        setIsUploading(true);
        setUploadError(null);

        try {
            await apiClient.uploadResume(file);

            // Poll until parsing completes (same pattern as useResumeState)
            let tries = 0;
            const poll = setInterval(async () => {
                tries++;
                try {
                    const resume = await apiClient.getMasterResume();
                    if (resume?.status === 'error') {
                        clearInterval(poll);
                        setIsUploading(false);
                        setUploadError(resume.error || 'Parsing failed. Please try a different file.');
                        return;
                    }
                    if (resume && resume.status !== 'processing' && (resume.fullName || resume.basics)) {
                        clearInterval(poll);
                        setIsUploading(false);
                        setUploadDone(true);
                        localStorage.setItem('onboarding_complete', 'true');
                        localStorage.removeItem('onboarding_step');
                        setTimeout(onComplete, 800);
                    }
                } catch { /* still processing */ }
                if (tries > 30) { clearInterval(poll); setIsUploading(false); }
            }, 2000);
        } catch (err: any) {
            setIsUploading(false);
            setUploadError(err?.message || 'Upload failed. Please try again.');
        } finally {
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    };

    // ── Step 0: Product preview ──────────────────────────────────────────────
    if (step === 0) return (
        <div className="fixed inset-0 z-[100] bg-slate-50 flex flex-col items-center justify-center p-6 overflow-y-auto">
            <div className="w-full max-w-sm">
                {/* Header */}
                <div className="text-center mb-8">
                    <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-blue-600 to-purple-600 flex items-center justify-center shadow-lg mx-auto mb-4">
                        <Sparkles className="w-6 h-6 text-white" />
                    </div>
                    <h1 className="text-[22px] font-bold text-slate-900 tracking-tight">TailorAI</h1>
                    <p className="text-[13px] text-slate-500 mt-1.5 leading-relaxed">
                        Your resume, scored and tailored for every job — automatically.
                    </p>
                </div>

                {/* Mock feed */}
                <div className="space-y-2.5 mb-8">
                    {MOCK_JOBS.map((job, i) => (
                        <MockJobCard key={job.id} job={job} delay={300 + i * 250} />
                    ))}
                </div>

                {/* CTA */}
                <button
                    onClick={goToStep1}
                    className="w-full flex items-center justify-center gap-2 py-3 bg-slate-900 hover:bg-slate-700 text-white text-[14px] font-medium rounded-xl transition-colors shadow-md"
                >
                    Let's set it up
                    <ArrowRight className="w-4 h-4" />
                </button>
            </div>
        </div>
    );

    // ── Step 1: Upload resume ────────────────────────────────────────────────
    return (
        <div className="fixed inset-0 z-[100] bg-slate-50 flex flex-col items-center justify-center p-6">
            <div className="w-full max-w-sm">
                <div className="text-center mb-8">
                    <div className="w-12 h-12 rounded-2xl bg-slate-900 flex items-center justify-center mx-auto mb-4">
                        <Upload className="w-6 h-6 text-white" />
                    </div>
                    <h2 className="text-[20px] font-bold text-slate-900">Upload your resume</h2>
                    <p className="text-[13px] text-slate-500 mt-1.5">
                        PDF or DOCX — AI will parse it and keep it on file for tailoring.
                    </p>
                </div>

                <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.docx"
                    className="hidden"
                    onChange={handleFileChange}
                />

                {uploadDone ? (
                    <div className="text-center py-4">
                        <div className="w-10 h-10 bg-green-50 border border-green-200 rounded-full flex items-center justify-center mx-auto mb-3">
                            <span className="text-green-600 text-lg">✓</span>
                        </div>
                        <p className="text-[14px] font-medium text-slate-900">Resume parsed</p>
                        <p className="text-[12px] text-slate-400 mt-1">Taking you in…</p>
                    </div>
                ) : (
                    <>
                        <button
                            onClick={() => fileInputRef.current?.click()}
                            disabled={isUploading}
                            className="w-full flex items-center justify-center gap-2 py-3 bg-slate-900 hover:bg-slate-700 text-white text-[14px] font-medium rounded-xl transition-colors shadow-md disabled:opacity-60"
                        >
                            {isUploading ? (
                                <><Loader2 className="w-4 h-4 animate-spin" /> Parsing with AI…</>
                            ) : (
                                <><Upload className="w-4 h-4" /> Choose file</>
                            )}
                        </button>

                        {uploadError && (
                            <p className="text-[12px] text-rose-500 text-center mt-3">{uploadError}</p>
                        )}

                        <p className="text-center mt-4 text-[11px] text-slate-300">
                            PDF and DOCX supported
                        </p>

                        <button
                            onClick={() => {
                                localStorage.setItem('onboarding_complete', 'true');
                                localStorage.removeItem('onboarding_step');
                                onComplete();
                            }}
                            className="w-full text-center mt-6 text-[12px] text-slate-400 hover:text-slate-600 transition-colors"
                        >
                            Skip for now — I'll upload later
                        </button>
                    </>
                )}
            </div>
        </div>
    );
};
