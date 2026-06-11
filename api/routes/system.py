"""
GET /api/system/status — OotoCV sidebar pulse feed.

Reshapes the scheduler state into the three fields the OotoCV sidebar needs:

  cron_state  : 'active' | 'sleeping' | 'error'
  next_run_at : ISO timestamp of the next scheduled scrape/eval cron fire,
                or null if all stages are manual / scheduler is down.
  last_error  : human-readable error from the most recent failed run, or null.

The 5-second message rotation ("Hunting while you sleep" / "Caffeinating on
your behalf" / etc.) is purely client-side cosmetic and not driven by this
endpoint. Per ADR-0024-adjacent decision, the frontend polls this every 30s
instead of opening a dedicated SSE channel for system state.

State derivation:

  scheduler not running                  → 'error'   (with last_error if known)
  scheduler running, but no scheduled
  jobs have a next_run_time (all manual) → 'sleeping'
  scheduler running, at least one job
  has a next_run_time                    → 'active'
"""
import logging
from typing import Optional

from fastapi import APIRouter

from services.pipeline_runs import get_last_run
from services.scheduler import get_job_status, get_scheduler

logger = logging.getLogger(__name__)
router = APIRouter()

# Scheduler job IDs that count as "the agent is hunting" — i.e. user-visible
# work that should drive the sidebar pulse. The reaper is excluded because
# it's a housekeeping job; the user doesn't care about its next fire time.
_HUNT_JOB_IDS = {"scrape_worker", "eval_worker"}


def _next_run_from_jobs(jobs: list[dict]) -> Optional[str]:
    """Earliest next_run_utc across the hunt-relevant jobs, or None."""
    candidates = [
        j.get("next_run_utc") for j in jobs
        if j.get("id") in _HUNT_JOB_IDS and j.get("next_run_utc")
    ]
    return min(candidates) if candidates else None


def _last_error() -> Optional[str]:
    """Most recent error_detail across scrape/evaluate/tailor last-runs."""
    for run_type in ("scrape", "evaluate", "tailor"):
        run = get_last_run(run_type) or {}
        if run.get("status") == "failed":
            err = run.get("error_detail")
            if err:
                return err
    return None


@router.get("/status")
def system_status():
    """Sidebar state feed; see module docstring for shape."""
    scheduler = get_scheduler()
    running = scheduler is not None and scheduler.running

    last_err = _last_error()

    if not running:
        cron_state = "error"
        next_run_at = None
    else:
        jobs = get_job_status() or []
        next_run_at = _next_run_from_jobs(jobs)
        cron_state = "active" if next_run_at else "sleeping"

    return {
        "cron_state": cron_state,
        "next_run_at": next_run_at,
        "last_error": last_err,
    }
