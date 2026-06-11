"""
POST /api/resumes/{resume_id}/changes/{change_id}/feedback.

Sibling endpoint to the existing PATCH /resumes/{rid}/changes/{cid} accept/
reject/keep_original handler in api/routes/resumes.py. We keep this in a
separate router so the OotoCV adaptation branch does not collide with the
Phase 1 placeholder-row lifecycle WIP in resumes.py.

Captures the user's reject chip ("Too formal" / "Not accurate" / "Other"),
bumps regeneration_count via the existing record_change_feedback helper,
and returns HTTP 409 when the cap is hit so the UI can fall back to
"edit manually" (R8 mitigation).

The actual regeneration LLM call is not driven from this endpoint yet —
this hop just stamps the audit fields. The regeneration job is wired in
Phase 4 (Task 21).
"""
import logging
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.database import RegenerationCapReached, record_change_feedback

logger = logging.getLogger(__name__)
router = APIRouter()


_FeedbackChip = Literal["too_formal", "not_accurate", "other"]


class FeedbackBody(BaseModel):
    feedback_type: _FeedbackChip


@router.post("/{resume_id}/changes/{change_id}/feedback")
def submit_change_feedback(
    resume_id: str,
    change_id: str,
    body: FeedbackBody,
):
    """Record a reject + feedback chip; bump regeneration_count.

    Returns the updated row. 409 if the regeneration cap is already reached.
    `resume_id` is accepted for URL symmetry with the sibling PATCH endpoint
    but not used by the helper — the change row is keyed by `change_id`.
    """
    try:
        return record_change_feedback(
            change_id=change_id,
            feedback_type=body.feedback_type,
        )
    except RegenerationCapReached as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        # record_change_feedback validates feedback_type itself; pydantic
        # already filtered before us, but surface any helper-side ValueError
        # as 400 rather than 500 just in case.
        raise HTTPException(status_code=400, detail=str(exc))
