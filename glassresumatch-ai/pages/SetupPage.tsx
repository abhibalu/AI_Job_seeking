import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, Loader2, Check, X } from 'lucide-react';
import { cn } from '../lib/utils';
import { apiClient } from '../services/apiClient';

interface SetupPageProps {
  isOnboarding: boolean;
  onComplete?: () => void;
}

export const SetupPage: React.FC<SetupPageProps> = ({ isOnboarding, onComplete }) => {
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadDone, setUploadDone] = useState(false);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      await apiClient.uploadResume(file);

      // Poll until parsing completes
      const poll = setInterval(async () => {
        try {
          const resume = await apiClient.getMasterResume();
          if (resume && resume.status !== 'processing' && resume.fullName) {
            clearInterval(poll);
            setUploading(false);
            setUploadDone(true);
            localStorage.setItem('onboarding_complete', 'true');
            if (onComplete) onComplete();
            else navigate('/');
          }
        } catch {}
      }, 2000);

      // Timeout after 60s
      setTimeout(() => {
        clearInterval(poll);
        setUploading(false);
      }, 60000);
    } catch {
      setUploading(false);
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

          {/* Upload */}
          <div className="space-y-6">
            <div>
              <div className="text-[9px] font-mono text-gray-500 uppercase tracking-widest mb-3">
                Step 1 — Your CV
              </div>
              <input
                type="file"
                accept=".pdf,.docx,.json"
                ref={fileRef}
                className="hidden"
                onChange={handleUpload}
              />
              <button
                onClick={() => fileRef.current?.click()}
                disabled={uploading || uploadDone}
                className={cn(
                  'w-full flex items-center justify-center gap-3 px-6 py-4 rounded-xl border transition-all cursor-pointer',
                  uploadDone
                    ? 'border-semantic-green/30 bg-semantic-green/5 text-semantic-green'
                    : 'border-white/[0.08] bg-surface hover:border-white/15 text-gray-300'
                )}
              >
                {uploading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : uploadDone ? (
                  <Check className="w-5 h-5" />
                ) : (
                  <Upload className="w-5 h-5" />
                )}
                <span className="font-mono text-sm">
                  {uploading ? 'Analyzing your CV...' : uploadDone ? 'CV uploaded' : 'Upload your CV (.pdf, .docx)'}
                </span>
              </button>
            </div>

            {/* Skip */}
            <button
              onClick={handleSkip}
              className="w-full text-center text-[10px] font-mono text-gray-600 hover:text-gray-400 transition-colors cursor-pointer py-2"
            >
              Skip for now — upload later
            </button>
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
              accept=".pdf,.docx,.json"
              ref={fileRef}
              className="hidden"
              onChange={handleUpload}
            />
            <button
              onClick={() => fileRef.current?.click()}
              disabled={uploading}
              className="flex items-center gap-2 px-4 py-2.5 rounded-lg border border-white/[0.08] bg-surface-hover text-gray-300 hover:border-white/15 transition-colors cursor-pointer text-sm"
            >
              {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
              {uploading ? 'Uploading...' : 'Upload new CV'}
            </button>
          </div>

          {/* Placeholder for future settings */}
          <div className="p-5 rounded-xl border border-white/5 bg-surface">
            <div className="text-[9px] font-mono text-gray-500 uppercase tracking-widest mb-3">API Keys</div>
            <p className="text-[11px] font-mono text-gray-600">Configuration coming soon.</p>
          </div>
        </div>
      </div>
    </div>
  );
};
