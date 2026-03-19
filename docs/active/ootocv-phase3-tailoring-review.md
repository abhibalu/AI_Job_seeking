# Plan: OotoCV Phase 3 — Tailoring Review UI

**Status:** 🟡 In Progress
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
- [ ] Does `PATCH /tailoring/:id/changes/bulk` exist or does bulk accept loop individual calls on the frontend?
- [ ] What renders in the change card when `accepted_text` has been set to `original_text` (Keep original)? Badge? Strikethrough on tailored_text?
- [ ] Cover letter: is the textarea in the same review flow or a separate section/step?

## Out of Scope
- Cover letter agent / prompt (backend generates it before this UI runs — prompt is a separate concern)
- Rejection regeneration loop changes (MAX_REVISIONS logic stays; this phase only adds the third button)

---

## Implementation Checklist

### Backend (agents/, api/, supabase_db/)
- [ ] `api/routes/tailoring.py` (or equivalent): `PATCH /tailoring/:id/changes/:change_id` accepts `action: 'accept' | 'reject' | 'keep_original'`
- [ ] Handler: `keep_original` → sets `accepted_text = original_text`, does NOT trigger revision loop
- [ ] `PATCH /jobs/:id/cover_letter`: accepts `cover_letter: string`, saves to DB

### Frontend (glassresumatch-ai/)
- [ ] `TailorReview.tsx`: render `Accept · Reject · Keep original` per change (replaces current two-button layout)
- [ ] `TailorReview.tsx`: "Keep original" calls API with `action: 'keep_original'`, updates local state immediately
- [ ] `TailorReview.tsx`: sort changes — high-confidence first, then low-confidence group sorted by ascending confidence score
- [ ] `TailorReview.tsx`: sticky footer with `Accept all remaining →` chip
- [ ] `TailorReview.tsx`: bulk accept calls `PATCH .../changes/bulk` or loops individual calls
- [ ] `TailorReview.tsx`: cover letter section — `<textarea>` pre-filled with `job.coverLetter`, saves on blur via `PATCH /jobs/:id/cover_letter`

---

## Progress Log
<!-- Append-only. Format: `- YYYY-MM-DD: what done, surprises, what changed` -->
- 2026-03-19: Phase 3 plan created. Depends on Phase 1 (Change model with original_text + cover_letter field).
