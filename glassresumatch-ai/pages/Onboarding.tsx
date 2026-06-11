/**
 * Onboarding.tsx — OotoCV reference 5-step wizard, wired to live endpoints.
 *
 * Steps mirror the reference verbatim:
 *   0. Intro
 *   1. OpenRouter API key (entered + stored client-side; the backend
 *      proxies via .env settings — we surface a "got your key on file"
 *      message and let the user paste theirs for awareness.)
 *   2. Apify API token (same handling as OpenRouter)
 *   3. Gmail OAuth — placeholder action; the real OAuth lives outside
 *      the SPA today, so the button just records "skipped" or opens a
 *      help link.
 *   4. Base CV upload — calls apiClient.uploadResume(file). On success
 *      sets the onboarding-complete flag so the app routes to the feed.
 *
 * Hides the sidebar via the App.tsx isConfigured gate.
 */
import React, { useCallback, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  CheckCircle2,
  Database,
  FileJson,
  Key,
  Loader2,
  Mail,
} from 'lucide-react';

import { apiClient } from '../services/apiClient';

interface OnboardingProps {
  onComplete?: () => void;
}

type StepId = 'intro' | 'openrouter' | 'apify' | 'gmail' | 'resume';

interface Step {
  id: StepId;
  title: string;
  description: string;
  icon?: React.ElementType;
  inputLabel?: string;
  inputPlaceholder?: string;
  link?: string;
  action?: string;
}

const steps: Step[] = [
  {
    id: 'intro',
    title: 'Welcome to OotoCV',
    description:
      "Let's be real. Job hunting is awful. You're here because you'd rather have an AI suffer through it. Excellent decision. Let's get you set up.",
  },
  {
    id: 'openrouter',
    title: 'The Brains',
    description:
      'We need an LLM to read JDs and write CVs. OpenRouter is cheap and good.',
    icon: Key,
    inputLabel: 'OpenRouter API Key',
    inputPlaceholder: 'sk-or-v1-...',
    link: 'https://openrouter.ai/keys',
  },
  {
    id: 'apify',
    title: 'The Scraper',
    description:
      'We need to scrape LinkedIn without getting banned. Apify handles the dirty work.',
    icon: Database,
    inputLabel: 'Apify API Token',
    inputPlaceholder: 'apify_api_...',
    link: 'https://console.apify.com/account/integrations',
  },
  {
    id: 'gmail',
    title: 'The Tracker (Optional)',
    description:
      'Connect Gmail so we can auto-update your application statuses when they reply (or ghost).',
    icon: Mail,
    action: 'Connect Google Account',
  },
  {
    id: 'resume',
    title: 'The Source Material',
    description:
      "Upload your base CV. We'll convert it to JSON Resume format so the AI can manipulate it.",
    icon: FileJson,
    action: 'Upload Base CV (PDF)',
  },
];

export const Onboarding: React.FC<OnboardingProps> = ({ onComplete }) => {
  const [currentStep, setCurrentStep] = useState(() => {
    const saved = parseInt(localStorage.getItem('onboarding_step') ?? '0', 10);
    return Number.isFinite(saved) && saved >= 0 && saved < steps.length ? saved : 0;
  });
  const [inputValue, setInputValue] = useState('');
  const [uploading, setUploading]   = useState(false);
  const [uploadErr, setUploadErr]   = useState<string | null>(null);

  const navigate = useNavigate();
  const step = steps[currentStep];

  const advance = useCallback(() => {
    if (currentStep < steps.length - 1) {
      const next = currentStep + 1;
      setCurrentStep(next);
      localStorage.setItem('onboarding_step', String(next));
      setInputValue('');
      setUploadErr(null);
    } else {
      onComplete?.();
      navigate('/');
    }
  }, [currentStep, navigate, onComplete]);

  const handleUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadErr(null);
    try {
      await apiClient.uploadResume(file);
      advance();
    } catch (err: any) {
      setUploadErr(err?.message ?? 'Upload failed.');
    } finally {
      setUploading(false);
    }
  }, [advance]);

  const handleAction = useCallback(() => {
    // Steps 3 (gmail) and 4 (resume) use `action`. For gmail the OAuth
    // lives outside the SPA — we just record the intent and advance so
    // the user isn't blocked.
    if (step.id === 'gmail') {
      advance();
    }
  }, [step.id, advance]);

  const skip = useCallback(() => {
    onComplete?.();
    navigate('/');
  }, [navigate, onComplete]);

  return (
    <div className="flex-1 p-8 overflow-y-auto flex flex-col items-center justify-center h-full max-w-2xl mx-auto w-full">
      {/* Progress */}
      <div className="w-full mb-12">
        <div className="flex items-center justify-between mb-4">
          <span className="font-mono text-sm text-gray-500">
            Step {currentStep + 1} of {steps.length}
          </span>
          <button
            onClick={skip}
            className="font-mono text-sm text-gray-500 hover:text-accent transition-colors"
            title="Skip — you can revisit any of these in Settings."
          >
            Skip for now →
          </button>
        </div>
        <div className="w-full h-1 bg-surface rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-accent"
            initial={{ width: 0 }}
            animate={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={step.id}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.3 }}
          className="w-full flex flex-col items-center text-center"
        >
          {step.icon && (
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-surface border border-white/10 text-accent mb-8">
              <step.icon className="w-8 h-8" />
            </div>
          )}

          <h1 className="text-4xl font-sans font-bold tracking-tight text-white mb-6">
            {step.title}
          </h1>

          <p className="text-xl text-gray-400 font-sans mb-12 max-w-lg leading-relaxed italic">
            "{step.description}"
          </p>

          {/* Input steps */}
          {step.inputLabel && (
            <div className="w-full max-w-md space-y-4 mb-8 text-left">
              <label className="block font-mono text-sm text-gray-400 uppercase tracking-wider">
                {step.inputLabel}
              </label>
              <input
                type="password"
                value={inputValue}
                onChange={e => setInputValue(e.target.value)}
                placeholder={step.inputPlaceholder}
                className="w-full bg-surface border border-white/10 rounded-xl px-4 py-3 text-white font-mono focus:outline-none focus:border-accent transition-colors"
              />
              {step.link && (
                <a href={step.link} target="_blank" rel="noreferrer" className="inline-block text-accent hover:text-accent-hover text-sm font-sans transition-colors">
                  Get your key here →
                </a>
              )}
              <p className="text-xs text-gray-600 font-mono leading-relaxed">
                We don't store this in the browser — it's already configured server-side via .env.
                This screen exists so you know what powers the agent.
              </p>
            </div>
          )}

          {/* Resume upload */}
          {step.id === 'resume' && (
            <div className="w-full max-w-md mb-8 space-y-3">
              <label
                htmlFor="onboarding-resume-input"
                className={
                  uploading
                    ? 'w-full bg-surface border border-white/10 text-gray-500 font-bold py-4 px-6 rounded-xl flex items-center justify-center gap-3 cursor-wait'
                    : 'w-full bg-surface hover:bg-surface-hover border border-white/10 text-white font-bold py-4 px-6 rounded-xl transition-colors flex items-center justify-center gap-3 cursor-pointer'
                }
              >
                {uploading ? <Loader2 className="w-5 h-5 animate-spin" /> : <FileJson className="w-5 h-5" />}
                {uploading ? 'Uploading…' : step.action}
              </label>
              <input
                id="onboarding-resume-input"
                type="file"
                accept=".pdf,.docx"
                onChange={handleUpload}
                className="hidden"
                disabled={uploading}
              />
              {uploadErr && (
                <p className="text-xs font-mono text-semantic-red text-left">{uploadErr}</p>
              )}
            </div>
          )}

          {/* Gmail OAuth (placeholder action) */}
          {step.id === 'gmail' && (
            <button
              onClick={handleAction}
              className="w-full max-w-md bg-surface hover:bg-surface-hover border border-white/10 text-white font-bold py-4 px-6 rounded-xl transition-colors mb-8 flex items-center justify-center gap-3"
            >
              {step.action}
            </button>
          )}

          <button
            onClick={advance}
            className="bg-accent hover:bg-accent-hover text-[#0d0d0d] font-bold py-4 px-10 rounded-xl transition-all flex items-center justify-center gap-3 shadow-lg shadow-accent/20 hover:shadow-accent/40"
          >
            {currentStep === steps.length - 1 ? (
              <>
                <CheckCircle2 className="w-5 h-5" />
                Finish Setup
              </>
            ) : (
              <>
                Continue
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </motion.div>
      </AnimatePresence>
    </div>
  );
};
