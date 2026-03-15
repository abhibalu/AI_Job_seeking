# ADR-0005: Plan-then-Execute Architecture + Google Docs Import

**Date:** 2026-03-14
**Status:** Accepted

## Problem

Two distinct gaps identified after Phase 1 quality fixes (ADR-0004):

1. **jd_context dump problem**: The tailor received ALL context (base resume, jd_context with gaps/keywords/suggestions, full approved_skills) in one massive prompt and had to both *decide what to change* and *make the changes* in a single LLM call. The evaluator already produced precise edit suggestions (`work.metro.highlights[4]`), but this precision was lost in the context soup.

2. **Google Docs was export-only**: The system could export tailored resumes to Google Docs but had no way to import a resume from Google Docs. Testing required uploading PDFs, even though the source of truth lived in Google Docs.

## Analysis

### Plan-then-Execute

The single-shot tailor combined two cognitive tasks:
- **Planning**: Analyzing gaps, cross-referencing approved skills, deciding which bullets to edit
- **Execution**: Actually modifying the resume JSON with specific edits

This is analogous to asking a surgeon to write the surgery plan and perform the surgery simultaneously. Results were inconsistent: sometimes over-editing, sometimes under-editing, with no audit trail of *why* specific changes were made.

The evaluator already outputs structured edit suggestions, but they were flattened into `jd_context` as an unstructured blob. A dedicated planner can distill these into a precise, inspectable edit plan.

### Google Docs Import

OAuth scopes (`documents` + `drive`) and credentials were already configured for export. The Google Docs API supports reading document content. The existing `process_resume_background()` function accepts raw text and runs `ResumeParserAgent` — so import only needs to extract text from the doc and feed it into the same pipeline.

## Decision

### Part A: Plan-then-Execute

Split the tailoring subgraph from `draft → validate → critique → save` into `plan → draft → validate → critique → save`:

- **New node: `plan`** (`ChangePlannerAgent`, temp 0.2): Analyzes gaps and approved skills, produces a structured edit plan with specific locations, actions, and reasons
- **Refocused `draft`** (`ResumeTailorAgent`): Now receives `edit_plan` instead of `jd_context` — applies planned edits only
- **Enhanced `validate`**: Additionally checks that only planned locations were modified
- **Refocused `critique`** (`ResumeCriticAgent`): Focuses on naturalness and authenticity only (structural checks handled by validator)
- **`save`**: Stores `edit_plan` alongside the tailored resume for audit trail

### Part B: Google Docs Import

- Add `read_google_doc()` to `services/google_docs.py`
- Add `POST /api/resumes/import-gdoc` endpoint that extracts text and reuses `process_resume_background()`
- Add frontend modal with URL/ID input and polling

### Part C: UI Navigation Fix

- Sync `viewMode` with browser history via `pushState`/`popstate` so back button works
- Add empty state when no master resume exists (was showing blank page)

## Consequences

- New subgraph flow: `plan → draft → validate → critique → save` (was: `draft → validate → critique → save`)
- Every tailored resume now has an `edit_plan` JSONB companion record — audit trail of what changed and why
- Tailor prompt simplified significantly — no longer needs to analyze gaps, just follow the plan
- Critic prompt narrowed to content quality (naturalness, authenticity, AI patterns) — structural checks handled by validator
- Google Docs import uses same downstream path as PDF upload — no new parsing logic
- Browser back button now works correctly in the SPA

### New Files
- `agents/change_planner.py` — ChangePlannerAgent
- `agent_prompts/change_planner.md` — Planner system prompt
- `supabase_db/migrations/007_resume_edit_plan.sql` — `edit_plan` JSONB column

### Modified Files
- `agents/tailoring_subgraph.py` — New `plan` node, updated state, updated `save` to include edit_plan
- `agents/resume_tailor.py` — Accepts `edit_plan` instead of `jd_context`
- `agents/resume_critic.py` — Accepts `base_resume` + `edit_plan` for comparison
- `agents/resume_validator.py` — Added `validate_planned_edits()`
- `agents/database.py` — `save_tailored_resume()` accepts `edit_plan`
- `agent_prompts/resume_tailor.md` — Refocused as "precision editor following a plan"
- `agent_prompts/resume_critic.md` — Refocused on naturalness/authenticity
- `services/google_docs.py` — Added `read_google_doc()`
- `api/routes/resumes.py` — Added import-gdoc endpoint
- `api/schemas.py` — Added `GDocImportRequest`
- `glassresumatch-ai/App.tsx` — GDoc import UI, history-based navigation, empty state
- `glassresumatch-ai/services/apiClient.ts` — Added `importFromGoogleDoc()`
