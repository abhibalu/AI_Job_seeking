# Plan: OotoCV Phase 1 — Foundation (Data Model)

**Status:** 🟡 In Progress
**Created:** 2026-03-19
**Branch:** feature/claude-skills

## Goal
Establish the data model that all subsequent OotoCV phases depend on. Every field, enum value, and schema change in this phase is a prerequisite for the UI work in phases 2–5. Phase 1 is complete when the DB, API schemas, and frontend types are in sync and the migration has been applied.

## Decisions Made
- `tailoringStatus` is aspirational (not in current code): treat as new field, add to DB + schemas + types.ts (ADR context: gap analysis is ground truth)
- `cancelled` added to `tailoring_status` enum (not a `partial` state — discards work on cancel)
- `Change` model stores `original_text` (immutable), `tailored_text`, `accepted_text` (nullable) — see ADR-0010
- `posted_at` returns UTC ISO string from backend; frontend uses existing `timeAgo()` util — no server-formatted relative strings
- `cover_letter` field added to tailoring output; editability from day one — see ADR-0011
- `cron_tz` stored as IANA zone name paired with `cron_time` — see ADR-0012 context

## Open Questions
- [x] Which table gets `tailoring_status`: `jobs` or `tailored_resumes`? → `resumes` table (consolidated tailored_resumes)
- [x] `cover_letter`: separate DB field on `tailored_resumes`, or part of the JSON output blob? → Separate TEXT column on `resumes`
- [x] `original_text` on `Change`: backfill strategy for existing rows? → Nulls acceptable for historical rows; new rows always populated

## Out of Scope
- UI changes (phase 2+)
- SSE endpoint (phase 4)
- Cover letter agent implementation (phase 3 or later)

---

## Implementation Checklist

### Backend (agents/, api/, supabase_db/)
- [x] DB migration: `010_ootocv_foundation.sql` — `tailoring_status` + `cancelled` + `cover_letter` on `resumes`; new `resume_changes` table; new `system_config` table with `cron_tz` + `cron_time` + `auto_send_threshold`
- [x] `api/schemas.py`: added `tailoring_status` and `cover_letter` to `JobDetail`; new `ResumeChange`, `ResumeChangeActionRequest`, `ResumeChangeBulkActionRequest`, `SystemConfigItem`, `CronConfigRequest`
- [x] `api/routes/resumes.py`: added `GET /{resume_id}/changes`, `PATCH /{resume_id}/changes/{change_id}`, `PATCH /{resume_id}/changes/bulk`, `PATCH /{resume_id}/cover_letter`
- [x] `agents/database.py`: `save_tailored_resume` now writes `resume_changes` rows via `_save_resume_changes`; added `update_cover_letter`, `update_tailoring_status`, `get_resume_changes`, `apply_change_action`, `apply_bulk_change_action`, `get_system_config`, `set_system_config`
- [ ] `api/routes/jobs.py`: verify `posted_at` returns raw UTC datetime (not pre-formatted) — `posted_at` is `TIMESTAMPTZ` in DB, returned as string by Supabase; likely already correct — needs verification

### Frontend (glassresumatch-ai/)
- [x] `services/apiClient.ts`: added `tailoring_status` to `Job`; added `ResumeChange` interface; updated `TailoredResume` with `tailoring_status` + `cover_letter`; added `getResumeChanges`, `applyChangeAction`, `applyBulkChangeAction`, `updateCoverLetter` methods
- [x] `types.ts`: exported `TailoredResume` and `ResumeChange`
- [x] `utils/sort.ts`: APPLY DIRECT sorts before TAILOR at same matchScore (Phase 2 sort fix, done while in the layer)
- [ ] Verify `formatTimeAgo(job.posted_at)` is used at render time in all job card components

---

## Progress Log
<!-- Append-only. Format: `- YYYY-MM-DD: what done, surprises, what changed` -->
- 2026-03-19: Phase 1 plan created from OotoCV critique analysis. ADRs 0009–0012 recorded. No code changed yet.
- 2026-03-19: Phase 1 implemented on branch `feature/ootocv-build`. Migration 010 creates `resume_changes` table (normalised, not JSONB) and `system_config` table. `_save_resume_changes` writes rows from `edit_plan.edits[]` on every tailor save — `original_text` captured from `current_text` (immutable). Sort fix for APPLY DIRECT done in same pass (sort.ts). One open item: verify posted_at UTC format in job list response.
