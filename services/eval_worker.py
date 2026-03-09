"""
Evaluator Worker — automatically evaluates unevaluated jobs from Supabase.

Flow:
  1. Fetch all active jobs not yet in job_evaluations
  2. Run JobEvaluatorAgent on each (respecting concurrency limit)  
  3. Save evaluation + trigger JD parsing in background
  4. Send Telegram alert for high-match jobs (score >= EVAL_HIGH_MATCH_THRESHOLD)
  5. Log run to pipeline_runs
"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.settings import settings
from agents.database import is_job_evaluated, save_evaluation
from agents.job_evaluator import JobEvaluatorAgent
from agents.jd_parser import run_jd_parser_task
from agents.supabase_client import get_supabase_client
from services.pipeline_runs import start_run, finish_run
from services.telegram_notifier import notify_eval_complete, notify_high_match, notify_pipeline_error

logger = logging.getLogger(__name__)

HIGH_MATCH_THRESHOLD = int(getattr(settings, "EVAL_HIGH_MATCH_THRESHOLD", 70))
MAX_JOBS_PER_RUN = int(getattr(settings, "EVAL_MAX_JOBS_PER_RUN", 50))
DELAY_BETWEEN_CALLS = float(getattr(settings, "EVAL_DELAY_SECONDS", 1.0))


def _get_unevaluated_jobs(limit: int) -> list[dict]:
    """
    Fetch active jobs from Supabase that haven't been evaluated yet.
    Uses a LEFT JOIN approach: get all active job IDs, then exclude evaluated ones.
    """
    try:
        client = get_supabase_client()

        # Get all evaluated job IDs
        evaluated_result = client.table("job_evaluations").select("job_id").execute()
        evaluated_ids = {r["job_id"] for r in (evaluated_result.data or [])}

        # Get active jobs not in evaluated list
        query = (
            client.table("jobs")
            .select("id, title, company_name, description_text, job_url")
            .eq("status", "active")
            .not_.is_("description_text", "null")
            .order("posted_at", desc=True)
            .limit(limit * 3)  # overfetch to account for client-side filtering
        )
        result = query.execute()
        all_jobs = result.data or []

        # Filter out already evaluated
        unevaluated = [j for j in all_jobs if j["id"] not in evaluated_ids]
        return unevaluated[:limit]

    except Exception as e:
        logger.error(f"[EvalWorker] Failed to fetch unevaluated jobs: {e}", exc_info=True)
        return []


def _evaluate_single_job(agent: JobEvaluatorAgent, job: dict) -> tuple[str, str | None]:
    """
    Evaluate one job. Returns (action, error_message).
    action is one of: 'apply' | 'tailor' | 'skip' | 'error'
    """
    job_id = job["id"]
    try:
        if is_job_evaluated(job_id):
            return "skip", None

        result = agent.run(
            job_id=job_id,
            description_text=job.get("description_text", ""),
            company_name=job.get("company_name", "Unknown"),
            title=job.get("title", "Unknown"),
            job_url=job.get("job_url", "Unknown"),
        )
        save_evaluation(result)

        # Kick off JD parsing in background (fire and forget)
        try:
            run_jd_parser_task(job_id, job.get("description_text", ""))
        except Exception:
            pass  # non-critical

        score = result.get("job_match_score", 0)
        action = result.get("recommended_action", "skip")

        # Send high-match alert immediately
        if score >= HIGH_MATCH_THRESHOLD:
            notify_high_match(
                company=result.get("company_name", "Unknown"),
                title=result.get("title_role", "Unknown"),
                score=score,
                job_id=job_id,
                action=action,
            )

        return action, None

    except Exception as e:
        logger.error(f"[EvalWorker] Error evaluating job {job_id}: {e}", exc_info=True)
        return "error", str(e)


def run_eval_worker() -> None:
    """
    Main entry point called by APScheduler after each scrape cycle.
    Processes up to MAX_JOBS_PER_RUN unevaluated jobs.
    """
    logger.info(f"[EvalWorker] Starting evaluation batch (max={MAX_JOBS_PER_RUN})")

    run_id = start_run("evaluate", metadata={"max_jobs": MAX_JOBS_PER_RUN})

    try:
        jobs = _get_unevaluated_jobs(MAX_JOBS_PER_RUN)
        if not jobs:
            logger.info("[EvalWorker] No unevaluated jobs found. Nothing to do.")
            finish_run(run_id, status="skipped", jobs_found=0, jobs_processed=0)
            return

        logger.info(f"[EvalWorker] Found {len(jobs)} unevaluated jobs.")
        agent = JobEvaluatorAgent()

        counters = {"apply": 0, "tailor": 0, "skip": 0, "error": 0}
        processed = 0

        for job in jobs:
            action, error = _evaluate_single_job(agent, job)
            counters[action] = counters.get(action, 0) + 1
            processed += 1
            time.sleep(DELAY_BETWEEN_CALLS)

        finish_run(
            run_id,
            status="completed",
            jobs_found=len(jobs),
            jobs_processed=processed,
            jobs_skipped=counters.get("skip", 0),
            metadata=counters,
        )

        notify_eval_complete(
            total=processed,
            applied=counters.get("apply", 0),
            tailored=counters.get("tailor", 0),
            skipped=counters.get("skip", 0),
        )

        logger.info(f"[EvalWorker] Batch complete. {processed} processed. Results: {counters}")

    except Exception as e:
        logger.error(f"[EvalWorker] Unhandled error: {e}", exc_info=True)
        finish_run(run_id, status="failed", error_detail=str(e))
        notify_pipeline_error("EvaluationWorker", str(e))
