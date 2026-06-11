/**
 * ResumeRoast.tsx — OotoCV reference, wired to /api/resumes/roast.
 *
 * Three states (upload / roasting / results) just like the reference.
 * The upload step is cosmetic — the backend always roasts the master
 * resume (see agents/roast.py). Uploading a different file here would
 * require a new endpoint; for now the upload kicks the LLM call against
 * the master CV and shows the result.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, CheckCircle2, ExternalLink, Flame, UploadCloud } from 'lucide-react';

import { TypewriterWaitState } from '../components/TypewriterWaitState';
import { apiClient } from '../services/apiClient';
import type { RoastItem } from '../services/apiClient';

type RoastState = 'upload' | 'roasting' | 'results' | 'error';

export const ResumeRoast: React.FC = () => {
  const navigate = useNavigate();
  const [state, setState]       = useState<RoastState>('upload');
  const [fileName, setFileName] = useState<string | null>(null);
  const [items, setItems]       = useState<RoastItem[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // The roast LLM call runs in parallel with the typewriter so the user
  // doesn't wait twice. Stash the result and let the typewriter's
  // onComplete advance to results when it finishes.
  const [pendingItems, setPendingItems] = useState<RoastItem[] | null>(null);

  const handleUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFileName(f.name);
    setState('roasting');
    setErrorMsg(null);
    setPendingItems(null);

    apiClient.roastResume()
      .then(({ items }) => setPendingItems(items ?? []))
      .catch(err => {
        setErrorMsg(err?.message ?? 'Roast failed.');
        setState('error');
      });
  }, []);

  // When the typewriter finishes AND items have arrived, show results.
  // If items arrive first, we still wait for the typewriter for the dramatic
  // effect — but if the typewriter beats the LLM, we hold until items land.
  const [typewriterDone, setTypewriterDone] = useState(false);
  useEffect(() => {
    if (state === 'roasting' && typewriterDone && pendingItems !== null) {
      setItems(pendingItems);
      setState('results');
    }
  }, [state, typewriterDone, pendingItems]);

  // Roasting state
  if (state === 'roasting') {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <TypewriterWaitState
          messages={[
            `Parsing ${fileName ?? 'your CV'}...`,
            'Oh no.',
            'Did you really use Times New Roman?',
            'Found "Microsoft Office" listed as a skill in 2024...',
            'Evaluating your "passionate about synergy" objective statement...',
            "Counting passive voice instances... it's a lot.",
            'Preparing the roast. This might sting.',
          ]}
          onComplete={() => setTypewriterDone(true)}
          speed={22}
          delayBetweenMessages={900}
        />
      </div>
    );
  }

  // Error state — surfaces backend failures (e.g., OpenRouter disabled).
  if (state === 'error') {
    return (
      <div className="flex-1 p-8 flex items-center justify-center">
        <div className="text-center space-y-4 max-w-md">
          <Flame className="w-12 h-12 text-semantic-red mx-auto" />
          <p className="text-gray-300 font-sans">
            Roast failed. {errorMsg ?? 'Unknown error.'}
          </p>
          <button
            onClick={() => { setState('upload'); setErrorMsg(null); }}
            className="text-accent font-mono text-sm hover:underline"
          >
            ← Try again
          </button>
        </div>
      </div>
    );
  }

  // Results state
  if (state === 'results') {
    return (
      <div className="flex-1 p-8 overflow-y-auto max-w-4xl mx-auto w-full">
        <button
          onClick={() => navigate('/settings')}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors mb-8 font-mono text-sm"
        >
          <ArrowLeft className="w-4 h-4" /> Back to settings
        </button>

        <header className="mb-10 text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-semantic-red/10 text-semantic-red mb-6">
            <Flame className="w-8 h-8" />
          </div>
          <h1 className="text-4xl font-sans font-bold tracking-tight text-white mb-3">
            The Roast
          </h1>
          <p className="text-gray-400 font-mono text-sm">
            {fileName ?? 'Your CV'} · {items.length} issue{items.length !== 1 ? 's' : ''} found · brutal but correct
          </p>
        </header>

        {items.length === 0 ? (
          <div className="rounded-xl border border-semantic-green/15 bg-semantic-green/5 p-8 text-center space-y-3">
            <CheckCircle2 className="w-10 h-10 text-semantic-green mx-auto" />
            <p className="text-gray-200 font-sans">
              No major issues. Either your CV is genuinely strong or the AI is being polite.
              Don't get cocky.
            </p>
          </div>
        ) : (
          <div className="space-y-5 mb-10">
            {items.map((item, idx) => (
              <div
                key={idx}
                className="rounded-xl border border-semantic-red/15 bg-semantic-red/5 overflow-hidden"
              >
                <div className="px-5 py-3 border-b border-semantic-red/10 flex items-center justify-between">
                  <h3 className="font-mono text-xs text-semantic-red uppercase tracking-wider font-semibold">
                    {item.section}
                  </h3>
                  <span className="font-mono text-[10px] text-semantic-red/50 uppercase tracking-wider">
                    Issue {idx + 1} of {items.length}
                  </span>
                </div>

                <div className="p-5 space-y-4">
                  <p className="text-gray-400 font-sans text-sm italic leading-relaxed border-l-2 border-semantic-red/30 pl-3">
                    {item.quote}
                  </p>
                  <p className="text-white font-sans text-sm leading-relaxed">
                    <span className="text-semantic-red font-mono text-xs uppercase tracking-wider mr-2">AI:</span>
                    {item.verdict}
                  </p>
                  {item.fixed && (
                    <div className="flex items-start gap-2 p-3 rounded-lg bg-semantic-green/5 border border-semantic-green/10">
                      <CheckCircle2 className="w-4 h-4 text-semantic-green shrink-0 mt-0.5" />
                      <p className="text-sm text-semantic-green/90 font-sans leading-relaxed">
                        {item.fixed}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="border border-white/5 bg-surface rounded-2xl p-8 text-center space-y-4">
          <p className="text-gray-300 font-sans text-lg leading-relaxed max-w-xl mx-auto">
            Apply these by updating your base CV in settings — future tailoring runs will then
            start from the cleaned-up version.
          </p>
          <div className="flex items-center justify-center gap-4 pt-2">
            <button
              onClick={() => navigate('/settings')}
              className="flex items-center gap-2 bg-accent hover:bg-accent-hover text-[#0d0d0d] font-bold py-4 px-8 rounded-xl transition-all shadow-lg shadow-accent/20 hover:shadow-accent/40"
            >
              <CheckCircle2 className="w-5 h-5" />
              Update base CV in settings
            </button>
            <button
              onClick={() => { setState('upload'); setItems([]); setFileName(null); }}
              className="flex items-center gap-2 px-6 py-4 rounded-xl border border-white/10 hover:bg-surface-hover text-gray-300 font-medium transition-colors"
            >
              <ExternalLink className="w-4 h-4" />
              Roast again
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Upload state
  return (
    <div className="flex-1 p-8 overflow-y-auto flex flex-col items-center justify-center h-full max-w-3xl mx-auto w-full text-center">
      <button
        onClick={() => navigate('/settings')}
        className="self-start flex items-center gap-2 text-gray-400 hover:text-white transition-colors mb-8 font-mono text-sm"
      >
        <ArrowLeft className="w-4 h-4" /> Back to settings
      </button>

      <div className="flex-1 flex flex-col items-center justify-center w-full">
        <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-surface border border-white/10 text-semantic-red mb-8">
          <Flame className="w-10 h-10" />
        </div>

        <h1 className="text-5xl font-sans font-bold tracking-tight text-white mb-6">
          Resume Roast
        </h1>

        <p className="text-xl text-gray-400 font-sans mb-12 max-w-xl leading-relaxed">
          Upload your CV. The AI will tear it apart, tell you exactly why recruiters are ignoring it, and then fix it for you.
        </p>

        <div className="w-full max-w-md relative group">
          <input
            type="file"
            accept=".pdf,.doc,.docx"
            onChange={handleUpload}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
          />
          <div className="border-2 border-dashed border-white/20 rounded-2xl p-12 bg-surface group-hover:bg-surface-hover group-hover:border-accent/50 transition-all flex flex-col items-center justify-center gap-4">
            <UploadCloud className="w-12 h-12 text-gray-500 group-hover:text-accent transition-colors" />
            <div className="space-y-1">
              <p className="text-white font-medium font-sans text-lg">Drop your resume here</p>
              <p className="text-gray-500 font-mono text-sm">PDF, DOCX up to 5MB</p>
            </div>
          </div>
        </div>

        <p className="mt-6 text-xs font-mono text-gray-600">
          Warning: this will be honest. Possibly uncomfortably so.
        </p>
      </div>
    </div>
  );
};
