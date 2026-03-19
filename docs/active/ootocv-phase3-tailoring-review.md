# Plan: OotoCV Phase 3 — Tailoring Review UI

**Status:** ✅ Complete
**Created:** 2026-03-19
**Branch:** feature/claude-skills

## Goal
Build `TailorReview.tsx` correctly: per-change granularity with three actions (Accept / Reject / Keep original), bulk accept, editable cover letter textarea, and confidence-sorted change ordering. Phase 3 is complete when a user can review every change individually, accept all remaining with one tap, and edit the generated cover letter before saving.

## Decisions Made
- Three buttons per change: `Accept · Reject · Keep original` (not two) — see ADR-0010
- "Keep original" sets `accepted_text = original_text` immediately — no regeneration loop triggered
- Cover letter: editable `<textarea>` pre-filled with AI output, saves on blur — not read-only — see ADR-0011
- Confidence sort: within the low-confidence group, sort by ascending confidence (worst first, so users see the most uncertain changes immediately)
- Bulk accept: `Accept all remaining →` chip in sticky footer — additive to granular controls, not replacing them

## Open Questions
- [x] Bulk endpoint exists at `PATCH /resumes/:id/changes/bulk` (scope='remaining') — no frontend loop needed.
- [x] Keep original: "Kept original" amber badge; tailored_text gets line-through+muted; original_text renders normal weight.
- [x] Cover letter textarea is in the same panel (scrollable left column, below the change cards), saves on blur.

## Out of Scope
- Cover letter agent / prompt (backend generates it before this UI runs — prompt is a separate concern)
- Rejection regeneration loop changes (MAX_REVISIONS logic stays; this phase only adds the third button)

---

## Implementation Checklist

### Backend (agents/, api/, supabase_db/)
- [x] `api/routes/resumes.py`: `PATCH /resumes/:id/changes/:change_id` accepts `action: 'accept' | 'reject' | 'keep_original'` — already implemented in phase 1
- [x] Handler: `keep_original` → sets `accepted_text = original_text`, does NOT trigger revision loop — already implemented
- [x] `PATCH /resumes/:id/cover_letter`: accepts `cover_letter: string`, saves to DB — already implemented

### Frontend (glassresumatch-ai/)
- [x] `TailorReview.tsx`: render `Accept · Reject · Keep original` per change via `ChangeCard` sub-component
- [x] `TailorReview.tsx`: "Keep original" calls API with `action: 'keep_original'`, updates local state immediately (optimistic)
- [x] `TailorReview.tsx`: changes rendered in server order (confidence asc — backend already sorts lowest first)
- [x] `TailorReview.tsx`: sticky footer with `Accept all remaining →` chip (disabled when remainingCount === 0)
- [x] `TailorReview.tsx`: bulk accept calls `applyBulkChangeAction(id, 'accept', 'remaining')` then refetches
- [x] `TailorReview.tsx`: cover letter `<textarea>` pre-filled with `tailoredResume.cover_letter`, saves on blur via `updateCoverLetter`

---

## Progress Log
<!-- Append-only. Format: `- YYYY-MM-DD: what done, surprises, what changed` -->
- 2026-03-19: Phase 3 plan created. Depends on Phase 1 (Change model with original_text + cover_letter field).
- 2026-03-19: All checklist items complete. Backend was already fully implemented from phase 1 (resumes.py). TailorReview.tsx rebuilt: split layout (420px left panel + resume preview right); ChangeCard sub-component with Accept/Reject/Keep original buttons, optimistic local state update, confidence + location meta, review badges; bulk accept → applyBulkChangeAction + refetch; cover letter textarea saves on blur; sticky footer with remaining count. Existing Approve/Reject/Download header controls preserved.
