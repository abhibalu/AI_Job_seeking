"""
ResumeRoastAgent — OotoCV resume critic.

Transient utility surfaced from Settings; never persisted. See ADR-0023-adjacent
risk register decision #3 (transient over stored history). The route layer
(api/routes/resume_roast.py) calls roast_resume() which:

  1. Loads the master resume via get_master_resume()
  2. Runs ResumeRoastAgent
  3. Returns the JSON payload verbatim — no DB writes, no audit row

If the master resume is missing, returns {"items": []} so the endpoint stays
200 and the UI can show an "upload first" empty state.
"""
import json
import logging
import os
from pathlib import Path

from agents.base import BaseAgent
from agents.database import get_master_resume

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "agent_prompts" / "resume_roast.md"


class ResumeRoastAgent(BaseAgent):
    """OotoCV-voice critic that emits roast items for a resume JSON."""

    def __init__(self, model: str | None = None):
        # Analytical agent — temperature 0.2 per agents/CLAUDE.md table.
        super().__init__(model=model, temperature=0.2)

    def get_system_prompt(self) -> str:
        return _PROMPT_PATH.read_text(encoding="utf-8")

    def build_user_prompt(self, resume: dict | None = None, **_) -> str:
        if not resume:
            return "RESUME (JSON):\n{}\n\nRoast it."
        return (
            "RESUME (JSON):\n"
            + json.dumps(resume, indent=2, ensure_ascii=False)
            + "\n\nRoast it."
        )


def roast_resume(resume_id: str | None = None) -> dict:
    """Roast the master resume; ignores `resume_id` for now.

    `resume_id` is accepted for forward-compat with a future "roast any
    saved tailored resume" feature, but today we only roast the master CV
    because that's the OotoCV Settings affordance. Pass it through but
    don't fail if it's None.
    """
    master = get_master_resume()
    if not master or not master.get("content"):
        return {"items": []}

    try:
        result = ResumeRoastAgent().run(resume=master["content"])
    except Exception:
        logger.exception("ResumeRoastAgent run failed")
        return {"items": []}

    items = result.get("items") if isinstance(result, dict) else None
    if not isinstance(items, list):
        return {"items": []}
    return {"items": items}
