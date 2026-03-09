"""
APScheduler integration for TailorAI background automation.

Registered in FastAPI on_startup. Runs:
  - ScrapeWorker  every SCRAPE_INTERVAL_HOURS  (default: 12h)
  - EvalWorker    every EVAL_INTERVAL_HOURS     (default: 1h)

Set SCHEDULER_ENABLED=false in .env to disable entirely (e.g., for testing).
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

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


def start_scheduler() -> None:
    """Start the background scheduler and register jobs. Called from FastAPI startup."""
    if not settings.SCHEDULER_ENABLED:
        logger.info("[Scheduler] SCHEDULER_ENABLED=false — scheduler not started.")
        return

    scheduler = get_scheduler()

    if scheduler.running:
        logger.warning("[Scheduler] Already running — skipping start.")
        return

    # Import workers here to avoid circular imports at module load time
    from services.scraper_worker import run_scrape_worker
    from services.eval_worker import run_eval_worker

    scheduler.add_job(
        run_scrape_worker,
        trigger=IntervalTrigger(hours=settings.SCRAPE_INTERVAL_HOURS),
        id="scrape_worker",
        name="LinkedIn Scraper",
        replace_existing=True,
    )

    scheduler.add_job(
        run_eval_worker,
        trigger=IntervalTrigger(hours=settings.EVAL_INTERVAL_HOURS),
        id="eval_worker",
        name="Job Evaluator",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        f"[Scheduler] Started. "
        f"ScrapeWorker every {settings.SCRAPE_INTERVAL_HOURS}h, "
        f"EvalWorker every {settings.EVAL_INTERVAL_HOURS}h."
    )


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
