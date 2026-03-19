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

## Active tasks
- **`docs/active/ootocv-frontend-rebuild.md`** — Full frontend rebuild to match OotoCV spec (8 phases: deps → shell → feed → detail → review → tracker → settings → polish)
- `docs/active/ootocv-phase1-foundation.md` — Data model (tailoringStatus, Change fields, cover_letter, cron_tz) ✅
- `docs/active/ootocv-phase2-feed.md` — Feed + card (⋯ quick actions, conditional button copy, sort/filter rules) ✅
- `docs/active/ootocv-phase3-tailoring-review.md` — Change-level review UI (Accept/Reject/Keep original, bulk accept, CL textarea) ✅
- `docs/active/ootocv-phase4-infrastructure.md` — SSE, error rollback, auto_send modal, typewriter sessionStorage ✅
- `docs/active/ootocv-phase5-tracker-and-onboarding.md` — Tracker link-back, timeline dots, onboarding Step 0 ✅

## Lessons log
See `docs/agent-lessons.md` for recurring mistake patterns and fixes.

## Architecture decisions
Recorded in `docs/decisions/`. ADR-0001 through ADR-0013 cover all major architectural shifts.
- ADR-0013: Application tracker uses `status_history JSONB` over a separate events table (single-user, bounded history, no join needed).
