"""
POST /api/resumes/roast — transient resume critique (OotoCV Settings utility).

LLM-only path. No DB writes. The roast result is returned verbatim from the
agent; if a quality-trend history is wanted later, add a `resume_roasts`
table — for now we honor the spec decision (transient).

This is a sibling router on /api/resumes to avoid touching the Phase 1 WIP
in api/routes/resumes.py.
"""
import logging

from fastapi import APIRouter
from pydantic import BaseModel

from agents.roast import roast_resume
from backend.service_guard import require_service

logger = logging.getLogger(__name__)
router = APIRouter()


class RoastBody(BaseModel):
    # Accepted for symmetry with the eventual "roast any saved resume" flow.
    # Today the agent always roasts the master resume — see agents/roast.py.
    resume_id: str | None = None


@router.post("/roast")
def roast(body: RoastBody):
    """Roast the user's master resume. Returns `{"items": [...]}`."""
    require_service("openrouter")  # 503 if OpenRouter is disabled (ADR-0019).
    return roast_resume(resume_id=body.resume_id)
