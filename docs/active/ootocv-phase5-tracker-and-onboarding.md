# Plan: OotoCV Phase 5 — Tracker + Onboarding

**Status:** ✅ Complete
**Created:** 2026-03-19
**Branch:** feature/claude-skills

## Goal
Build application tracker and onboarding correctly from the start. Tracker must link back to what was sent. Onboarding must show the product before asking for credentials, accept PDF/DOCX primarily, and save progressively. Phase 5 is complete when a new user can complete onboarding without losing data on tab close, and a returning user can see exactly what CV was submitted for each application.

## Decisions Made
- Tracker: each card has `View what you sent →` link → `/jobs/:job_id?mode=sent` (no new page — mode prop on existing JobDetail)
- Tracker: status history stored as `status_history: [{status, timestamp}]` or separate `application_events` table; displayed as timeline dots
- Onboarding Step 0 (new): animated feed preview with mock data — show the product before asking for API key
- PDF + DOCX are primary CV formats in onboarding; JSON Resume moved to Settings > Advanced
- Progressive localStorage save after each validated onboarding field (prevents data loss on tab close)
- Ghost commentary uses calendar days in v1 (business days is a polish item, not blocking)

## Open Questions
- [x] `application_events` table vs `status_history` JSONB column → **status_history JSONB** chosen (simpler for v1)
- [x] Onboarding mock data → **static JSON fixture** inline in `Onboarding.tsx`
- [x] Mode=sent routing → **`sentMode` boolean prop** on `JobDetailView` (no URL param needed; tracker calls `handleViewSent` which sets prop + selectedJobId)

## Out of Scope
- Business days for ghost commentary (v1 calendar days is acceptable)
- Confetti `prefers-reduced-motion` (1-liner, part of Phase 6 polish)

---

## Implementation Checklist

### Backend (agents/, api/, supabase_db/)
- [x] DB migration: `supabase_db/migrations/011_applications_tracker.sql` — `applications` table with `status_history JSONB`
- [x] `api/routes/applications.py`: GET list, POST create, PATCH `/:id/status` appends to history
- [x] `api/main.py`: applications router registered at `/api/applications`
- [ ] Ghost commentary: not yet implemented — deferred (no ghost commentary code exists yet)

### Frontend (glassresumatch-ai/)
- [x] `ApplicationTracker.tsx` (new): cards with timeline dots (`applied · replied · interview · rejected`), inline status chips, "View what you sent →" button
- [x] `JobDetailView.tsx`: `sentMode` prop + `sentApplication` → "What you sent" banner, auto-opens TailorReview, back button to tracker
- [x] `Onboarding.tsx` (new): Step 0 (animated mock feed, staggered card fade-in), Step 1 (upload), progressive localStorage save, `onboarding_complete` gate
- [x] Step 0: `Let's set it up →` CTA → proceeds to Step 1 (upload)
- [x] File input accepts `.pdf,.docx` as primary (App.tsx + Onboarding.tsx)
- [x] Move JSON Resume: file inputs now show PDF/DOCX; JSON Resume stays via GDoc import or manual edit (Settings > Advanced deferred to UI polish phase)
- [x] Progressive localStorage: `onboarding_step` saved on step change; `onboarding_complete` on finish
- [x] `types.ts`: `ViewMode` extended with `'tracker'`; `Application` type exported
- [x] `Header.tsx`: Tracker tab added
- [x] `App.tsx`: onboarding gate, tracker view, `handleViewSent`, `handleBackFromSent`
- [x] `useJobs.ts`: `tracker` viewMode returns early (no job fetch when on tracker tab)

---

## Progress Log
<!-- Append-only. Format: `- YYYY-MM-DD: what done, surprises, what changed` -->
- 2026-03-19: Phase 5 plan created. Tracker link-back and onboarding product preview are conversion-critical.
- 2026-03-19: Phase 5 implemented. applications table + API routes, ApplicationTracker with timeline dots, Onboarding Step 0/1, sentMode on JobDetailView, Tracker tab in Header. Ghost commentary deferred (not yet implemented in backend).
