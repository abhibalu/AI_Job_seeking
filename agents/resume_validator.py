"""
Structural validator for tailored resumes.

Pure Python checks (no LLM) that verify the draft resume
maintains structural integrity against the base resume.
"""
import logging

logger = logging.getLogger(__name__)


def validate_structure(base_resume: dict, draft_resume: dict) -> list[str]:
    """
    Compare draft against base resume for structural violations.
    Returns a list of violation strings (empty = valid).
    """
    violations = []

    base_work = base_resume.get("work", [])
    draft_work = draft_resume.get("work", [])

    # 1. Work entry count must match
    if len(base_work) != len(draft_work):
        violations.append(
            f"Work entry count changed: base has {len(base_work)}, draft has {len(draft_work)}"
        )

    # 2. Bullet count per work entry must match
    for i, base_job in enumerate(base_work):
        if i >= len(draft_work):
            break
        draft_job = draft_work[i]
        base_id = base_job.get("id", f"index_{i}")

        base_count = len(base_job.get("highlights", []))
        draft_count = len(draft_job.get("highlights", []))
        if base_count != draft_count:
            violations.append(
                f"'{base_id}': bullet count changed from {base_count} to {draft_count}"
            )

    # 3. ID preservation — all base IDs must appear in draft
    base_ids = {j.get("id") for j in base_work if j.get("id")}
    draft_ids = {j.get("id") for j in draft_work if j.get("id")}
    missing_ids = base_ids - draft_ids
    if missing_ids:
        violations.append(f"Missing work entry IDs in draft: {missing_ids}")

    extra_ids = draft_ids - base_ids
    if extra_ids:
        violations.append(f"Unexpected new work entry IDs in draft: {extra_ids}")

    # 4. No new top-level sections invented
    metadata_keys = {"_model_used", "_agent"}
    base_sections = set(base_resume.keys())
    draft_sections = set(draft_resume.keys()) - metadata_keys
    new_sections = draft_sections - base_sections
    if new_sections:
        violations.append(f"New sections invented: {new_sections}")

    # 5. Change ratio check (the "40% rule" — at most ~50% of bullets should change)
    base_bullets = [h for j in base_work for h in j.get("highlights", [])]
    draft_bullets = [h for j in draft_work for h in j.get("highlights", [])]
    if base_bullets and len(base_bullets) == len(draft_bullets):
        unchanged = sum(1 for b, d in zip(base_bullets, draft_bullets) if b == d)
        change_pct = 1 - (unchanged / len(base_bullets))
        if change_pct > 0.55:
            violations.append(
                f"Change ratio {change_pct:.0%} exceeds 50% — too much was rewritten"
            )

    # 6. Education entry count must match
    base_edu = base_resume.get("education", [])
    draft_edu = draft_resume.get("education", [])
    if len(base_edu) != len(draft_edu):
        violations.append(
            f"Education entry count changed: base has {len(base_edu)}, draft has {len(draft_edu)}"
        )

    return violations
