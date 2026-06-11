"""
Database module for storing agent evaluation results.

Uses Supabase (PostgreSQL) as the backend.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any

from backend.settings import settings

logger = logging.getLogger(__name__)


def _execute_safe(query_builder):
    """Execute a Supabase query with retry logic for connection drops."""
    import time
    from httpx import RemoteProtocolError

    max_retries = 3
    for attempt in range(max_retries):
        try:
            return query_builder.execute()
        except (RemoteProtocolError, Exception) as e:
            is_disconnect = "disconnected" in str(e).lower() or isinstance(e, RemoteProtocolError)

            if is_disconnect and attempt < max_retries - 1:
                wait_time = 0.5 * (2 ** attempt)
                logger.warning(f"Supabase connection dropped. Retrying in {wait_time}s... ({attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                continue
            raise e


def _get_supabase():
    """Get Supabase client (lazy import to avoid circular deps)."""
    from agents.supabase_client import get_supabase_client
    return get_supabase_client()


def _ensure_job_exists(job_id: str, company_name: str = "", title: str = "", job_url: str = ""):
    """Ensure a job record exists in the jobs table (for foreign key)."""
    client = _get_supabase()

    # Check if job exists
    result = client.table("jobs").select("id").eq("id", job_id).execute()

    if not result.data:
        # Insert minimal job record
        client.table("jobs").insert({
            "id": job_id,
            "company_name": company_name,
            "title": title,
            "job_url": job_url,
        }).execute()


def init_database():
    """Validate Supabase connection on startup."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set. "
            "SQLite fallback has been removed."
        )
    logger.info("Using Supabase backend")


# ============================================
# EVALUATION FUNCTIONS
# ============================================

def is_job_evaluated(job_id: str) -> bool:
    """Check if a job has already been evaluated."""
    client = _get_supabase()
    result = client.table("job_evaluations").select("job_id").eq("job_id", job_id).execute()
    return len(result.data) > 0


def get_evaluation(job_id: str) -> dict | None:
    """Get evaluation for a job."""
    client = _get_supabase()
    result = client.table("job_evaluations").select("*").eq("job_id", job_id).execute()
    if result.data:
        return result.data[0]
    return None


def list_evaluations(skip: int = 0, limit: int = 20, action: str | None = None, verdict: str | None = None, search: str | None = None) -> tuple[list[dict], int]:
    """List evaluations with pagination and filtering."""
    client = _get_supabase()

    query = client.table("job_evaluations").select("*, jobs(company_website)", count="exact")

    if action:
        query = query.eq("recommended_action", action)
    if verdict:
        query = query.eq("verdict", verdict)
    if search:
        query = query.or_(f"company_name.ilike.%{search}%,title_role.ilike.%{search}%")

    # Supabase range is inclusive
    result = query.order("evaluated_at", desc=True).range(skip, skip + limit - 1).execute()

    data = result.data or []
    # Flatten jobs.company_website -> company_website
    for row in data:
        if "jobs" in row and row["jobs"]:
            if isinstance(row["jobs"], dict):
                row["company_website"] = row["jobs"].get("company_website")
            elif isinstance(row["jobs"], list) and len(row["jobs"]) > 0:
                row["company_website"] = row["jobs"][0].get("company_website")
            del row["jobs"]

    return data, result.count or 0


def get_evaluation_statistics() -> dict:
    """Get evaluation statistics."""
    client = _get_supabase()

    try:
        # Total count (efficient HEAD request)
        total_res = _execute_safe(client.table("job_evaluations").select("*", count="exact", head=True))
        total = total_res.count or 0

        # Fetch all needed data in ONE query to minimize round-trips
        res = _execute_safe(client.table("job_evaluations").select("job_match_score, recommended_action, verdict"))
        data = res.data or []

        # Average Score
        score_list = [r["job_match_score"] for r in data if r["job_match_score"] is not None]
        avg_score = sum(score_list) / len(score_list) if score_list else 0

        # Group by Action
        by_action = {}
        for r in data:
            act = r.get("recommended_action") or "unknown"
            by_action[act] = by_action.get(act, 0) + 1

        # Group by Verdict
        by_verdict = {}
        for r in data:
            v = r.get("verdict") or "unknown"
            by_verdict[v] = by_verdict.get(v, 0) + 1

    except Exception as e:
        logger.error(f"Failed to fetch stats from Supabase: {e}", exc_info=True)
        return {
            "total_evaluated": 0,
            "average_score": 0,
            "by_action": {},
            "by_verdict": {},
        }

    return {
        "total_evaluated": total,
        "average_score": round(avg_score, 1),
        "by_action": by_action,
        "by_verdict": by_verdict,
    }


def save_evaluation(result: dict):
    """Save job evaluation to database."""
    job_id = str(result.get("job_id", ""))
    company_name = result.get("company_name", "")
    title_role = result.get("title_role", "")
    job_url = result.get("job_url", "")

    client = _get_supabase()

    # Ensure job exists for FK
    _ensure_job_exists(job_id, company_name, title_role, job_url)

    data = {
        "job_id": job_id,
        "company_name": company_name,
        "title_role": title_role,
        "job_url": job_url,
        "verdict": result.get("Verdict", result.get("verdict", "")),
        "job_match_score": result.get("job_match_score", 0),
        "summary": result.get("summary", ""),
        "required_exp": result.get("required_exp", ""),
        "recommended_action": result.get("recommended_action", ""),
        "gaps": result.get("gaps", {}),
        "improvement_suggestions": result.get("improvement_suggestions", {}),
        "interview_tips": result.get("interview_tips", {}),
        "jd_keywords": result.get("jd_keywords", []),
        "matched_keywords": result.get("matched_keywords", []),
        "missing_keywords": result.get("missing_keywords", []),
        "model_used": result.get("_model_used", ""),
        "raw_response": result,
        "evaluated_at": datetime.now().isoformat(),
        "recruiter_email": result.get("recruiter_email") if result.get("recruiter_email") not in (None, "", "Unknown") else None,
        "wit_line": result.get("wit_line") or None,
    }

    # Upsert (insert or update on conflict)
    client.table("job_evaluations").upsert(
        data,
        on_conflict="job_id"
    ).execute()


# ============================================
# JD PARSED FUNCTIONS
# ============================================

def is_job_parsed(job_id: str) -> bool:
    """Check if a job's JD has been parsed."""
    client = _get_supabase()
    result = client.table("jd_parsed").select("job_id").eq("job_id", job_id).execute()
    return len(result.data) > 0


def save_jd_parsed(result: dict):
    """Save JD parsed signals to database."""
    job_id = str(result.get("job_id", ""))

    client = _get_supabase()

    # Ensure job exists for FK
    _ensure_job_exists(job_id)

    data = {
        "job_id": job_id,
        "must_haves": result.get("must_haves", []),
        "nice_to_haves": result.get("nice_to_haves", []),
        "domain": result.get("domain", ""),
        "seniority": result.get("seniority") if result.get("seniority") in ('junior', 'mid', 'senior', 'lead', 'unspecified') else None,
        "location_constraints": result.get("location_constraints", []),
        "ats_keywords": result.get("ats_keywords", []),
        "normalized_skills": result.get("normalized_skills", {}),
        "model_used": result.get("_model_used", ""),
        "raw_response": result,
        "parsed_at": datetime.now().isoformat(),
    }

    # Upsert
    client.table("jd_parsed").upsert(
        data,
        on_conflict="job_id"
    ).execute()


# ============================================
# TASK FUNCTIONS
# ============================================

def list_tasks(limit: int = 20) -> list[dict]:
    """List recent tasks."""
    client = _get_supabase()
    result = client.table("tasks").select("*").order("created_at", desc=True).limit(limit).execute()
    return result.data


def save_task_status(task_id: str, status: str, progress: dict | None = None, error: str | None = None):
    """Save or update task status."""
    client = _get_supabase()

    # Check if task exists
    result = client.table("tasks").select("task_id").eq("task_id", task_id).execute()

    data = {
        "task_id": task_id,
        "status": status,
        "progress": progress or {},
        "error": error,
    }

    if status in ("completed", "failed"):
        data["completed_at"] = datetime.now().isoformat()

    if result.data:
        # Update
        client.table("tasks").update(data).eq("task_id", task_id).execute()
    else:
        # Insert
        client.table("tasks").insert(data).execute()


def get_task_status(task_id: str) -> dict | None:
    """Get task status by ID."""
    client = _get_supabase()
    result = client.table("tasks").select("*").eq("task_id", task_id).execute()
    if result.data:
        return result.data[0]
    return None


# ============================================
# RESUME FUNCTIONS
# ============================================

def save_resume(content: dict, name: str = "Master Resume", is_master: bool = False, status: str = None, job_id: str = None, version: int = None, gdoc_url: str = None) -> str:
    """Save parsed resume to database (United Resumes Table).

    Args:
        is_master: Legacy flag, if True implies status='master' and job_id=None.
        status: 'master', 'pending', 'approved', 'rejected'.
        job_id: ID of job if tailored.
    """
    import uuid
    record_id = str(uuid.uuid4())

    # Normalize inputs
    if is_master:
        status = 'master'
        job_id = None
        version = None
    elif status is None:
        status = 'pending'

    client = _get_supabase()

    data = {
        "id": record_id,
        "name": name,
        "content": content,
        "status": status,
        "job_id": job_id,
        "version": version,
        "updated_at": datetime.now().isoformat(),
    }
    if gdoc_url is not None:
        data["gdoc_url"] = gdoc_url

    client.table("resumes").insert(data).execute()
    return record_id


def get_master_resume() -> dict | None:
    """Get the latest master resume."""
    client = _get_supabase()
    try:
        result = client.table("resumes").select("content, updated_at, gdoc_url").eq("status", "master").order("created_at", desc=True).limit(1).execute()
        if result.data:
            row = result.data[0]
            return {"content": row["content"], "updated_at": row.get("updated_at"), "gdoc_url": row.get("gdoc_url")}
    except Exception:
        pass

    return None


# ============================================
# TAILORED RESUME FUNCTIONS
# ============================================

def save_tailored_resume(*args, **kwargs):
    """REMOVED in Phase 1 Cluster A (ADR-0022).

    The old INSERT-at-end model has been replaced by:
      create_processing_placeholder(job_id) -> resume_id      (at worker entry)
      complete_tailored_resume(resume_id, ...)                (at node_save)
      mark_resume_cancelled(resume_id)                        (cancel/reaper)

    This shim raises NotImplementedError so any straggling call site is
    caught at runtime instead of silently double-INSERTing a tailored row.
    """
    raise NotImplementedError(
        "save_tailored_resume was split into create_processing_placeholder + "
        "complete_tailored_resume in Phase 1 Cluster A (ADR-0022). "
        "Call sites must thread target_resume_id through TailoringState."
    )


def create_processing_placeholder(job_id: str) -> str:
    """INSERT a placeholder resumes row at tailoring worker entry.

    The row is created with tailoring_status='processing',
    processing_started_at=now(), and an empty content={} which
    complete_tailored_resume() fills in at end-of-pipeline.

    Returns:
        resume_id (UUID string) of the newly-created placeholder row.
    """
    import uuid
    record_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    client = _get_supabase()
    client.table("resumes").insert({
        "id": record_id,
        "name": "Tailored Resume (in progress)",
        "content": {},
        "status": "pending",
        "job_id": job_id,
        "tailoring_status": "processing",
        "processing_started_at": now_iso,
        "updated_at": now_iso,
    }).execute()
    return record_id


def complete_tailored_resume(
    resume_id: str,
    version: int,
    content: dict,
    status: str = "pending",
    edit_plan: dict | None = None,
) -> bool:
    """CAS UPDATE a placeholder resumes row to its final tailored content.

    Predicate: WHERE id = resume_id AND tailoring_status = 'processing'.
    On zero rows updated, returns False and does NOT insert resume_changes
    (avoids orphans against a row already cancelled by the reaper or user).

    Returns:
        True if the UPDATE applied; False on CAS no-op.
    """
    tailoring_status_map = {
        "pending": "ready",
        "needs_review": "needs_review",
        "approved": "ready",
        "rejected": "ready",
    }

    update = {
        "name": f"Tailored Resume V{version}",
        "content": content,
        "status": status,
        "version": version,
        "tailoring_status": tailoring_status_map.get(status, "ready"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if edit_plan is not None:
        update["edit_plan"] = edit_plan

    client = _get_supabase()
    result = (
        client.table("resumes")
        .update(update)
        .eq("id", resume_id)
        .eq("tailoring_status", "processing")
        .execute()
    )
    if not result.data:
        logger.warning(
            "complete_tailored_resume.no_op",
            extra={"resume_id": resume_id, "reason": "row not in processing state"},
        )
        return False

    if edit_plan:
        job_id = result.data[0].get("job_id")
        _save_resume_changes(resume_id, job_id, edit_plan)
    return True


def mark_resume_cancelled(resume_id: str) -> bool:
    """CAS UPDATE: transition a processing resumes row to cancelled.

    Idempotent — concurrent callers (worker `finally`, cancel endpoint,
    reaper) safely no-op once one wins.

    Returns:
        True if THIS call won the CAS; False if the row was already
        terminal (cancelled / ready / needs_review).
    """
    client = _get_supabase()
    result = (
        client.table("resumes")
        .update({
            "tailoring_status": "cancelled",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", resume_id)
        .eq("tailoring_status", "processing")
        .execute()
    )
    return bool(result.data)


def _save_resume_changes(resume_id: str, job_id: str, edit_plan: dict) -> None:
    """Write per-change rows to resume_changes table from edit_plan edits.

    original_text is captured from current_text in the plan (immutable pre-AI text).
    tailored_text is populated after the tailor agent runs — stored in target_text.
    accepted_text starts NULL (user has not reviewed yet).
    """
    edits = edit_plan.get("edits", [])
    if not edits:
        return

    client = _get_supabase()
    rows = []
    for edit in edits:
        action_type = edit.get("action", "rephrase")
        if action_type not in ("rephrase", "add", "remove"):
            action_type = "rephrase"

        rows.append({
            "resume_id": resume_id,
            "job_id": job_id,
            "location": edit.get("location", ""),
            "action_type": action_type,
            "original_text": edit.get("current_text"),   # immutable — captured before AI edits
            "tailored_text": edit.get("target_text"),     # AI output
            "accepted_text": None,                        # user has not reviewed yet
            "review_action": None,
            "reason": edit.get("reason"),
            "confidence": edit.get("confidence"),
            "approved_source": edit.get("approved_source"),
        })

    if rows:
        try:
            client.table("resume_changes").insert(rows).execute()
            logger.info(f"Saved {len(rows)} resume_changes for resume {resume_id}")
        except Exception as e:
            logger.warning("Failed to save resume_changes for resume %s: %s", resume_id, e, exc_info=True)


def get_tailored_resume(record_id: str) -> dict | None:
    """Get a single tailored resume by its record ID (primary key)."""
    client = _get_supabase()
    result = client.table("resumes").select("*").eq("id", record_id).single().execute()
    return result.data


def get_tailored_resumes(job_id: str) -> list[dict]:
    """Get all tailored versions for a job."""
    client = _get_supabase()
    result = client.table("resumes").select("*").eq("job_id", job_id).order("version", desc=True).execute()
    return result.data


def update_tailored_resume_status(record_id: str, status: str):
    """Update status (approved/rejected)."""
    client = _get_supabase()
    client.table("resumes").update({"status": status}).eq("id", record_id).execute()


def update_gdoc_url(resume_id: str, gdoc_url: str) -> None:
    """Save the Google Docs export URL to a tailored resume."""
    client = _get_supabase()
    client.table("resumes").update({"gdoc_url": gdoc_url}).eq("id", resume_id).execute()


def update_cover_letter(resume_id: str, cover_letter: str) -> None:
    """Save user-edited cover letter to a tailored resume (ADR-0011)."""
    client = _get_supabase()
    client.table("resumes").update({"cover_letter": cover_letter}).eq("id", resume_id).execute()


def update_tailoring_status(resume_id: str, tailoring_status: str) -> None:
    """Update the tailoring pipeline status on a resume row."""
    client = _get_supabase()
    client.table("resumes").update({"tailoring_status": tailoring_status}).eq("id", resume_id).execute()


# ============================================
# RESUME CHANGES FUNCTIONS (ADR-0010)
# ============================================

def get_resume_changes(resume_id: str) -> list[dict]:
    """Get all change records for a tailored resume, ordered by confidence asc (worst first)."""
    client = _get_supabase()
    result = (
        client.table("resume_changes")
        .select("*")
        .eq("resume_id", resume_id)
        .order("confidence", desc=False, nullsfirst=False)
        .execute()
    )
    return result.data or []


def apply_change_action(change_id: str, action: str) -> None:
    """Apply Accept / Reject / Keep original to a single change (ADR-0010).

    'keep_original': sets accepted_text = original_text immediately, no regen loop.
    'accept': sets accepted_text = tailored_text.
    'reject': clears accepted_text (triggers UI regeneration flow if implemented).
    """
    client = _get_supabase()
    row = client.table("resume_changes").select("original_text, tailored_text").eq("id", change_id).execute()
    if not row.data:
        return

    change = row.data[0]
    if action == "accept":
        accepted_text = change.get("tailored_text")
    elif action == "keep_original":
        accepted_text = change.get("original_text")
    else:  # reject
        accepted_text = None

    client.table("resume_changes").update({
        "review_action": action,
        "accepted_text": accepted_text,
    }).eq("id", change_id).execute()


def apply_bulk_change_action(resume_id: str, action: str, scope: str = "remaining") -> int:
    """Apply an action to multiple changes at once.

    scope='remaining': only changes where review_action IS NULL.
    scope='all': all changes for the resume.
    Returns count of rows updated.
    """
    client = _get_supabase()

    # Build query to fetch target changes
    query = client.table("resume_changes").select("id, original_text, tailored_text").eq("resume_id", resume_id)
    if scope == "remaining":
        query = query.is_("review_action", "null")

    result = query.execute()
    rows = result.data or []

    for row in rows:
        if action == "accept":
            accepted_text = row.get("tailored_text")
        elif action == "keep_original":
            accepted_text = row.get("original_text")
        else:
            accepted_text = None

        client.table("resume_changes").update({
            "review_action": action,
            "accepted_text": accepted_text,
        }).eq("id", row["id"]).execute()

    return len(rows)


# ============================================
# SYSTEM CONFIG FUNCTIONS
# ============================================

def get_system_config(key: str) -> str | None:
    """Get a system config value by key."""
    client = _get_supabase()
    result = client.table("system_config").select("value").eq("key", key).execute()
    if result.data:
        return result.data[0]["value"]
    return None


def set_system_config(key: str, value: str) -> None:
    """Upsert a system config value."""
    client = _get_supabase()
    client.table("system_config").upsert({"key": key, "value": value}, on_conflict="key").execute()


def get_jd_parsed(job_id: str) -> dict | None:
    """Get parsed signals for a job."""
    client = _get_supabase()
    result = client.table("jd_parsed").select("*").eq("job_id", job_id).execute()
    if result.data:
        return result.data[0]
    return None


# ─────────────────────────────────────────────────────────────────
# OotoCV adaptation — runs feed, pipeline config, ghost commentary
# (Migrations 021–025, ADRs 0023–0025)
# ─────────────────────────────────────────────────────────────────


def list_runs(limit: int = 50) -> list[dict]:
    """Return recent pipeline runs with per-verdict aggregated counts.

    Backed by the `runs_with_counts(limit_n)` SQL function defined in
    migration `021b_runs_with_counts_rpc.sql`. Each row carries:
      id, started_at, finished_at, status, jobs_found,
      tailor_count, borderline_count, apply_direct_count, skip_count.

    If the RPC is not installed (e.g. partial migration apply), returns []
    and logs a warning rather than raising — the caller (GET /api/runs) can
    still respond 200 with an empty list while the operator applies 021b.
    """
    try:
        client = _get_supabase()
        resp = client.rpc("runs_with_counts", {"limit_n": limit}).execute()
        return resp.data or []
    except Exception:  # noqa: BLE001 — RPC missing or DB down
        logger.warning("list_runs failed", exc_info=True)
        return []


def get_run(run_id: str) -> dict | None:
    """Return a single pipeline_runs row, or None."""
    try:
        client = _get_supabase()
        resp = (
            client.table("pipeline_runs")
            .select("*")
            .eq("id", run_id)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        return rows[0] if rows else None
    except Exception:  # noqa: BLE001
        logger.warning("get_run failed", exc_info=True, extra={"run_id": run_id})
        return None


_PIPELINE_MODE_KEYS: dict[str, str] = {
    "scrape_mode":   "pipeline_scrape_mode",
    "evaluate_mode": "pipeline_evaluate_mode",
    "tailor_mode":   "pipeline_tailor_mode",
}
_VALID_MODES: frozenset[str] = frozenset({"auto", "manual"})


def get_pipeline_config() -> dict:
    """Return current pipeline modes + auto_send_threshold as a flat dict.

    Defaults match migration 025 seeds (auto/auto/manual, threshold 0) so
    a fresh install without the seed still gets sane behaviour.
    """
    client = _get_supabase()
    keys = list(_PIPELINE_MODE_KEYS.values()) + ["auto_send_threshold"]
    resp = (
        client.table("system_config")
        .select("key,value")
        .in_("key", keys)
        .execute()
    )
    rows = {r["key"]: r["value"] for r in (resp.data or [])}
    return {
        "scrape_mode":         rows.get("pipeline_scrape_mode",   "auto"),
        "evaluate_mode":       rows.get("pipeline_evaluate_mode", "auto"),
        "tailor_mode":         rows.get("pipeline_tailor_mode",   "manual"),
        "auto_send_threshold": int(rows.get("auto_send_threshold", "0")),
    }


def set_pipeline_config(updates: dict) -> dict:
    """Validate + upsert pipeline config rows. Returns the new full config.

    Accepts any subset of {scrape_mode, evaluate_mode, tailor_mode,
    auto_send_threshold}. Reuses set_system_config() so we don't duplicate
    the upsert primitive.
    """
    for short_key, value in updates.items():
        if short_key == "auto_send_threshold":
            ival = int(value)
            if not 0 <= ival <= 4:
                raise ValueError("auto_send_threshold must be 0..4")
            set_system_config("auto_send_threshold", str(ival))
            continue
        if short_key not in _PIPELINE_MODE_KEYS:
            raise ValueError(f"Unknown pipeline config key: {short_key}")
        if value not in _VALID_MODES:
            raise ValueError(
                f"Invalid mode '{value}' for {short_key}; "
                f"must be one of {sorted(_VALID_MODES)}"
            )
        set_system_config(_PIPELINE_MODE_KEYS[short_key], value)
    return get_pipeline_config()


def compute_ghost_commentary(days_since_update: int) -> str:
    """OotoCV-voice ghosting commentary, bracketed by days_since_update.

    Recompute on every read — never store. The agent's "awareness" depends
    on commentary aging with the row (Cache-Control: no-store on the
    response, R5 mitigation).
    """
    if days_since_update <= 3:
        return "Probably just busy."
    if days_since_update <= 7:
        return "Still nothing. Rude, but fine."
    if days_since_update <= 14:
        return "At this point we're assuming they lost it."
    return "They don't deserve you."


class RegenerationCapReached(Exception):
    """Raised when a rejected change has already hit the regeneration cap."""


REGENERATION_CAP = 2


def record_change_feedback(change_id: str, feedback_type: str) -> dict:
    """Mark a change as rejected with a feedback chip and bump regeneration_count.

    Returns the updated row. Raises RegenerationCapReached if the count is
    already at REGENERATION_CAP — the route layer maps that to HTTP 409 and
    the UI falls back to "edit manually" (R8 mitigation).

    The actual regeneration LLM call is wired by the route layer; this
    helper only stamps the audit fields and increments the counter.
    """
    if feedback_type not in ("too_formal", "not_accurate", "other"):
        raise ValueError(f"invalid feedback_type: {feedback_type}")

    client = _get_supabase()
    current = (
        client.table("resume_changes")
        .select("regeneration_count")
        .eq("id", change_id)
        .limit(1)
        .execute()
    )
    rows = current.data or []
    prev_count = (rows[0].get("regeneration_count") if rows else 0) or 0
    if prev_count >= REGENERATION_CAP:
        raise RegenerationCapReached(
            f"regeneration_count >= {REGENERATION_CAP} for change {change_id}"
        )

    resp = (
        client.table("resume_changes")
        .update({
            "review_action":      "reject",
            "feedback_type":      feedback_type,
            "regenerated_at":     datetime.now(timezone.utc).isoformat(),
            "regeneration_count": prev_count + 1,
        })
        .eq("id", change_id)
        .execute()
    )
    updated = (resp.data or [{}])[0]
    return updated
