"""
APScheduler integration for TailorAI background automation.

Registered in FastAPI on_startup. Runs:
  - ScrapeWorker  — controlled by SCRAPE_CRON (cron expr) or SCRAPE_INTERVAL_HOURS
  - EvalWorker    — controlled by EVAL_CRON (cron expr) or EVAL_INTERVAL_HOURS

Cron expressions take priority when set. Format: 'minute hour day month day_of_week'
  Examples:
    '* * * * *'      — every minute  (great for testing)
    '*/5 * * * *'    — every 5 minutes
    '0 */12 * * *'   — every 12 hours at :00
    '0 8,20 * * *'   — at 08:00 and 20:00 daily
    '0 9 * * 1-5'    — 09:00 on weekdays only

Set SCHEDULER_ENABLED=false in .env to disable entirely (e.g., for CI).
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from agents.database import get_system_config, _get_supabase
from backend.log_context import set_correlation_id
from backend.settings import settings

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(
            job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 300},
            timezone="UTC",
        )
    return _scheduler


def _build_trigger(cron_expr: str, interval_hours: int, label: str):
    """
    Return a CronTrigger if cron_expr is non-empty and valid,
    otherwise fall back to an IntervalTrigger with interval_hours.
    """
    if cron_expr.strip():
        try:
            parts = cron_expr.strip().split()
            if len(parts) != 5:
                raise ValueError("Cron expression must have exactly 5 fields")
            minute, hour, day, month, day_of_week = parts
            trigger = CronTrigger(
                minute=minute, hour=hour, day=day,
                month=month, day_of_week=day_of_week,
                timezone="UTC",
            )
            logger.info(f"[Scheduler] {label}: using CronTrigger '{cron_expr}'")
            return trigger
        except Exception as e:
            logger.warning(
                "[Scheduler] Invalid cron expression for %s ('%s'): %s. Falling back to interval of %dh.",
                label, cron_expr, e, interval_hours,
                exc_info=True,
            )
    logger.info(f"[Scheduler] {label}: using IntervalTrigger every {interval_hours}h")
    return IntervalTrigger(hours=interval_hours)


def reap_stale_tailoring_runs():
    """Sweep resumes rows stuck in tailoring_status='processing'.

    Timeout is operator-tunable via system_config[
    'tailoring_processing_timeout_minutes'] (default 15). Job runs every
    5 minutes (configured in start_scheduler()). Worst-case wasted-LLM
    window: 19m59s (timeout + interval).

    Per ADR-0017 the APScheduler thread does not inherit contextvars,
    so we set correlation_id explicitly at entry."""
    from datetime import datetime, timedelta, timezone

    set_correlation_id("reaper")
    try:
        timeout_min = 15
        raw = get_system_config("tailoring_processing_timeout_minutes")
        if raw:
            try:
                timeout_min = int(raw)
            except (TypeError, ValueError):
                logger.warning(
                    "reaper.invalid_timeout_config",
                    extra={"raw_value": raw, "default_used": timeout_min},
                )
        threshold = datetime.now(timezone.utc) - timedelta(minutes=timeout_min)

        client = _get_supabase()
        result = (
            client.table("resumes")
            .update({
                "tailoring_status": "cancelled",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("tailoring_status", "processing")
            .lt("processing_started_at", threshold.isoformat())
            .execute()
        )
        reaped = len(result.data or [])
        if reaped:
            logger.warning(
                "reaper.cancelled_stale_processing",
                extra={"count": reaped, "timeout_minutes": timeout_min},
            )
    finally:
        set_correlation_id(None)


def start_scheduler() -> None:
    """Start the background scheduler and register jobs. Called from FastAPI startup."""
    if not settings.SCHEDULER_ENABLED:
        logger.info("[Scheduler] SCHEDULER_ENABLED=false — scheduler not started.")
        return

    scheduler = get_scheduler()

    if scheduler.running:
        logger.warning("[Scheduler] Already running — skipping start.")
        return

    from services.scraper_worker import run_scrape_worker
    from services.eval_worker import run_eval_worker

    scheduler.add_job(
        run_scrape_worker,
        trigger=_build_trigger(settings.SCRAPE_CRON, settings.SCRAPE_INTERVAL_HOURS, "ScrapeWorker"),
        id="scrape_worker",
        name="LinkedIn Scraper",
        replace_existing=True,
    )

    scheduler.add_job(
        run_eval_worker,
        trigger=_build_trigger(settings.EVAL_CRON, settings.EVAL_INTERVAL_HOURS, "EvalWorker"),
        id="eval_worker",
        name="Job Evaluator",
        replace_existing=True,
    )

    scheduler.add_job(
        reap_stale_tailoring_runs,
        trigger=IntervalTrigger(minutes=5),
        id="reap_stale_tailoring_runs",
        name="Tailoring Reaper",
        coalesce=True,
        max_instances=1,
        replace_existing=True,
    )

    scheduler.start()
    logger.info("[Scheduler] Started.")


def stop_scheduler() -> None:
    """Gracefully shut down the scheduler. Called from FastAPI shutdown."""
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[Scheduler] Stopped.")


def get_job_status() -> list[dict]:
    """Return APScheduler job metadata for the status endpoint."""
    scheduler = get_scheduler()
    if not scheduler.running:
        return []
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_utc": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        })
    return jobs
