"""Applications routes — OotoCV application tracker."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.supabase_client import get_supabase_client

router = APIRouter()

VALID_STATUSES = ('applied', 'replied', 'interview', 'rejected', 'ghosting')


class ApplicationCreate(BaseModel):
    job_id: str
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    resume_id: Optional[str] = None
    cv_version: str = 'base'  # 'base' | 'tailored'


class ApplicationStatusUpdate(BaseModel):
    status: str  # one of VALID_STATUSES


@router.get("")
def list_applications():
    """List all applications, newest first."""
    client = get_supabase_client()
    result = (
        client.table("applications")
        .select("*")
        .order("applied_at", desc=True)
        .execute()
    )
    return result.data


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
