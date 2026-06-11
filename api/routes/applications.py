"""Applications routes — OotoCV application tracker."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from agents.database import compute_ghost_commentary
from agents.supabase_client import get_supabase_client

router = APIRouter()

# 'offer' added 2026-06-11 (migration 023, ADR-0023-adjacent).
VALID_STATUSES = (
    'applied', 'replied', 'interview', 'rejected', 'ghosting', 'offer',
)


class ApplicationCreate(BaseModel):
    job_id: str
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    resume_id: Optional[str] = None
    cv_version: str = 'base'  # 'base' | 'tailored'


class ApplicationStatusUpdate(BaseModel):
    status: str  # one of VALID_STATUSES


def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp; tolerate trailing Z and naive input.

    Returns None if `ts` is falsy or unparseable. Naive datetimes are coerced
    to UTC so subsequent (aware - aware) subtraction works.
    """
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _enrich_application(row: dict) -> dict:
    """Add `days_since_update` and `ghost_commentary` to a tracker row.

    `days_since_update` is `now - latest(status_history[].timestamp, applied_at)`
    in whole days. `ghost_commentary` is the OotoCV-voice line bracketed by
    that count. Both are computed on every read so the agent's "awareness"
    naturally ages with the row — never cache (R5; Cache-Control: no-store on
    the response). See ADR-0023-adjacent risk register and ADR-0013 for the
    status_history audit log.
    """
    history = row.get("status_history") or []
    last_ts: Optional[str] = None
    if history:
        last_ts = history[-1].get("timestamp")
    last_dt = _parse_iso(last_ts) or _parse_iso(row.get("applied_at"))
    if last_dt is None:
        days = 0
    else:
        delta = datetime.now(timezone.utc) - last_dt
        days = max(0, delta.days)
    return {
        **row,
        "days_since_update": days,
        "ghost_commentary": compute_ghost_commentary(days),
    }


@router.get("")
def list_applications(response: Response):
    """List all applications, newest first.

    Adds `ghost_commentary` and `days_since_update` per row (computed from
    `status_history`, never stored). The response is marked no-store so the
    commentary cannot go stale via shared caches.
    """
    client = get_supabase_client()
    result = (
        client.table("applications")
        .select("*")
        .order("applied_at", desc=True)
        .execute()
    )
    response.headers["Cache-Control"] = "no-store"
    return [_enrich_application(r) for r in (result.data or [])]


@router.post("", status_code=201)
def create_application(body: ApplicationCreate):
    """Record a new application (called when user clicks Apply in JobCard)."""
    if body.cv_version not in ('base', 'tailored'):
        raise HTTPException(status_code=422, detail="cv_version must be 'base' or 'tailored'")

    client = get_supabase_client()
    now = datetime.now(timezone.utc).isoformat()

    row = {
        "job_id": body.job_id,
        "job_title": body.job_title,
        "company_name": body.company_name,
        "resume_id": body.resume_id,
        "cv_version": body.cv_version,
        "status": "applied",
        "status_history": [{"status": "applied", "timestamp": now}],
    }

    result = client.table("applications").insert(row).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create application")
    return result.data[0]


@router.patch("/{application_id}/status")
def update_application_status(application_id: str, body: ApplicationStatusUpdate):
    """Update application status and append to status_history."""
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {VALID_STATUSES}")

    client = get_supabase_client()
    existing = (
        client.table("applications")
        .select("status_history")
        .eq("id", application_id)
        .single()
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Application not found")

    history = existing.data.get("status_history") or []
    now = datetime.now(timezone.utc).isoformat()
    history.append({"status": body.status, "timestamp": now})

    result = (
        client.table("applications")
        .update({"status": body.status, "status_history": history})
        .eq("id", application_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to update application")
    return result.data[0]
