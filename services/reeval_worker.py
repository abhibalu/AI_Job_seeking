"""
Re-evaluation Worker — runs the full pipeline as a background task with per-stage SSE progress.

Approach A: manually steps through pipeline nodes, emitting save_task_status() at each boundary.
Supports cancellation via is_cancelled() check before each stage.

Stage map:
  0: evaluating  — node_evaluate(state)           [all paths]
  1: routing     — route_after_evaluation(state)   [all paths; sets total + evaluation_snapshot]
  2: parsing     — node_parse(state)               [tailor only]
  3: planning    — subgraph node_plan(state)        [tailor only]
  4: drafting    — subgraph node_draft(state)       [tailor only]
  5: critiquing  — subgraph node_critique(state)    [tailor only]
  6: saving      — subgraph node_save(state) + node_notify_tailored(state)  [tailor only]

Skip path:  stages 0-1, then run_complete (total=2)
Apply path: stages 0-1 + node_notify_apply, then run_complete (total=2)
Tailor path: all 7 stages (total=7)
"""
import logging
from pathlib import Path

from agents.database import (
    save_task_status,
    get_task_status,
    save_evaluation,
    get_master_resume,
)
from agents.pipeline_graph import (
    node_evaluate,
    node_parse,
    node_notify_apply,
    node_notify_tailored,
    route_after_evaluation,
)
from agents.tailoring_subgraph import (
    node_plan,
    node_draft,
    node_validate,
    node_critique,
    node_save,
    route_validate,
    route_critique,
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
    """Background worker that re-evaluates a job through the full pipeline with per-stage progress."""
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
        "tailored_resume_id": "",
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
                save_evaluation(state["evaluation"])
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

        # --- Tailor path: update total to 7 ---
        progress = {
            "completed": 1, "total": 7, "stage": "routing",
            "path": "tailor", "evaluation_snapshot": evaluation_snapshot,
        }
        save_task_status(task_id, "running", progress)

        if check_cancelled(progress):
            return

        # --- Stage 2: Parsing ---
        progress = {
            "completed": 2, "total": 7, "stage": "parsing",
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

        # --- Build tailoring subgraph state ---
        parsed_jd = state.get("parsed_jd", {})
        jd_context = {
            "role": job_details.get("title", "Unknown"),
            "company": job_details.get("company_name", "Unknown"),
            "summary": state["evaluation"].get("summary", ""),
            "must_haves": parsed_jd.get("must_haves", []),
            "ats_keywords": parsed_jd.get("ats_keywords", []),
            "strategic_gaps": state["evaluation"].get("gaps", {}),
            "improvement_suggestions": state["evaluation"].get("improvement_suggestions", []),
        }

        base_resume = get_master_resume()
        if not base_resume:
            save_task_status(task_id, "failed", progress, error="No master resume found in DB")
            return

        approved_skills = ""
        skills_path = Path("agent_prompts/approved_skills.md")
        if skills_path.exists():
            with open(skills_path) as f:
                approved_skills = f.read()

        sub_state: dict = {
            "job_id": job_id,
            "base_resume": base_resume,
            "jd_context": jd_context,
            "approved_skills": approved_skills,
            "edit_plan": {},
            "draft_resume": {},
            "critique": [],
            "revision_count": 0,
            "final_resume_id": "",
            "status": "queued",
            "errors": [],
        }

        # --- Stage 3: Planning ---
        progress = {
            "completed": 3, "total": 7, "stage": "planning",
            "path": "tailor", "evaluation_snapshot": evaluation_snapshot,
        }
        save_task_status(task_id, "running", progress)
        if check_cancelled(progress):
            return

        result = node_plan(sub_state)
        sub_state.update(result)
        if sub_state.get("errors"):
            save_task_status(task_id, "failed", progress, error="; ".join(sub_state["errors"]))
            return

        # --- Stage 4: Drafting + Validation (may loop) ---
        progress = {
            "completed": 4, "total": 7, "stage": "drafting",
            "path": "tailor", "evaluation_snapshot": evaluation_snapshot,
        }
        save_task_status(task_id, "running", progress)
        if check_cancelled(progress):
            return

        result = node_draft(sub_state)
        sub_state.update(result)
        if sub_state.get("errors"):
            save_task_status(task_id, "failed", progress, error="; ".join(sub_state["errors"]))
            return

        result = node_validate(sub_state)
        sub_state.update(result)

        route_v = route_validate(sub_state)
        while route_v == "revise":
            if check_cancelled(progress):
                return
            result = node_draft(sub_state)
            sub_state.update(result)
            if sub_state.get("errors"):
                save_task_status(task_id, "failed", progress, error="; ".join(sub_state["errors"]))
                return
            result = node_validate(sub_state)
            sub_state.update(result)
            route_v = route_validate(sub_state)

        if route_v == "error":
            save_task_status(
                task_id, "failed", progress,
                error="; ".join(sub_state.get("errors", ["Validation error"])),
            )
            return

        # --- Stage 5: Critiquing (may loop back to draft) ---
        progress = {
            "completed": 5, "total": 7, "stage": "critiquing",
            "path": "tailor", "evaluation_snapshot": evaluation_snapshot,
        }
        save_task_status(task_id, "running", progress)
        if check_cancelled(progress):
            return

        result = node_critique(sub_state)
        sub_state.update(result)
        if sub_state.get("errors"):
            save_task_status(task_id, "failed", progress, error="; ".join(sub_state["errors"]))
            return

        route_c = route_critique(sub_state)
        while route_c == "revise":
            if check_cancelled(progress):
                return
            result = node_draft(sub_state)
            sub_state.update(result)
            if sub_state.get("errors"):
                save_task_status(task_id, "failed", progress, error="; ".join(sub_state["errors"]))
                return
            result = node_validate(sub_state)
            sub_state.update(result)
            result = node_critique(sub_state)
            sub_state.update(result)
            if sub_state.get("errors"):
                save_task_status(task_id, "failed", progress, error="; ".join(sub_state["errors"]))
                return
            route_c = route_critique(sub_state)

        if route_c == "error":
            save_task_status(
                task_id, "failed", progress,
                error="; ".join(sub_state.get("errors", ["Critique error"])),
            )
            return

        # --- Stage 6: Saving + Notify ---
        progress = {
            "completed": 6, "total": 7, "stage": "saving",
            "path": "tailor", "evaluation_snapshot": evaluation_snapshot,
        }
        save_task_status(task_id, "running", progress)
        if check_cancelled(progress):
            return

        result = node_save(sub_state)
        sub_state.update(result)
        if sub_state.get("errors"):
            save_task_status(task_id, "failed", progress, error="; ".join(sub_state["errors"]))
            return

        record_id = sub_state.get("final_resume_id", "")

        # Update parent pipeline state for notification
        state["tailored_resume_id"] = record_id
        node_notify_tailored(state)

        save_task_status(task_id, "completed", {
            "completed": 7, "total": 7, "stage": "done",
            "path": "tailor", "evaluation_snapshot": evaluation_snapshot,
            "resume_id": record_id,
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
