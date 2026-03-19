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

## Lessons log
See `docs/agent-lessons.md` for recurring mistake patterns and fixes.

## Architecture decisions
Recorded in `docs/decisions/`. ADR-0001 through ADR-0015 cover all major architectural shifts.
- ADR-0013: Application tracker uses `status_history JSONB` over a separate events table (single-user, bounded history, no join needed).
- ADR-0014: Tailoring endpoint converted from sync to background task + SSE + cancel (reuses existing infra from ADR-0009).
- ADR-0015: Google Docs export uses copy-and-fill path (copy base GDoc + replaceAllText) when `GOOGLE_BASE_RESUME_DOC_ID` is set, preserving formatting.
