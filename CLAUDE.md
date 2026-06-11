# TailorAI

Autonomous job-seeking agent: scrapes LinkedIn jobs, evaluates fit, tailors resumes via a
multi-agent LangGraph pipeline. Stack: React frontend, FastAPI backend, Supabase (PostgreSQL).

## Commands

### Backend
```bash
pip install -r requirements.txt
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
pytest
pytest test/test_file.py::test_function -v
ruff check .
ruff format .
```

### Frontend
```bash
cd glassresumatch-ai
npm install
npm run dev    # port 3000
npm run build
```

### Infrastructure
```bash
docker-compose -f docker-compose.langfuse.yml up -d  # Langfuse observability
```

## Ports
- Frontend: 3000
- Backend API: 8000
- Langfuse: 3010

## Context map — load what your task needs

| Task touches                              | Load this next                        |
|-------------------------------------------|---------------------------------------|
| agents/, graphs, pipeline, DB schema      | agents/CLAUDE.md                      |
| api/, routes/, schemas, background tasks  | api/CLAUDE.md                         |
| agent_prompts/                            | agent_prompts/CLAUDE.md               |
| glassresumatch-ai/, frontend              | glassresumatch-ai/CLAUDE.md           |
| services/, scheduler, workers             | services/CLAUDE.md                    |
| supabase_db/, migrations                  | agents/CLAUDE.md (DB section)         |
| cross-cutting (>1 domain)                 | docs/active/TEMPLATE.md + domain files|
| import rules, full data flow              | docs/core/architecture.md             |
| feature behaviour, state machines         | docs/features/<feature>.md            |
| UI layout, spacing, component sizing      | docs/core/ui-density-guidelines.md    |

## Active tasks
- `docs/active/ootocv-frontend-rebuild.md` — OotoCV frontend rebuild ✅ (phases 1–8 complete; new pages live, old components removed)
- `docs/active/tailoring-ux-overhaul.md` — Tailoring UX overhaul 🟡 (background task + SSE + cancel + button fixes)
- `docs/active/gdoc-access-from-app.md` — GDoc auth flow hardening from UI (allow users to grant/revoke scope access)
- `docs/active/phase1-schema-foundation.md` — Phase 1 Cluster A: schema foundation 🟡
- `docs/active/ootocv-schema-adaptation.md` — OotoCV schema adaptation 🟡 (migrations 021–025 applied; API + workers + evaluator landed; frontend wiring next)

## Lessons log
See `docs/agent-lessons.md` for recurring mistake patterns and fixes.

## Architecture decisions
Recorded in `docs/decisions/`. ADR-0001 through ADR-0025 cover all major architectural shifts.
- ADR-0013: Application tracker uses `status_history JSONB` over a separate events table (single-user, bounded history, no join needed).
- ADR-0014: Tailoring endpoint converted from sync to background task + SSE + cancel (reuses existing infra from ADR-0009).
- ADR-0015: Google Docs export uses copy-and-fill path (copy base GDoc + replaceAllText) when `GOOGLE_BASE_RESUME_DOC_ID` is set, preserving formatting.
- ADR-0016: Settings page shows current resume indicator (name + timestamp + source GDoc link); `gdoc_url` column reused for source URL on master rows vs export URL on tailored rows.
- ADR-0017: Structured logging with stdlib only (structlog removed); correlation IDs via `ContextVar` in `backend/log_context.py`; set at HTTP middleware + APScheduler worker entry points.
- ADR-0018: GDoc export extended with `insertText` for additions (new skills/bullets); safety guards for apostrophe escaping and skills format mismatch.
- ADR-0019: Service kill switches in `system_config` (OpenRouter, Apify, Google Docs toggles); `require_service()` guard on routes, `is_service_enabled()` check in workers.
- ADR-0020: Async re-evaluation with per-stage SSE progress; `reeval_worker.py` wrapper steps through pipeline nodes emitting `save_task_status()` at each boundary.
- ADR-0021: Re-evaluation is read-only (stops after JD parsing, total=3 stages); frontend shows CTA ("Re-tailor →" / "Later") rather than silently re-tailoring.
- ADR-0022: Tailoring uses placeholder-row lifecycle (create at worker entry → CAS UPDATE at node_save → reaper sweeps stale rows after operator-tunable timeout).
- ADR-0023: Four-way verdict (`tailor | borderline | apply_direct | skip`) with pre-computed card lines (`top_strength` / `deciding_factor` / `kill_shot` / `red_flags`) on `job_evaluations`; legacy `apply` kept in the CHECK so historical rows stay valid (migration 022).
- ADR-0024: Per-stage pipeline mode (`pipeline_scrape_mode` / `pipeline_evaluate_mode` / `pipeline_tailor_mode` in `system_config`) toggles auto-vs-manual cron firing; distinct from kill switches (ADR-0019). Gated `_gated_*_worker` wrappers in `services/scheduler.py` enforce the mode.
- ADR-0025: `jobs.run_id` is a nullable FK to `pipeline_runs.id`, stamped only by `ScrapeWorker`. `runs_with_counts(limit_n)` RPC powers `GET /api/runs` with per-verdict aggregated counts.
