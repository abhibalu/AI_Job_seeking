# TailorAI Architecture Map

> Load this file when a task spans multiple domains and you need to understand import
> directions, data flow, or cross-cutting rules before touching code.

---

## Dependency direction

```
agent_prompts/ → agents/ → services/ → api/ → glassresumatch-ai/
```

**Rules:**
- Nothing imports rightward (no circular deps, no frontend importing backend modules).
- `api/` does not import agents directly for request handling — agents are triggered
  via `BackgroundTasks`, not inline route calls.
- `glassresumatch-ai/` communicates with the backend only through `apiClient.ts`.
  No direct Supabase access from the frontend.
- `services/` imports from `agents/` (e.g. eval_worker calls pipeline_graph).
  `agents/` does not import from `services/`.

---

## Within agents/

```
agents/base.py (BaseAgent)
  └─ job_evaluator.py, jd_parser.py, change_planner.py,
     resume_tailor.py, resume_critic.py, resume_parser.py
       ↓
agents/pipeline_graph.py  (main LangGraph graph)
  └─ agents/tailoring_subgraph.py  (nested, compiled fresh per job inside node_tailor)
       ↓
agents/database.py  (Supabase read/write, no LLM calls)
agents/supabase_checkpointer.py  (LangGraph state persistence)
```

---

## Data flow (end to end)

```
Apify (LinkedIn scrape)
  → services/scraper_worker.py → parse_raw_json() → map_job_record()
  → Supabase: jobs table  (raw_json preserved for reprocessing)

  → services/eval_worker.py: fetches unevaluated jobs in batches
  → agents/pipeline_graph.py: per-job LangGraph execution
      → JobEvaluatorAgent → [skip | apply | tailor]
      → JDParserAgent  (if tailor path)
      → tailoring_subgraph: ChangePlanner → ResumeTailor → Validate → ResumeCritic → Save
  → Supabase: evaluations + tailored_resumes tables

  → services/telegram_notifier.py: notify on high match or pipeline error

  → api/ routes: read Supabase state for the frontend
  → glassresumatch-ai/: renders job list, evaluation details, tailor review
      → writes back only via POST endpoints (status updates, tailor trigger, GDoc export)
```

---

## Cross-cutting: Langfuse tracing

Every agent LLM call is traced via `@observe` decorators in `BaseAgent`.
Langfuse env vars are set at the top of `agents/base.py` **before** the langfuse import.

**Rule**: Do not add `@observe` outside `BaseAgent`. Creates duplicate traces and
misattributed costs.

---

## Cross-cutting: Supabase checkpointing

LangGraph state is persisted via `SupabaseSaver` in `agents/supabase_checkpointer.py`.
The top-level pipeline graph uses the checkpointer. `tailoring_subgraph` inherits it —
no nested checkpointing.

**Rule**: Never bypass the checkpointer in graph nodes. Runs must survive restarts.

---

## Cross-cutting: structured logging and correlation IDs (ADR-0017)

All log lines are emitted as JSON via `JSONFormatter` in `backend/logging.py`. Every line includes
a `correlation_id` field injected by `CorrelationFilter` (from `backend/log_context.py`).

Set at:
- **HTTP requests** — `RequestLoggingMiddleware` sets `X-Request-ID` (from header or generated),
  echoes it back in the response, clears in `finally`.
- **APScheduler workers** — `run_eval_worker` / `run_scrape_worker` set `run:{run_id[:8]}` /
  `scrape:{run_id[:8]}` at entry, clear in `finally`. APScheduler threads do **not** inherit
  `contextvars` automatically — must be set explicitly.
- **FastAPI background tasks** and `run_in_threadpool` inherit context automatically.

`backend/log_context.py` is the single source of truth for correlation ID state.

**Rule**: Never use `print()` in any background task or service. Always `logger.exception()` or
`logger.warning(..., exc_info=True)` inside `except` blocks — bare `logger.error(f"... {e}")`
silently drops the stack trace.

---

## Cross-cutting: background task status tracking

User-triggered long-running operations (batch eval, tailoring) follow:
`save_task_status()` in `agents/database.py` → frontend streams via SSE `GET /api/events/stream?task_id=...`
(ADR-0009). `GET /api/tasks/{task_id}` remains for non-SSE callers.
See `api/CLAUDE.md` for the full sequence and SSE event schema.

---

## Key shared resource: approved_skills.md

`agent_prompts/approved_skills.md` constrains what skills `ChangePlannerAgent` can add to
a resume. Edits take effect immediately on the next tailoring run — no deploy needed.

---

# TailorAI Architecture & Features Overview

## 1. System Components
TailorAI is a split-stack application:
- **Frontend**: A React application (GlassResumatch-AI) built with TypeScript. It provides a review interface (`TailorReview.tsx`) for users to compare their base resume against the tailored output, switch views, and export to PDF/Google Docs.
- **Backend**: A FastAPI server running Python. It orchestrates complex Natural Language pipelines using autonomous agents and connects to a Supabase PostgreSQL database for persistent storage.

## 2. Multi-Agent Tailoring Pipeline
The core value proposition of TailorAI is generating highly specific resumes tailored to a single Job Description (JD). The application achieves this not with a single LLM call, but through an orchestrated pipeline (`pipeline_graph.py`) that utilizes three specialized subagents before and during the tailoring process.

### 2.1 The Pre-Tailoring Subagents
Before a resume is rewritten, two analytical subagents run to build a strict context profile of the job:
1. **The Job Evaluator Subagent (`JobEvaluatorAgent`)**
   - **Role:** The harsh screener.
   - **Input:** Candidate's Base Resume (JSON), raw Job Description text, and the candidate's `approved_skills.md`.
   - **Task:** Scores the candidate's Base Resume against the raw JD text. 
   - **Output:** It determines if the job is a "Strong Match", "Moderate Match", or "Weak Match". Most importantly for tailoring, it generates explicit structural `gaps` (technical, domain, soft skills) and `improvement_suggestions`.
2. **The JD Parser Subagent (`JDParserAgent`)**
   - **Role:** The signal extractor.
   - **Input:** Raw Job Description text and the candidate's `approved_skills.md`.
   - **Task:** Normalizes the raw JD text against the candidate's `approved_skills` dictionary.
   - **Output:** It strictly returns lists of canonical `ats_keywords` and explicit `must_haves` hidden in the job posting.

### 2.2 The Tailoring Loop Subagents (Actor-Critic)
Once the job is deemed worth tailoring for, those analytical signals are injected into a specialized `tailoring_subgraph.py` which runs an Actor-Critic loop:
1. **The Actor Subagent (`ResumeTailorAgent`)**
   - **Role:** The "Conservative Editor".
   - **Input:** Base Resume (JSON), the candidate's `approved_skills.md`, the extracted JD context (`ats_keywords`, `gaps`), and any `critique` from previous graph iterations.
   - **Task:** It receives the JD context and drafts a JSON resume. Crucially, it is instructed to preserve bullet counts and IDs while only rewriting ~40% of the content.
2. **The Critic Subagent (`ResumeCriticAgent`)**
   - **Role:** The strict Hiring Manager.
   - **Input:** The Actor's newly drafted Resume (JSON), the extracted JD context, and the candidate's `approved_skills.md`.
   - **Task:** It reviews the Actor's newly generated draft against the established JD requirements and the candidate's actual approved skills. 
   - **Output:** It outputs an array of actionable critiques (e.g., "You hallucinated a skill," or "You missed an ATS keyword").
3. **Routing:** 
   - If the Critic array is empty (~0 flaws found), the graph routes to **Save**.
   - If flaws are found, it routes back to the Actor for a retry, appending the critique to the prompt.
   - *Failsafe*: A `MAX_REVISIONS = 2` counter prevents infinite LLM loops.
5. **Save Node**: Cleans up internal metadata (e.g. keys starting with `_`) and saves the final JSON layout to the Supabase database.

## 3. Google Docs Export Service
Users can export their structured JSON resume into a fully formatted Google Doc.
- **Service (`google_docs.py`)**: Uses OAuth2 (`google-authentication.json`) for authorization.
- **Organization**: Automatically attempts to find or create a master folder (via `GOOGLE_DRIVE_FOLDER_ID`), then nests a subfolder named after the *Company*.
- **Sync/Replace Logic**: If an export already exists for the specific role at that company, the service clears the content via a `deleteContentRange` API request and injects the updated resume text, maintaining the same Document URL.
