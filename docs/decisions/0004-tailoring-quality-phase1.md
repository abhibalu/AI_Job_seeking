# ADR-0004: Tailoring Quality — Phase 1 Fixes

**Date:** 2026-03-13
**Status:** Accepted

## Problem

The Actor-Critic tailoring loop produced inconsistent and sometimes inauthentic resumes. Root cause analysis identified 5 issues:

1. **ATS keywords bug** — Both jd_context construction sites used the wrong field name (`keywords_to_include` instead of `ats_keywords`). The tailor received an empty keyword list every time.
2. **Temperature too high** — Tailor and Critic both ran at 0.7 (creative default) despite the tailor prompt saying "You are NOT a creative writer."
3. **No structural validation** — Nothing enforced bullet count preservation, ID integrity, or change ratio limits.
4. **Force-saved resumes indistinguishable** — Max-revision resumes saved as `pending` (same as critic-approved).
5. **Critic scope too broad** — Tried to catch structure + content + tone in one pass.

## Analysis

The ATS keywords bug alone explains a large portion of quality issues — the tailor's "Vocabulary Source" strategy was completely inert. Combined with a 0.7 temperature, the tailor was creatively rephrasing without keyword guidance.

The evaluator (0.3) and JD parser (0.2) temperatures were correctly set for their roles. The tailor (conservative editor) and critic (strict reviewer) should be equally constrained.

Structural violations (changed bullet counts, missing IDs, over-editing) were only caught if the LLM critic happened to notice — no deterministic enforcement.

## Decision

Phase 1: Fix immediate issues without architectural changes.

1. Fix `keywords_to_include` → `ats_keywords` in both `api/routes/resumes.py` and `agents/pipeline_graph.py`
2. Lower temperatures: Tailor 0.7→0.3, Critic 0.7→0.2
3. Add `node_validate` to the subgraph (pure Python, no LLM) between draft and critique
4. Differentiate force-save status: `needs_review` for max-revision saves, `pending` for clean approval

Phase 2 (planned): Separate "what to change" (planning) from "make the changes" (execution) into distinct pipeline nodes. See `docs/proposals/tailoring-quality-improvement.md`.

## Consequences

- Tailor now receives 5-12 ATS keywords per job (was receiving `[]`)
- More consistent output from lower temperatures
- Structural violations caught deterministically before the critic runs — saves an LLM call on invalid drafts
- New subgraph flow: `draft → validate → (critique or revise) → ... → save`
- Force-saved resumes distinguishable in the DB via `status='needs_review'`
- New file: `agents/resume_validator.py`
