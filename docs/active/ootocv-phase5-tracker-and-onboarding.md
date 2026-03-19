# Plan: OotoCV Phase 5 — Tracker + Onboarding

**Status:** 🟡 In Progress
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
- [ ] `application_events` table vs `status_history` JSONB column — which fits the existing schema better?
- [ ] Onboarding mock data: static JSON fixture or generated from a seed script?
- [ ] Does `/jobs/:job_id?mode=sent` use a query param or a separate route segment (`/jobs/:job_id/sent`)?

## Out of Scope
- Business days for ghost commentary (v1 calendar days is acceptable)
- Confetti `prefers-reduced-motion` (1-liner, part of Phase 6 polish)

---

## Implementation Checklist

### Backend (agents/, api/, supabase_db/)
- [ ] DB migration: add `status_history` JSONB to `applications` table (or create `application_events` table)
- [ ] `api/routes/applications.py`: `PATCH /applications/:id/status` appends to status history
- [ ] Ghost commentary: verify it stops once status advances past `applied/ghosting` state

### Frontend (glassresumatch-ai/)
- [ ] Application tracker card: `View what you sent →` link to `/jobs/:job_id?mode=sent`
- [ ] `JobDetail.tsx`: accept `mode=sent` query param → read-only CTAs, show approved CV diff + cover letter
- [ ] Application tracker card: timeline dots component (`applied · replied · interview · rejected`) driven by `status_history`
- [ ] `Onboarding.tsx` Step 0 (new): animated mock feed preview — show verdict cards, typewriter wit lines, TailoringStrip with mock data
- [ ] Step 0: single CTA `Let's set it up →` → proceeds to Step 1 (API key)
- [ ] `Onboarding.tsx`: file input accepts `.pdf, .docx` as primary (not JSON Resume)
- [ ] Move JSON Resume option to Settings > Advanced section
- [ ] Progressive localStorage save: `localStorage.setItem('onboarding_progress', ...)` after each validated field

---

## Progress Log
<!-- Append-only. Format: `- YYYY-MM-DD: what done, surprises, what changed` -->
- 2026-03-19: Phase 5 plan created. Tracker link-back and onboarding product preview are conversion-critical.
