"""
agents/evaluator_writer.py — OotoCV adaptation.

Writes the new card-line columns (top_strength, deciding_factor, kill_shot,
red_flags) to job_evaluations after the existing save_evaluation() call.
Lives in a separate module so this branch leaves agents/database.py
untouched — the Phase 1 placeholder-row lifecycle WIP there is unaffected.

The normalizer enforces em-dash format on red_flags (R6 mitigation): the
OotoCV SKIP layout splits each red_flag string on " — " to render the
label in bold and the explanation in muted gray. If the evaluator emits
a plain hyphen, the UI breaks silently. The normalizer rewrites any
`<space><hyphen-or-endash><space>` sequence to ` — ` on write.

For the four-way verdict mapping itself, see ADR-0023 and the prompt at
agent_prompts/job_evaluator.md.
"""
import logging
import re

from agents.database import _get_supabase, save_evaluation

logger = logging.getLogger(__name__)


# Plain hyphen (`-`) or en-dash (`–`) surrounded by whitespace becomes em-dash.
# Already-em-dashed strings are left untouched.
_HYPHEN_LIKE_RE = re.compile(r"\s+[-–]\s+")
_EM_DASH = " — "  # " — " — the canonical separator the frontend splits on.


def _normalize_red_flags(items) -> list[str]:
    """Coerce each red_flag entry to a `Label — explanation` string.

    - Strings: normalize plain hyphens / en-dashes to em-dash.
    - Non-strings: dropped silently. Bad LLM output should not propagate
      to the DB as ints / dicts / None.
    - Empty / whitespace-only strings: dropped.
    """
    if not items:
        return []
    out: list[str] = []
    for raw in items:
        if not isinstance(raw, str):
            continue
        s = raw.strip()
        if not s:
            continue
        out.append(_HYPHEN_LIKE_RE.sub(_EM_DASH, s))
    return out


def save_evaluation_with_card_lines(result: dict) -> None:
    """Persist a JobEvaluatorAgent result, including the OotoCV card lines.

    Two-step:
      1. Call the existing save_evaluation(result) so legacy columns and
         downstream consumers (ChangePlannerAgent / ResumeTailorAgent) get
         the same shape they have today.
      2. Issue a second UPDATE keyed by job_id to set top_strength,
         deciding_factor, kill_shot, red_flags.

    Step 2 is a no-op when none of those fields are present (e.g. during
    a transition window where the evaluator hasn't been redeployed yet),
    so this wrapper is safe to call from every existing save_evaluation
    site even before the prompt is updated.
    """
    save_evaluation(result)

    card_payload = {
        "top_strength":    result.get("top_strength"),
        "deciding_factor": result.get("deciding_factor"),
        "kill_shot":       result.get("kill_shot"),
        "red_flags":       _normalize_red_flags(result.get("red_flags")),
    }
    # Skip the second round-trip if the evaluator hasn't been redeployed yet.
    if not any(v for v in card_payload.values()):
        return

    job_id = result.get("job_id")
    if not job_id:
        logger.warning("save_evaluation_with_card_lines: missing job_id; skipping card-line UPDATE")
        return

    try:
        _get_supabase().table("job_evaluations").update(card_payload).eq(
            "job_id", job_id
        ).execute()
    except Exception:  # noqa: BLE001
        logger.warning(
            "save_evaluation_with_card_lines: card-line UPDATE failed",
            exc_info=True,
            extra={"job_id": job_id},
        )
