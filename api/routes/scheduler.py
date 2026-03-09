"""
Scheduler status route — GET /api/scheduler/status

Returns:
  - scheduler running flag
  - registered APScheduler jobs with next run times
  - last 10 pipeline_runs entries (summary of recent activity)
  - last run per type (scrape / evaluate / tailor)
"""
import logging
from fastapi import APIRouter

from services.pipeline_runs import get_recent_runs, get_last_run
from services.scheduler import get_scheduler, get_job_status

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("")
def scheduler_status():
    """Return pipeline health: APScheduler jobs + recent pipeline_runs history."""
    from backend.settings import settings

    scheduler = get_scheduler()
    scheduler_running = scheduler is not None and scheduler.running

    return {
        "scheduler_enabled": settings.SCHEDULER_ENABLED,
        "scheduler_running": scheduler_running,
        "jobs": get_job_status(),
        "config": {
            "scrape_interval_hours": settings.SCRAPE_INTERVAL_HOURS,
            "eval_interval_hours": settings.EVAL_INTERVAL_HOURS,
            "eval_max_jobs_per_run": settings.EVAL_MAX_JOBS_PER_RUN,
            "high_match_threshold": settings.EVAL_HIGH_MATCH_THRESHOLD,
            "telegram_configured": bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID),
        },
        "last_runs": {
            "scrape": get_last_run("scrape"),
            "evaluate": get_last_run("evaluate"),
            "tailor": get_last_run("tailor"),
        },
        "recent_history": get_recent_runs(limit=10),
    }


@router.post("/trigger/scrape")
def trigger_scrape_now():
    """Manually trigger the scrape worker immediately (outside the schedule)."""
    import threading
    from services.scraper_worker import run_scrape_worker
    thread = threading.Thread(target=run_scrape_worker, daemon=True, name="manual_scrape")
    thread.start()
    return {"status": "triggered", "message": "Scrape worker started in background."}


@router.post("/trigger/evaluate")
def trigger_eval_now():
    """Manually trigger the evaluation worker immediately."""
    import threading
    from services.eval_worker import run_eval_worker
    thread = threading.Thread(target=run_eval_worker, daemon=True, name="manual_eval")
    thread.start()
    return {"status": "triggered", "message": "Evaluation worker started in background."}
