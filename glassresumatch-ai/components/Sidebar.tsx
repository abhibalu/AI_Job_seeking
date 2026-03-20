import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { LayoutGrid, ClipboardList, Settings } from 'lucide-react';
import { cn } from '../lib/utils';
import { AnimatePresence, motion } from 'motion/react';
import { apiClient } from '../services/apiClient';
import { formatTimeAgo } from '../utils/format';

interface SidebarProps {
  actionableBadge: number;
}

interface SchedulerState {
  status: 'active' | 'sleeping' | 'error';
  message: string;
  hoverMessage: string;
}

export const Sidebar: React.FC<SidebarProps> = ({ actionableBadge }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [cronHovered, setCronHovered] = useState(false);
  const [scheduler, setScheduler] = useState<SchedulerState>({
    status: 'sleeping',
    message: 'Checking scheduler…',
    hoverMessage: 'Check setup',
  });

  // Poll scheduler status every 60s
  useEffect(() => {
    let cancelled = false;

    const fetchStatus = async () => {
      try {
        const data = await apiClient.getSchedulerStatus();
        if (cancelled) return;

        const lastRuns = data.last_runs || {};
        const isRunning = data.scheduler_running ||
          Object.values(lastRuns).some((r: any) => r?.status === 'running');
        const hasFailed = Object.values(lastRuns).some((r: any) => r?.status === 'failed');

        if (isRunning) {
          setScheduler({
            status: 'active',
            message: 'Running now…',
            hoverMessage: data.jobs?.[0]?.next_run_utc
              ? `Next: ${new Date(data.jobs[0].next_run_utc).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
              : 'Running…',
          });
        } else if (hasFailed) {
          setScheduler({
            status: 'error',
            message: 'Last run failed',
            hoverMessage: 'View logs →',
          });
        } else {
          // Find most recent finished_at across all runs
          const finishedTimes = Object.values(lastRuns)
            .map((r: any) => r?.finished_at)
            .filter(Boolean);
          const lastFinished = finishedTimes.length > 0
            ? finishedTimes.sort().pop()
            : null;

          setScheduler({
            status: 'sleeping',
            message: lastFinished ? `Last run ${formatTimeAgo(lastFinished)}` : 'No runs yet',
            hoverMessage: data.jobs?.[0]?.next_run_utc
              ? `Next: ${new Date(data.jobs[0].next_run_utc).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
              : 'Check setup',
          });
        }
      } catch {
        if (cancelled) return;
        setScheduler({
          status: 'sleeping',
          message: 'Scheduler unavailable',
          hoverMessage: 'Check setup',
        });
      }
    };

    fetchStatus();
    const t = setInterval(fetchStatus, 60000);
    return () => { cancelled = true; clearInterval(t); };
  }, []);

  const navItems = [
    { path: '/', label: 'Feed', hint: 'Today\'s matches', icon: LayoutGrid },
    { path: '/tracker', label: 'Tracker', hint: 'Applications', icon: ClipboardList },
    { path: '/settings', label: 'Settings', hint: 'Config', icon: Settings },
  ];

  return (
    <aside className="w-64 h-screen flex-shrink-0 bg-surface border-r border-white/5 flex flex-col">
      {/* Logo */}
      <div className="px-5 pt-5 pb-4">
        <div className="flex items-center gap-3">
          <svg
            width="34"
            height="22"
            viewBox="0 0 34 22"
            fill="none"
            style={{ isolation: 'isolate' }}
          >
            <circle cx="9" cy="11" r="8" className="fill-accent animate-pulse-slow" style={{ mixBlendMode: 'screen' }} />
            <circle cx="17" cy="11" r="8" className="fill-accent animate-pulse-slow-delay-1" style={{ mixBlendMode: 'screen' }} />
            <circle cx="25" cy="11" r="8" className="fill-accent animate-pulse-slow-delay-2" style={{ mixBlendMode: 'screen' }} />
          </svg>
          <span className="font-mono text-xs text-gray-500 tracking-wider uppercase">OotoCV</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-2 space-y-1">
        {navItems.map(({ path, label, hint, icon: Icon }) => {
          const isActive = path === '/'
            ? location.pathname === '/'
            : location.pathname.startsWith(path);

          return (
            <button
              key={path}
              onClick={() => navigate(path)}
              className={cn(
                'group w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors cursor-pointer',
                isActive
                  ? 'bg-surface-hover text-accent'
                  : 'text-gray-400 hover:bg-surface-hover hover:text-gray-100'
              )}
            >
              <Icon className="w-4 h-4" />
              <span>{label}</span>
              <span className={cn(
                'ml-auto text-[10px] font-mono tracking-tight text-gray-500',
                'opacity-0 group-hover:opacity-100 transition-opacity',
              )}>
                {hint}
              </span>
            </button>
          );
        })}
      </nav>

      {/* Cron Status */}
      <div
        className="px-4 py-3 border-t border-white/5"
        onMouseEnter={() => setCronHovered(true)}
        onMouseLeave={() => setCronHovered(false)}
      >
        <div className="flex items-center gap-2">
          <div className={cn(
            'w-2 h-2 rounded-full',
            scheduler.status === 'active' && 'bg-semantic-green animate-pulse',
            scheduler.status === 'sleeping' && 'bg-semantic-amber',
            scheduler.status === 'error' && 'bg-semantic-red',
          )} />
          <AnimatePresence mode="wait">
            <motion.span
              key={cronHovered ? 'hover' : scheduler.message}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
              className={cn(
                'text-[10px] font-mono text-gray-500 truncate',
                cronHovered && scheduler.status === 'error' && 'cursor-pointer',
              )}
              onClick={cronHovered && scheduler.status === 'error' ? () => navigate('/settings') : undefined}
            >
              {cronHovered ? scheduler.hoverMessage : scheduler.message}
            </motion.span>
          </AnimatePresence>
        </div>
      </div>
    </aside>
  );
};
