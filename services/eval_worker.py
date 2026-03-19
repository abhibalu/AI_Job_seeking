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

from backend.settings import settings
from agents.database import save_evaluation
from agents.supabase_client import get_supabase_client
from agents.pipeline_graph import build_pipeline_graph
from agents.supabase_checkpointer import SupabaseSaver
from services.pipeline_runs import start_run, finish_run
from services.telegram_notifier import notify_eval_complete, notify_pipeline_error
from backend.log_context import set_correlation_id, new_request_id

logger = logging.getLogger(__name__)

MAX_JOBS_PER_RUN = int(getattr(settings, "EVAL_MAX_JOBS_PER_RUN", 50))
DELAY_BETWEEN_CALLS = float(getattr(settings, "EVAL_DELAY_SECONDS", 1.0))


def _get_unevaluated_jobs(limit: int) -> list[dict]:
    """Fetch active jobs from Supabase that haven't been evaluated yet."""
    try:
        client = get_supabase_client()

        # Single query via enriched view — no double round-trip or client-side filtering
        result = (
            client.table("v_jobs_enriched")
            .select("id, title, company_name, description_text, job_url")
            .eq("status", "active")
            .eq("is_evaluated", False)
            .not_.is_("description_text", "null")
            .order("posted_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    except Exception as e:
        logger.error(f"[EvalWorker] Failed to fetch unevaluated jobs: {e}", exc_info=True)
        return []


def _process_single_job_graph(graph, job: dict) -> tuple[str, str | None]:
    """
    Process one job through the LangGraph state machine.
    Returns (action, error_message) where action is 'apply', 'tailor', 'skip', or 'error'.
    """
    job_id = job["id"]
    try:
        # Initialize state
        initial_state = {
            "job_id": job_id,
            "job_details": {
                "title": job.get("title"),
                "company_name": job.get("company_name"),
                "description_text": job.get("description_text"),
                "job_url": job.get("job_url"),
            },
        }
        
        # We use the job_id as the thread_id so SupabaseSaver can resume if needed
        config = {"configurable": {"thread_id": job_id}}
        
        final_state = graph.invoke(initial_state, config=config)
        
        # ALWAYS save the evaluation to the job_evaluations table for dashboard compatibility,
        # even if later nodes (parse/tailor) failed. The evaluation itself succeeded.
        if final_state.get("evaluation"):
            try:
                save_evaluation(final_state["evaluation"])
            except Exception as e:
                logger.warning(f"[GraphWorker] Failed to save evaluation to DB for {job_id}: {e}")

        # If there were errors in the graph execution (e.g., parse or tailor failed)
        if final_state.get("errors"):
            logger.warning(f"[GraphWorker] Graph completed with errors for {job_id}: {final_state['errors']}")
            # Still return the action from the evaluation, not 'error',
            # because the evaluation DID succeed and was saved.
            eval_dict = final_state.get("evaluation") or {}
            action = eval_dict.get("recommended_action", "skip").lower()
            return action, None

        # Determine the action taken based on the evaluation
        eval_dict = final_state.get("evaluation") or {}
        action = eval_dict.get("recommended_action", "skip").lower()
        return action, None

    except Exception as e:
        logger.error(f"[GraphWorker] Error orchestrating job {job_id}: {e}", exc_info=True)
        return "error", str(e)


def run_eval_worker() -> None:
    """
    Main entry point called by APScheduler after each scrape cycle.
    Processes up to MAX_JOBS_PER_RUN unevaluated jobs through LangGraph.
    """
    logger.info(f"[GraphWorker] Starting LangGraph batch (max={MAX_JOBS_PER_RUN})")

    run_id = start_run("evaluate", metadata={"max_jobs": MAX_JOBS_PER_RUN, "orchestration": "langgraph"})
    set_correlation_id(f"run:{run_id[:8]}" if run_id else f"run:{new_request_id()}")

    try:
        jobs = _get_unevaluated_jobs(MAX_JOBS_PER_RUN)
        if not jobs:
            logger.info("[GraphWorker] No unevaluated jobs found. Nothing to do.")
            finish_run(run_id, status="skipped", jobs_found=0, jobs_processed=0)
            return

        logger.info(f"[GraphWorker] Found {len(jobs)} unevaluated jobs.")
        
        # Build graph and checkpointer
        supabase_client = get_supabase_client()
        checkpointer = SupabaseSaver(supabase_client)
        graph = build_pipeline_graph().compile(checkpointer=checkpointer)

        counters = {"apply": 0, "tailor": 0, "skip": 0, "error": 0}
        processed = 0

        for job in jobs:
            action, error = _process_single_job_graph(graph, job)
            if action not in counters:
                action = "skip" # normalize unexpected strings
            counters[action] += 1
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

        logger.info(f"[GraphWorker] Batch complete. {processed} processed. Results: {counters}")

    except Exception as e:
        logger.error(f"[GraphWorker] Unhandled error: {e}", exc_info=True)
        finish_run(run_id, status="failed", error_detail=str(e))
        notify_pipeline_error("GraphWorker", str(e))
    finally:
        set_correlation_id(None)
