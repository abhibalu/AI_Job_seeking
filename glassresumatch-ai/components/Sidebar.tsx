/**
 * Sidebar.tsx — OotoCV reference verbatim, wired to /api/system/status.
 *
 * Rotating cron messages (5s interval) only run when cron_state === 'active'.
 * `/api/system/status` returns the three-field shape (cron_state /
 * next_run_at / last_error) so we can drive the pulse and hover label
 * directly without re-deriving state.
 */
import React, { useEffect, useMemo, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { Activity, Briefcase, Settings as SettingsIcon } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';

import { cn } from '../lib/utils';
import { apiClient } from '../services/apiClient';

const cronMessages = [
  'Hunting while you sleep',
  'Judging JDs for you',
  'Working the night shift',
  'Rejecting in silence',
  'Caffeinating on your behalf',
];

type CronState = 'active' | 'sleeping' | 'error';

interface SidebarProps {
  actionableBadge?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({ actionableBadge }) => {
  const [cronState, setCronState] = useState<CronState>('sleeping');
  const [nextRunAt, setNextRunAt] = useState<string | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);
  const [cronMessageIndex, setCronMessageIndex] = useState(0);

  // Rotate the active-state hype copy.
  useEffect(() => {
    if (cronState !== 'active') return;
    const interval = setInterval(() => {
      setCronMessageIndex((prev) => (prev + 1) % cronMessages.length);
    }, 5000);
    return () => clearInterval(interval);
  }, [cronState]);

  // Poll system status. 30s is enough — cron state only changes when a
  // job starts/ends (ADR-0024-adjacent decision; the 5s rotation is
  // client-side cosmetic, not a poll target).
  useEffect(() => {
    let cancelled = false;
    const fetchStatus = async () => {
      try {
        const data = await apiClient.getSystemStatus();
        if (cancelled) return;
        setCronState(data.cron_state);
        setNextRunAt(data.next_run_at);
        setLastError(data.last_error);
      } catch {
        if (cancelled) return;
        setCronState('sleeping');
        setLastError(null);
      }
    };
    fetchStatus();
    const t = setInterval(fetchStatus, 30000);
    return () => { cancelled = true; clearInterval(t); };
  }, []);

  const navItems = useMemo(() => [
    {
      name: 'Feed',
      path: '/',
      end: true,
      icon: Briefcase,
      hint: "Today's matches",
      badge: actionableBadge && actionableBadge > 0 ? actionableBadge : undefined,
    },
    { name: 'Tracker',  path: '/tracker',  end: false, icon: Activity,    hint: 'The ghosting tracker' },
    { name: 'Settings', path: '/settings', end: false, icon: SettingsIcon, hint: 'Your arsenal' },
  ], [actionableBadge]);

  const hoverLabel = useMemo(() => {
    if (cronState === 'active') {
      if (nextRunAt) {
        const t = new Date(nextRunAt).toLocaleTimeString([], {
          hour: '2-digit', minute: '2-digit',
        });
        return `Next run: ${t}`;
      }
      return 'Running now';
    }
    if (cronState === 'error') {
      return lastError ? `${lastError.slice(0, 32)} — View logs →` : 'View logs →';
    }
    if (nextRunAt) {
      const t = new Date(nextRunAt).toLocaleTimeString([], {
        hour: '2-digit', minute: '2-digit',
      });
      return `Next run: ${t}`;
    }
    return 'Check setup';
  }, [cronState, nextRunAt, lastError]);

  return (
    <aside className="w-64 border-r border-white/5 bg-base flex flex-col h-screen sticky top-0">
      {/* Logo + wordmark */}
      <div className="p-6 flex items-center gap-3">
        <svg
          width="34" height="22"
          viewBox="0 0 34 22"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          style={{ isolation: 'isolate' }}
        >
          {[
            { cx: 9,  anim: 'animate-pulse-slow' },
            { cx: 17, anim: 'animate-pulse-slow-delay-1' },
            { cx: 25, anim: 'animate-pulse-slow-delay-2' },
          ].map(({ cx, anim }) => (
            <circle
              key={cx}
              cx={cx} cy={11} r={8}
              className={cn('fill-accent', cronState === 'active' && anim)}
              style={{ mixBlendMode: 'screen', opacity: cronState === 'active' ? undefined : 0.55 }}
            />
          ))}
        </svg>
        <span className="font-sans font-bold text-xl tracking-tight text-white">OotoCV</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-4 py-6 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.name}
            to={item.path}
            end={item.end}
            className={({ isActive }) =>
              cn(
                'group flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-surface text-accent'
                  : 'text-gray-400 hover:bg-surface-hover hover:text-gray-100'
              )
            }
          >
            <div className="flex items-center gap-3">
              <item.icon className="w-4 h-4" />
              {item.name}
              {item.badge !== undefined && (
                <span className="ml-1 px-1.5 py-0.5 rounded-md bg-accent/10 text-accent text-[10px] font-mono font-bold">
                  {item.badge}
                </span>
              )}
            </div>
            <span className="text-[10px] font-mono tracking-tight text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity">
              {item.hint}
            </span>
          </NavLink>
        ))}
      </nav>

      {/* Cron status */}
      <div className="p-4 border-t border-white/5">
        <div className="group relative flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-surface-hover transition-colors cursor-help overflow-hidden">
          <div className={cn(
            'shrink-0 w-2 h-2 rounded-full',
            cronState === 'active'   && 'bg-semantic-green animate-pulse-slow',
            cronState === 'sleeping' && 'bg-semantic-amber',
            cronState === 'error'    && 'bg-semantic-red',
          )} />
          <div className="relative h-4 w-[160px]">
            {/* Default label */}
            <div className="absolute inset-0 flex items-center opacity-100 group-hover:opacity-0 transition-opacity duration-300">
              <AnimatePresence mode="wait">
                <motion.span
                  key={cronState === 'active' ? cronMessageIndex : cronState}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.3 }}
                  className={cn(
                    'text-xs font-mono tracking-tight truncate',
                    cronState === 'error' ? 'text-semantic-red' : 'text-gray-400'
                  )}
                >
                  {cronState === 'active'   && cronMessages[cronMessageIndex]}
                  {cronState === 'sleeping' && 'Cron: Sleeping'}
                  {cronState === 'error'    && 'Cron: Failed'}
                </motion.span>
              </AnimatePresence>
            </div>
            {/* Hover label */}
            <div className="absolute inset-0 flex items-center opacity-0 group-hover:opacity-100 transition-opacity duration-300">
              <span className={cn(
                'text-xs font-mono tracking-tight truncate',
                cronState === 'error' ? 'text-semantic-red' : 'text-gray-300'
              )}>
                {hoverLabel}
              </span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
};
