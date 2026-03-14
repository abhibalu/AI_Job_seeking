# ADR-0006: Resume Parser Fidelity + Projects Section

**Date:** 2026-03-14
**Status:** Accepted

## Problem

After enabling Google Docs import (ADR-0005), the parsed output from `ResumeParserAgent` was losing significant content compared to the source document:

1. **Entire TECHNICAL PROJECTS section dropped** — 2 projects with 5 highlights gone from output
2. **Work highlights truncated** — every bullet shortened or paraphrased; first METRO bullet dropped entirely
3. **Location info stripped** — `Bangalore, India` absent from all work entries
4. **Education details truncated** — degree names and fields of study abbreviated

Additionally, the `label` field in `basics` was being hallucinated in some runs — the LLM grabbed the profile summary ("Engineer (5+ Years, with a valid VISA to work in IE)") instead of inferring a short job title.

A secondary issue: the `projects[]` array in the JSON Resume schema was silently dropped by `_to_frontend_format()` in the API, so even correct parses were invisible in the UI.

## Root Cause Analysis

### Parser issues

| # | Root Cause | Effect |
|---|---|---|
| 1 | `temperature=0.7` inherited from `BaseAgent` | Non-deterministic extraction; random omissions across runs |
| 2 | Instruction: *"Split descriptions into **concise** highlights"* | LLM treated parsing as a summarization task |
| 3 | Instruction: *"Extract as much information as possible"* — too weak | Easy to satisfy by extracting most but not all content |
| 4 | No section-mapping guidance | "TECHNICAL PROJECTS" in source not explicitly linked to `projects[]` in schema |
| 5 | `label` instruction: *"Infer if not explicitly stated"* | LLM grabbed profile text instead of most recent job title |
| 6 | No one-shot example | LLM had no reference for expected fidelity level |

### UI issue

`_to_frontend_format()` in `api/routes/resumes.py` converted JSON Resume → frontend format but had no mapping for `projects[]`. The field was silently dropped before reaching the React frontend. `ResumePreview.tsx` also had no rendering logic for projects, and `types.ts` had no `Project` type.

## Decision

### Part A: Parser prompt and temperature

- Set `temperature=0.1` in `ResumeParserAgent.__init__` (parsing is deterministic extraction, not creative generation)
- Rewrote `RESUME_PARSER_SYSTEM_PROMPT` with:
  - **"VERBATIM extraction, not summarization"** as the top-level framing
  - **Explicit section-mapping table**: `TECHNICAL PROJECTS → projects[]`, `WORK EXPERIENCE → work[]`, etc.
  - **Per-bullet preservation rule**: "each bullet point becomes a SEPARATE highlights[] entry preserving the FULL original text"
  - **DO NOT rules**: no summarizing, no truncating, no merging bullets, no dropping sections, no stripping location, no abbreviating degrees
  - **Label guardrail**: "use the most recent job title from WORK EXPERIENCE, not profile/summary text"
- Added `ONE_SHOT_EXAMPLE` constant (content of `test/one_shot_json_resume.json`) embedded in `build_user_prompt()` to show expected structure and fidelity without bloating the system prompt

### Part B: Projects in the frontend pipeline

- **`api/routes/resumes.py`**: Added `projects[]` mapping in `_to_frontend_format()` — maps `name`, `description`, `highlights`, `url`, `id` from JSON Resume to frontend `Project` objects
- **`glassresumatch-ai/types.ts`**: Added `Project` interface (`id`, `name`, `description`, `highlights`, `url`) and `projects?: Project[]` to `ResumeData`
- **`glassresumatch-ai/components/ResumePreview.tsx`**: Added Projects section rendered between Experience and Skills for all templates. `ats_friendly` layout: bold project name, URL float-right, description paragraph, hanging-indent bullets. Section hidden when `projects` is empty.

## Consequences

- Parser now produces verbatim output — no shortening of bullets, no dropped sections
- `label` field reliably reflects the most recent job title
- Projects section visible in TailorReview diff/final view and base resume preview
- `_to_frontend_format()` is now a complete mapping with no silent data loss
- `INITIAL_DATA` in `types.ts` includes `projects: []` for correct empty state

### Modified Files

- `agents/resume_parser.py` — `temperature=0.1`, rewritten prompt, `ONE_SHOT_EXAMPLE`, updated `build_user_prompt()`
- `agents/base.py` — Added `response_format` param to `_call_llm()` (used by parser for `json_object` mode)
- `api/schemas.py` — Added `JSONResumeSchema` Pydantic models for LLM output validation
- `api/routes/resumes.py` — Added `projects[]` mapping in `_to_frontend_format()`
- `glassresumatch-ai/types.ts` — Added `Project` interface and `projects` field
- `glassresumatch-ai/components/ResumePreview.tsx` — Added Projects section rendering
