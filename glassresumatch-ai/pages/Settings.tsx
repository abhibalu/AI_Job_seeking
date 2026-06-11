/**
 * Settings.tsx — OotoCV reference layout, folded with live service controls.
 *
 * Sections (top → bottom):
 *   1. API Keys (display-only — keys live in backend .env; surface masked)
 *   2. Integrations (Google Account — connect/disconnect placeholder)
 *   3. Base Resume (server-confirmed current resume indicator + Update)
 *   4. External Services (ADR-0019 kill switches: OpenRouter / Apify / Google Docs)
 *   5. Resume Roast (link to /roast)
 *
 * Section 4 is the only deviation from the reference Settings — it
 * preserves the kill-switch UI that already existed in the live app and
 * fits the reference's "Settings = your arsenal" theme.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ExternalLink,
  FileJson,
  Flame,
  Key,
  Loader2,
  Mail,
  Shield,
} from 'lucide-react';

import { cn } from '../lib/utils';
import { apiClient } from '../services/apiClient';
import type { ServiceToggles } from '../services/apiClient';

interface MasterResumeSummary {
  name?: string | null;
  updatedAt?: string | null;
  sourceGdocUrl?: string | null;
}

export const Settings: React.FC = () => {
  const navigate = useNavigate();

  const [master, setMaster] = useState<MasterResumeSummary | null>(null);
  const [toggles, setToggles] = useState<ServiceToggles | null>(null);
  const [togglePending, setTogglePending] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    apiClient.getMasterResume()
      .then(data => {
        if (cancelled) return;
        setMaster({
          name: data?.name ?? data?.basics?.name ?? 'base_resume',
          updatedAt: data?.updatedAt ?? data?.updated_at ?? null,
          sourceGdocUrl: data?.sourceGdocUrl ?? data?.gdoc_url ?? null,
        });
      })
      .catch(() => { if (!cancelled) setMaster(null); });
    apiClient.getServiceToggles()
      .then(t => { if (!cancelled) setToggles(t); })
      .catch(() => { if (!cancelled) setToggles(null); });
    return () => { cancelled = true; };
  }, []);

  const flipToggle = useCallback(async (service: keyof ServiceToggles) => {
    if (!toggles) return;
    const next = !toggles[service];
    setTogglePending(service);
    setToggles({ ...toggles, [service]: next });   // optimistic
    try {
      const updated = await apiClient.updateServiceToggle(service, next);
      setToggles(updated);
    } catch {
      setToggles(toggles);                          // roll back
    } finally {
      setTogglePending(null);
    }
  }, [toggles]);

  const updatedLabel = master?.updatedAt
    ? new Date(master.updatedAt).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })
    : null;

  return (
    <div className="flex-1 p-8 overflow-y-auto max-w-4xl mx-auto w-full">
      <header className="mb-10">
        <h1 className="text-3xl font-sans font-bold tracking-tight text-white mb-2">Settings</h1>
        <p className="text-gray-400 font-mono text-sm">
          API keys, integrations, and your base resume. Nothing else.
        </p>
      </header>

      <div className="space-y-8">
        {/* API Keys */}
        <section className="bg-surface border border-white/5 rounded-2xl p-6">
          <h2 className="text-xl font-sans font-semibold text-white mb-6 flex items-center gap-2">
            <Key className="w-5 h-5 text-accent" />
            API Keys
          </h2>
          <div className="space-y-6">
            <div>
              <label className="block font-mono text-sm text-gray-400 uppercase tracking-wider mb-2">
                OpenRouter API Key
              </label>
              <input
                type="password"
                defaultValue="sk-or-v1-•••••••••••••••"
                disabled
                className="w-full bg-base border border-white/10 rounded-xl px-4 py-3 text-gray-500 font-mono cursor-not-allowed"
              />
              <p className="text-xs text-gray-500 mt-2 font-mono">
                Server-side via .env. Edit on the backend host to change.
              </p>
            </div>
            <div>
              <label className="block font-mono text-sm text-gray-400 uppercase tracking-wider mb-2">
                Apify API Token
              </label>
              <input
                type="password"
                defaultValue="apify_api_•••••••••••••••"
                disabled
                className="w-full bg-base border border-white/10 rounded-xl px-4 py-3 text-gray-500 font-mono cursor-not-allowed"
              />
              <p className="text-xs text-gray-500 mt-2 font-mono">
                Same — managed in backend .env.
              </p>
            </div>
          </div>
        </section>

        {/* Integrations */}
        <section className="bg-surface border border-white/5 rounded-2xl p-6">
          <h2 className="text-xl font-sans font-semibold text-white mb-6 flex items-center gap-2">
            <Mail className="w-5 h-5 text-accent" />
            Integrations
          </h2>
          <div className="flex items-center justify-between p-4 bg-base rounded-xl border border-white/5">
            <div>
              <h3 className="text-white font-medium">Google Account</h3>
              <p className="text-sm text-gray-400">
                {toggles?.google_docs ? 'Connected for Drive export.' : 'Disabled — enable below to use Drive export.'}
              </p>
            </div>
            <a
              href="https://myaccount.google.com/permissions"
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 rounded-lg border border-white/10 text-sm font-medium text-gray-300 hover:bg-white/5 transition-colors flex items-center gap-2"
            >
              Manage <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        </section>

        {/* Base Resume */}
        <section className="bg-surface border border-white/5 rounded-2xl p-6">
          <h2 className="text-xl font-sans font-semibold text-white mb-6 flex items-center gap-2">
            <FileJson className="w-5 h-5 text-accent" />
            Base Resume
          </h2>
          <div className="flex items-center justify-between p-4 bg-base rounded-xl border border-white/5">
            <div>
              <h3 className="text-white font-medium">
                {master?.name ?? 'No resume on file yet.'}
              </h3>
              <p className="text-sm text-gray-400">
                {updatedLabel ? `Last updated ${updatedLabel}` : 'Upload one in onboarding or here.'}
                {master?.sourceGdocUrl && (
                  <>
                    {' · '}
                    <a
                      href={master.sourceGdocUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-accent hover:underline"
                    >
                      open source doc ↗
                    </a>
                  </>
                )}
              </p>
            </div>
            <button
              onClick={() => navigate('/onboarding')}
              className="px-4 py-2 rounded-lg border border-white/10 text-sm font-medium text-gray-300 hover:bg-white/5 transition-colors"
            >
              Update File
            </button>
          </div>
        </section>

        {/* External Services kill switches (ADR-0019) */}
        <section className="bg-surface border border-white/5 rounded-2xl p-6">
          <h2 className="text-xl font-sans font-semibold text-white mb-1 flex items-center gap-2">
            <Shield className="w-5 h-5 text-accent" />
            External Services
          </h2>
          <p className="text-sm text-gray-400 font-sans mb-6">
            Hard off-switches for outbound traffic. Different from pipeline modes — these
            short-circuit the integration entirely rather than just pausing the cron.
          </p>
          {toggles == null ? (
            <p className="text-xs font-mono text-gray-500">Loading…</p>
          ) : (
            <div className="space-y-3">
              {(['openrouter', 'apify', 'google_docs'] as Array<keyof ServiceToggles>).map(svc => {
                const enabled = toggles[svc];
                const pending = togglePending === svc;
                return (
                  <div key={svc} className="flex items-center justify-between p-4 bg-base rounded-xl border border-white/5">
                    <div>
                      <h3 className="text-white font-medium capitalize">
                        {svc === 'google_docs' ? 'Google Docs' : svc}
                      </h3>
                      <p className="text-xs text-gray-500 font-mono">
                        {svc === 'openrouter' && 'LLM evaluation + tailoring.'}
                        {svc === 'apify'      && 'LinkedIn scraping.'}
                        {svc === 'google_docs' && 'Resume export to Drive.'}
                      </p>
                    </div>
                    <button
                      onClick={() => flipToggle(svc)}
                      disabled={pending}
                      className={cn(
                        'flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-mono font-medium transition-colors',
                        enabled
                          ? 'bg-semantic-green/10 text-semantic-green border border-semantic-green/20 hover:bg-semantic-green/20'
                          : 'bg-semantic-red/10 text-semantic-red border border-semantic-red/20 hover:bg-semantic-red/20',
                        pending && 'opacity-50 cursor-wait',
                      )}
                    >
                      {pending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                      {enabled ? 'Enabled' : 'Disabled'}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* Resume Roast */}
        <section className="bg-surface border border-white/5 rounded-2xl p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-sans font-semibold text-white mb-1 flex items-center gap-2">
                <Flame className="w-5 h-5 text-semantic-red" />
                Resume Roast
              </h2>
              <p className="text-sm text-gray-400 font-sans">
                Get a brutal, honest AI critique of your base resume. Not for the faint-hearted.
              </p>
            </div>
            <button
              onClick={() => navigate('/roast')}
              className="flex items-center gap-2 px-5 py-3 rounded-xl border border-semantic-red/20 bg-semantic-red/5 text-semantic-red font-mono text-sm font-medium hover:bg-semantic-red/10 transition-colors whitespace-nowrap"
            >
              <ExternalLink className="w-4 h-4" />
              Roast my CV
            </button>
          </div>
        </section>
      </div>
    </div>
  );
};
