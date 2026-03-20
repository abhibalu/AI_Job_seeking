import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, Loader2, X, Link2 } from 'lucide-react';
import { cn } from '../lib/utils';
import { apiClient } from '../services/apiClient';
import { Toast } from '../components/Toast';
import { formatTimeAgo } from '../utils/format';

interface SetupPageProps {
  isOnboarding: boolean;
  onComplete?: () => void;
}

type ImportSource = 'file' | 'gdoc';

type FlowPhase =
  | { phase: 'idle' }
  | { phase: 'gdoc_input'; url: string; urlError: string | null }
  | { phase: 'uploading'; source: ImportSource; label: string }
  | { phase: 'done' }
  | { phase: 'error'; source: ImportSource; message: string };

function extractDocId(url: string): string | null {
  const match = url.match(/\/d\/([a-zA-Z0-9_-]+)\//);
  return match ? match[1] : null;
}

export const SetupPage: React.FC<SetupPageProps> = ({ isOnboarding, onComplete }) => {
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);
  const [flow, setFlow] = useState<FlowPhase>({ phase: 'idle' });
  const [settingsToast, setSettingsToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [currentResume, setCurrentResume] = useState<{ fullName: string; updatedAt?: string; sourceGdocUrl?: string } | null>(null);

  useEffect(() => {
    if (isOnboarding) return;
    apiClient.getMasterResume()
      .then(r => setCurrentResume({ fullName: r.fullName, updatedAt: r.updatedAt, sourceGdocUrl: r.sourceGdocUrl }))
      .catch(() => {});
  }, [isOnboarding]);

  function refreshCurrentResume() {
    apiClient.getMasterResume()
      .then(r => setCurrentResume({ fullName: r.fullName, updatedAt: r.updatedAt, sourceGdocUrl: r.sourceGdocUrl }))
      .catch(() => {});
  }

  function startPolling(onSuccess: () => void, onTimeout: () => void) {
    const poll = setInterval(async () => {
      try {
        const resume = await apiClient.getMasterResume();
        if (resume && resume.status !== 'processing' && resume.fullName) {
          clearInterval(poll);
          clearTimeout(timeout);
          onSuccess();
        }
      } catch {}
    }, 2000);
    const timeout = setTimeout(() => {
      clearInterval(poll);
      onTimeout();
    }, 60000);
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;

    setFlow({ phase: 'uploading', source: 'file', label: 'Reading your CV…' });
    try {
      await apiClient.uploadResume(file);
      startPolling(
        () => {
          if (isOnboarding) {
            setFlow({ phase: 'done' });
            localStorage.setItem('onboarding_complete', 'true');
            setTimeout(() => {
              if (onComplete) onComplete();
              else navigate('/');
            }, 300);
          } else {
            setFlow({ phase: 'idle' });
            setSettingsToast({ message: "CV updated. You're good to go.", type: 'success' });
            refreshCurrentResume();
          }
        },
        () => {
          setFlow({ phase: 'error', source: 'file', message: 'Parse timed out. Happens sometimes. Try again.' });
        }
      );
    } catch (err: any) {
      setFlow({ phase: 'error', source: 'file', message: err.message });
    }
  };

  const handleGdocImport = async () => {
    if (flow.phase !== 'gdoc_input') return;
    const docId = extractDocId(flow.url);
    if (!docId) {
      setFlow({ phase: 'gdoc_input', url: flow.url, urlError: "That doesn't look like a Google Docs URL" });
      return;
    }

    setFlow({ phase: 'uploading', source: 'gdoc', label: 'Pulling your doc…' });
    try {
      await apiClient.importFromGoogleDoc(docId);
      startPolling(
        () => {
          if (isOnboarding) {
            setFlow({ phase: 'done' });
            localStorage.setItem('onboarding_complete', 'true');
            setTimeout(() => {
              if (onComplete) onComplete();
              else navigate('/');
            }, 300);
          } else {
            setFlow({ phase: 'idle' });
            setSettingsToast({ message: "CV updated. You're good to go.", type: 'success' });
            refreshCurrentResume();
          }
        },
        () => {
          setFlow({ phase: 'error', source: 'gdoc', message: 'Parse timed out. Happens sometimes. Try again.' });
        }
      );
    } catch (err: any) {
      setFlow({ phase: 'error', source: 'gdoc', message: err.message });
    }
  };

  const handleSkip = () => {
    localStorage.setItem('onboarding_complete', 'true');
    if (onComplete) onComplete();
    else navigate('/');
  };

  if (isOnboarding) {
    return (
      <div className="min-h-screen bg-base flex items-center justify-center">
        <div className="max-w-lg w-full px-6">
          {/* First-run copy */}
          <div className="mb-10">
            <p className="font-mono text-sm text-gray-400 leading-relaxed">
              Let's be real. Job hunting is awful. You're here because you'd rather have an AI suffer through it. Excellent decision. Let's get you set up.
            </p>
          </div>

          <div className="space-y-6">
            <div>
              <div className="text-[9px] font-mono text-gray-500 uppercase tracking-widest mb-3">
                Step 1 — Your CV
              </div>
              <input
                type="file"
                accept=".pdf,.docx"
                ref={fileRef}
                className="hidden"
                onChange={handleFileChange}
              />

              {/* Idle / gdoc_input: two tiles + expanding input */}
              {(flow.phase === 'idle' || flow.phase === 'gdoc_input') && (
                <>
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      onClick={() => fileRef.current?.click()}
                      className="flex flex-col items-center justify-center gap-2 flex-1 px-4 py-6 rounded-xl border border-white/[0.08] bg-surface hover:border-white/15 hover:bg-surface-hover transition-colors duration-100 cursor-pointer min-h-[88px]"
                    >
                      <Upload className="w-5 h-5 text-gray-400" />
                      <div className="text-center">
                        <div className="font-mono text-sm text-gray-300">Upload file</div>
                        <div className="font-mono text-[10px] text-gray-600">PDF or DOCX</div>
                      </div>
                    </button>

                    <button
                      onClick={() => setFlow({ phase: 'gdoc_input', url: '', urlError: null })}
                      className={cn(
                        'flex flex-col items-center justify-center gap-2 flex-1 px-4 py-6 rounded-xl border bg-surface hover:bg-surface-hover transition-colors duration-100 cursor-pointer min-h-[88px]',
                        flow.phase === 'gdoc_input'
                          ? 'border-accent/40'
                          : 'border-white/[0.08] hover:border-white/15'
                      )}
                    >
                      <Link2 className="w-5 h-5 text-gray-400" />
                      <div className="text-center">
                        <div className="font-mono text-sm text-gray-300">Google Doc</div>
                        <div className="font-mono text-[10px] text-gray-600">Paste a URL</div>
                      </div>
                    </button>
                  </div>

                  <div className={cn(
                    'overflow-hidden transition-all duration-150',
                    flow.phase === 'gdoc_input' ? 'max-h-32 opacity-100' : 'max-h-0 opacity-0 pointer-events-none'
                  )}>
                    <div className="pt-3 space-y-1.5">
                      <div className="flex items-center gap-2">
                        <input
                          value={flow.phase === 'gdoc_input' ? flow.url : ''}
                          onChange={e => flow.phase === 'gdoc_input' && setFlow({ phase: 'gdoc_input', url: e.target.value, urlError: null })}
                          placeholder="Paste your Google Docs URL"
                          className="flex-1 px-3 py-2.5 bg-surface border border-white/[0.08] rounded-lg font-mono text-sm text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-accent/60"
                        />
                        <button
                          onClick={handleGdocImport}
                          className="px-4 py-2.5 bg-accent text-[#0d0d0d] font-mono text-sm rounded-lg cursor-pointer hover:bg-accent/90 transition-colors whitespace-nowrap"
                        >
                          Import →
                        </button>
                        <button
                          onClick={() => setFlow({ phase: 'idle' })}
                          className="text-gray-600 hover:text-gray-400 transition-colors cursor-pointer"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                      {flow.phase === 'gdoc_input' && flow.urlError && (
                        <p className="text-[11px] font-mono text-semantic-red">{flow.urlError}</p>
                      )}
                    </div>
                  </div>
                </>
              )}

              {/* Uploading / done: spinner block */}
              {(flow.phase === 'uploading' || flow.phase === 'done') && (
                <div className="flex flex-col items-center justify-center gap-2 px-4 py-6 rounded-xl border border-white/[0.08] bg-surface min-h-[88px]">
                  <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
                  <span className="font-mono text-sm text-gray-300">
                    {flow.phase === 'uploading' ? flow.label : ''}
                  </span>
                  <span className="font-mono text-[10px] text-gray-600">This takes 10–30 seconds.</span>
                </div>
              )}

              {/* Error */}
              {flow.phase === 'error' && (
                <div className="px-4 py-5 rounded-xl border border-semantic-red/20 bg-semantic-red/5">
                  <p className="font-mono text-sm text-semantic-red mb-2">{flow.message}</p>
                  <button
                    onClick={() => setFlow({ phase: 'idle' })}
                    className="text-[11px] font-mono text-accent underline underline-offset-2 cursor-pointer"
                  >
                    Try again
                  </button>
                </div>
              )}
            </div>

            {/* Skip — only in idle/gdoc_input */}
            {(flow.phase === 'idle' || flow.phase === 'gdoc_input') && (
              <button
                onClick={handleSkip}
                className="w-full text-center text-[10px] font-mono text-gray-600 hover:text-gray-400 transition-colors cursor-pointer py-2"
              >
                Skip for now — upload later
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Settings mode (non-onboarding)
  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-2xl mx-auto p-8">
        <h1 className="text-2xl font-bold text-gray-100 mb-6">Settings</h1>

        <div className="space-y-6">
          {/* CV Upload */}
          <div className="p-5 rounded-xl border border-white/5 bg-surface">
            <div className="text-[9px] font-mono text-gray-500 uppercase tracking-widest mb-3">Base CV</div>
            <input
              type="file"
              accept=".pdf,.docx"
              ref={fileRef}
              className="hidden"
              onChange={handleFileChange}
            />

            {/* Idle: two pill buttons */}
            {flow.phase === 'idle' && (
              <div>
                {currentResume && (
                  <div className="flex items-center gap-2 mb-3">
                    <span className="font-mono text-[11px] text-semantic-green">✓</span>
                    <span className="font-mono text-sm text-gray-300">{currentResume.fullName}</span>
                    {currentResume.updatedAt && (
                      <span className="font-mono text-[11px] text-gray-600">
                        · updated {formatTimeAgo(currentResume.updatedAt)}
                      </span>
                    )}
                    {currentResume.sourceGdocUrl && (
                      <a
                        href={currentResume.sourceGdocUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-mono text-[11px] text-gray-600 hover:text-gray-400 transition-colors"
                      >
                        · open doc ↗
                      </a>
                    )}
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => fileRef.current?.click()}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg border border-white/[0.08] bg-surface-hover text-gray-300 hover:border-white/15 transition-colors cursor-pointer font-mono text-sm"
                  >
                    <Upload className="w-4 h-4" /> Upload file
                  </button>
                  <button
                    onClick={() => setFlow({ phase: 'gdoc_input', url: '', urlError: null })}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg border border-white/[0.08] bg-surface-hover text-gray-300 hover:border-white/15 transition-colors cursor-pointer font-mono text-sm"
                  >
                    <Link2 className="w-4 h-4" /> Google Doc
                  </button>
                </div>
              </div>
            )}

            {/* GDoc input: compact single-row */}
            {flow.phase === 'gdoc_input' && (
              <div className="space-y-1.5">
                <div className="flex items-center gap-2">
                  <input
                    value={flow.url}
                    onChange={e => setFlow({ phase: 'gdoc_input', url: e.target.value, urlError: null })}
                    placeholder="Paste your Google Docs URL"
                    className="flex-1 px-3 py-2 bg-surface-hover border border-white/[0.08] rounded-lg font-mono text-sm text-gray-200 placeholder:text-gray-600 focus:outline-none focus:border-accent/60"
                  />
                  <button
                    onClick={handleGdocImport}
                    className="px-4 py-2 bg-accent text-[#0d0d0d] font-mono text-sm rounded-lg cursor-pointer hover:bg-accent/90 transition-colors whitespace-nowrap"
                  >
                    Import →
                  </button>
                  <button
                    onClick={() => setFlow({ phase: 'idle' })}
                    className="text-gray-600 hover:text-gray-400 transition-colors cursor-pointer"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
                {flow.urlError && (
                  <p className="text-[11px] font-mono text-semantic-red">{flow.urlError}</p>
                )}
              </div>
            )}

            {/* Uploading: inline spinner */}
            {flow.phase === 'uploading' && (
              <div className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
                <span className="font-mono text-sm text-gray-300">{flow.label}</span>
              </div>
            )}

            {/* Error: inline red text + retry */}
            {flow.phase === 'error' && (
              <div>
                <p className="font-mono text-sm text-semantic-red mb-1">{flow.message}</p>
                <button
                  onClick={() => setFlow({ phase: 'idle' })}
                  className="text-[11px] font-mono text-accent underline underline-offset-2 cursor-pointer"
                >
                  Try again
                </button>
              </div>
            )}
          </div>

          {/* Placeholder for future settings */}
          <div className="p-5 rounded-xl border border-white/5 bg-surface">
            <div className="text-[9px] font-mono text-gray-500 uppercase tracking-widest mb-3">API Keys</div>
            <p className="text-[11px] font-mono text-gray-600">Configuration coming soon.</p>
          </div>
        </div>
      </div>

      {settingsToast && (
        <Toast
          message={settingsToast.message}
          type={settingsToast.type}
          onDismiss={() => setSettingsToast(null)}
        />
      )}
    </div>
  );
};
