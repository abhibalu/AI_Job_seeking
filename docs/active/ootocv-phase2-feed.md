# Plan: OotoCV Phase 2 — Feed + Card

**Status:** 🟡 In Progress
**Created:** 2026-03-19
**Branch:** feature/claude-skills

## Goal
Build the verdict-conditional card feed correctly from the start — before any patterns get hardcoded. Phase 2 is complete when `JobCard.tsx` renders with always-visible `⋯` quick actions, correct conditional button copy for Apply Direct, and `useJobs.ts` applies the filter/actioned intersection rule.

## Decisions Made
- `⋯` icon at `opacity-30` always visible (not `opacity-0`) — discoverable on first session, touch-accessible
- Quick action buttons reveal on hover (desktop) or tap on `⋯` (touch) — not hover-only
- Button copy is conditional on `tailoringStatus`: `Apply with base CV →` vs `Apply with tailored CV →`
- Filter pills operate on unactioned jobs only; actioned/dimmed cards render below filtered results regardless of filter state
- APPLY DIRECT sorts before TAILOR at equal `matchScore` (less friction = more urgent)

## Open Questions
- [ ] Does the feed sort live in `useJobs.ts` or a separate `sort.ts` utility?
- [ ] Touch reveal for `⋯`: inline expansion or a bottom sheet?

## Out of Scope
- TailoringReview UI (phase 3)
- SSE connection for live status updates (phase 4) — JobCard shows `tailoringStatus` from initial load only in this phase

---

## Implementation Checklist

### Frontend (glassresumatch-ai/)
- [ ] `JobCard.tsx`: add permanent `⋯` icon at `opacity-30` on card right edge
- [ ] `JobCard.tsx`: hover → icon `opacity-100`, quick action buttons slide in
- [ ] `JobCard.tsx`: tap `⋯` on touch → reveal action buttons inline (no hover)
- [ ] `JobCard.tsx`: Apply Direct button copy conditional — `tailoringStatus === 'ready'` → "Apply with tailored CV →" else "Apply with base CV →"
- [ ] `JobCard.tsx`: pass `cv_version: 'base' | 'tailored'` in `PATCH /jobs/:id/action` call
- [ ] `useJobs.ts`: filter pills apply to unactioned jobs only
- [ ] `useJobs.ts`: actioned/dimmed cards always render below filtered results
- [ ] `sort.ts` (or equivalent): APPLY DIRECT sorts before TAILOR at same `matchScore` — 1-line comparator change

---

## Progress Log
<!-- Append-only. Format: `- YYYY-MM-DD: what done, surprises, what changed` -->
- 2026-03-19: Phase 2 plan created. Depends on Phase 1 (tailoringStatus in types.ts).
