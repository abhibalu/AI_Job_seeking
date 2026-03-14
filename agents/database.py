"""
Database module for storing agent evaluation results.

Uses Supabase (PostgreSQL) as the backend.
"""
import json
import logging
from datetime import datetime
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

def save_resume(content: dict, name: str = "Master Resume", is_master: bool = False, status: str = None, job_id: str = None, version: int = None) -> str:
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

    client.table("resumes").insert(data).execute()
    return record_id


def get_master_resume() -> dict | None:
    """Get the latest master resume."""
    client = _get_supabase()
    try:
        result = client.table("resumes").select("content").eq("status", "master").order("created_at", desc=True).limit(1).execute()
        if result.data:
            return result.data[0]["content"]
    except Exception:
        pass

    return None


# ============================================
# TAILORED RESUME FUNCTIONS
# ============================================

def save_tailored_resume(job_id: str, version: int, content: dict, status: str = "pending", edit_plan: dict = None) -> str:
    """Save a tailored resume (wrapper around save_resume), optionally with edit plan."""
    record_id = save_resume(
        content=content,
        name=f"Tailored Resume V{version}",
        is_master=False,
        status=status,
        job_id=job_id,
        version=version
    )

    # Store edit plan if provided
    if edit_plan:
        try:
            client = _get_supabase()
            client.table("resumes").update({"edit_plan": edit_plan}).eq("id", record_id).execute()
        except Exception as e:
            logger.warning(f"Failed to save edit_plan for resume {record_id}: {e}")

    return record_id


def get_tailored_resumes(job_id: str) -> list[dict]:
    """Get all tailored versions for a job."""
    client = _get_supabase()
    result = client.table("resumes").select("*").eq("job_id", job_id).order("version", desc=True).execute()
    return result.data


def update_tailored_resume_status(record_id: str, status: str):
    """Update status (approved/rejected)."""
    client = _get_supabase()
    client.table("resumes").update({"status": status}).eq("id", record_id).execute()


def get_jd_parsed(job_id: str) -> dict | None:
    """Get parsed signals for a job."""
    client = _get_supabase()
    result = client.table("jd_parsed").select("*").eq("job_id", job_id).execute()
    if result.data:
        return result.data[0]
    return None
