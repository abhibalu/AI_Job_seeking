# ADR-0010 — Change data model must preserve original_text

**Date**: 2026-03-19
**Status**: Accepted

## Context
The current tailoring subgraph (`tailoring_subgraph.py`) has a `MAX_REVISIONS=2` failsafe that saves the current draft when revision limits are hit. The problem: "current draft" may be the AI's second (still wrong) attempt — not the user's original text. `TailorReview.tsx` shows approve/reject buttons only. There is no escape hatch that lets a user say "I want the original wording, not any AI version."

## Decision
Every `Change` object stores three fields: `original_text` (immutable — the pre-AI text), `tailored_text` (AI output), and `accepted_text` (nullable — the final value, set on user action). "Keep original" is a first-class action that sets `accepted_text = original_text` immediately without triggering a regeneration loop.

## Reasoning
Without `original_text` stored separately, the system has no reliable way to recover the user's exact prior wording once the AI has processed it. The "reject → regenerate" loop (up to MAX_REVISIONS) is not a substitute: it may produce two wrong versions before giving up, and the fallback saves the wrong version. Preserving `original_text` at write time is cheap and makes the system auditable and reversible.

## Alternatives Considered
- **Keep current (no original_text field)**: Rejected because the MAX_REVISIONS fallback silently saves bad AI output as the accepted version, which could appear in a submitted CV without the user realising.
- **Reconstruct original from git/version history**: Rejected because the tailoring pipeline doesn't version resume text at that granularity, and reconstruction would be unreliable.
- **Store original only when user rejects**: Rejected because at that point the original text may already be lost from the pipeline's working state.

## Consequences
**Positive**:
- "Keep original" becomes a genuine first-class action in the review UI
- Audit trail: every change has a clear before/after regardless of what the user chose
- Eliminates the bad-fallback problem in MAX_REVISIONS logic

**Negative / Trade-offs**:
- Slight storage increase: three text fields per change instead of one or two
- Schema migration required for existing `changes` records (nulls acceptable for `original_text` on historical records)

## Do Not Revisit Unless
Storage costs for the per-change text duplication become measurably prohibitive at scale (unlikely — resume text is small).
