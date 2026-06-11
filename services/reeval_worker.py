"""
Re-evaluation Worker — runs evaluate + route as a background task with per-stage SSE progress.

Read-only re-evaluation: no tailoring is performed. The frontend uses the verdict to offer
the user a CTA (tailor, apply, skip) without silently running the full pipeline.

Stage map:
  0: evaluating  — node_evaluate(state)           [all paths]
  1: routing     — route_after_evaluation(state)   [all paths; sets total + evaluation_snapshot]
  2: parsing     — node_parse(state)               [tailor only — provides ATS keywords]

Skip path:  stages 0-1, then run_complete (total=2)
Apply path: stages 0-1 + node_notify_apply, then run_complete (total=2)
Tailor path: stages 0-2 (total=3)
"""
import logging

from agents.database import (
    save_task_status,
    get_task_status,
)
from agents.evaluator_writer import save_evaluation_with_card_lines
from agents.pipeline_graph import (
    node_evaluate,
    node_parse,
    node_notify_apply,
    route_after_evaluation,
)
from backend.log_context import set_correlation_id

logger = logging.getLogger(__name__)


def _build_evaluation_snapshot(evaluation: dict) -> dict:
    """Extract the fields the frontend needs for the verdict crossfade."""
    return {
        "recommended_action": evaluation.get("recommended_action", "skip"),
        "job_match_score": evaluation.get("job_match_score", 0),
        "wit_line": evaluation.get("wit_line") or evaluation.get("summary") or "",
        "verdict": evaluation.get("Verdict", evaluation.get("verdict", "")),
    }


def run_reeval_worker(task_id: str, job_id: str, job_details: dict):
    """Background worker that re-evaluates a job (read-only, no tailoring)."""
    set_correlation_id(f"reeval:{task_id[:8]}")

    def is_cancelled():
        task = get_task_status(task_id)
        return task and task.get("status") == "cancelled"

    def check_cancelled(progress: dict) -> bool:
        """Check cancellation and write terminal status if cancelled. Returns True if cancelled."""
        if is_cancelled():
            save_task_status(task_id, "cancelled", progress)
            return True
        return False

    # Build initial pipeline state
    state: dict = {
        "job_id": job_id,
        "job_details": job_details,
        "evaluation": {},
        "parsed_jd": {},
        "status": "queued",
        "errors": [],
    }

    try:
        # --- Stage 0: Evaluating ---
        progress = {"completed": 0, "total": 2, "stage": "evaluating"}
        save_task_status(task_id, "running", progress)
        if check_cancelled(progress):
            return

        result = node_evaluate(state)
        state.update(result)
        if state.get("errors"):
            save_task_status(
                task_id, "failed", progress,
                error="; ".join(state["errors"]),
            )
            return

        # Save evaluation to DB immediately (same as sync behavior)
        if state.get("evaluation"):
            try:
                save_evaluation_with_card_lines(state["evaluation"])
            except Exception as e:
                logger.warning("[ReEvalWorker] Failed to save evaluation to DB: %s", e, exc_info=True)

        # --- Stage 1: Routing ---
        route = route_after_evaluation(state)
        evaluation_snapshot = _build_evaluation_snapshot(state["evaluation"])

        if route == "error":
            save_task_status(
                task_id, "failed",
                {"completed": 1, "total": 2, "stage": "routing", "path": "error",
                 "evaluation_snapshot": evaluation_snapshot},
                error="; ".join(state.get("errors", ["Routing returned error"])),
            )
            return

        if route in ("skip", "apply"):
            # Short paths — total stays at 2
            progress = {
                "completed": 1, "total": 2, "stage": "routing",
                "path": route, "evaluation_snapshot": evaluation_snapshot,
            }
            save_task_status(task_id, "running", progress)

            if route == "apply":
                node_notify_apply(state)

            save_task_status(task_id, "completed", {
                "completed": 2, "total": 2, "stage": "done",
                "path": route, "evaluation_snapshot": evaluation_snapshot,
            })
            return

        # --- Tailor path: evaluate → route → parse JD → DONE (total=3) ---
        progress = {
            "completed": 1, "total": 3, "stage": "routing",
            "path": "tailor", "evaluation_snapshot": evaluation_snapshot,
        }
        save_task_status(task_id, "running", progress)

        if check_cancelled(progress):
            return

        # --- Stage 2: Parsing ---
        progress = {
            "completed": 2, "total": 3, "stage": "parsing",
            "path": "tailor", "evaluation_snapshot": evaluation_snapshot,
        }
        save_task_status(task_id, "running", progress)
        if check_cancelled(progress):
            return

        result = node_parse(state)
        state.update(result)
        if state.get("errors"):
            save_task_status(task_id, "failed", progress, error="; ".join(state["errors"]))
            return

        save_task_status(task_id, "completed", {
            "completed": 3, "total": 3, "stage": "done",
            "path": "tailor", "evaluation_snapshot": evaluation_snapshot,
        })

    except Exception as e:
        logger.exception("ReEval worker unhandled exception", extra={"task_id": task_id, "job_id": job_id})
        save_task_status(
            task_id, "failed",
            {"completed": 0, "total": 2, "stage": "error"},
            error=str(e),
        )
    finally:
        set_correlation_id(None)
