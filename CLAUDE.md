# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TailorAI is an autonomous job-seeking agent that discovers, evaluates, and tailors resumes to job descriptions using a multi-agent LLM pipeline. It combines a React frontend, FastAPI backend, LangGraph orchestration, and Supabase (PostgreSQL).

## Commands

### Backend
```bash
# Install dependencies
pip install -r requirements.txt

# Run API server (port 8000)
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest

# Run a single test
pytest test/test_file.py::test_function -v

# Lint & format
ruff check .
ruff format .
```

### Frontend
```bash
cd glassresumatch-ai
npm install
npm run dev    # Dev server on port 3000
npm run build  # Production build
```

### Infrastructure
```bash
docker-compose -f docker-compose.langfuse.yml up -d  # Langfuse (observability)
```

## Architecture

### Multi-Agent Pipeline (LangGraph)

The core pipeline (`agents/pipeline_graph.py`) routes jobs through evaluation → parsing → tailoring:

```
START → Evaluate (JobEvaluatorAgent)
        ├→ score too low: Skip → END
        ├→ high match: Notify "Apply" → END
        └→ needs tailoring: Parse (JDParserAgent) → Tailoring SubGraph → Notify → END
```

The tailoring subgraph (`agents/tailoring_subgraph.py`) implements an Actor-Critic loop:

```
Draft (ResumeTailorAgent) → Critique (ResumeCriticAgent)
        ├→ no issues: Save → END
        ├→ issues & revision_count < 2: → back to Draft
        └→ max revisions reached: force Save → END
```

All agents extend `BaseAgent` (`agents/base.py`), which wraps the OpenAI SDK pointed at OpenRouter and integrates Langfuse tracing. Agent system prompts live in `agent_prompts/`.

### Data Flow

1. **Scraper** (Apify → LinkedIn) → `parse_raw_json()` → `map_job_record()` → **Supabase** (with `raw_json` preserved for reprocessing)
2. Frontend reads from Supabase via FastAPI endpoints; tailoring writes back to Supabase

### Key Directories

- `agents/` — LangGraph graphs, agent classes, DB layer, checkpointer
- `api/` — FastAPI app, routes, Pydantic schemas, middleware
- `glassresumatch-ai/` — React + TypeScript + TailwindCSS frontend
- `services/` — Background workers (scraper, eval), scheduler, job mapper, Google Docs export, Telegram notifications
- `agent_prompts/` — System prompts and approved skills dictionary
- `backend/` — Settings (Pydantic), logging config
- `docs/` — Layered documentation (logic → architecture → implementation)

### Database

Backend: Supabase (PostgreSQL). LangGraph state is checkpointed via `agents/supabase_checkpointer.py`.

### API Structure

Routes are in `api/routes/`. Key endpoints:
- `GET/POST /api/jobs` — Job CRUD and search
- `GET /api/evaluations` — Evaluation results with filtering
- `GET/POST /api/resumes` — Master resume, tailored resumes, export
- `POST /api/resumes/tailor` — Triggers tailoring subgraph (background task)
- `POST /api/resumes/export-gdoc` — Export to Google Docs
- `GET /api/tasks/{task_id}` — Background task status tracking

### Frontend

React 19 + TypeScript + Vite. The main app (`App.tsx`) renders a job list with evaluation details. `TailorReview.tsx` provides side-by-side resume comparison and export. API calls go through `services/apiClient.ts` (base URL: `localhost:8000`).

## Environment

Key env vars (configured in `.env`, loaded via `backend/settings.py`):
- `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` — LLM access
- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` — Database (required)
- `APIFY_TOKEN`, `LINKEDIN_SEARCH_URLS` — Job scraping
- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` — Observability
- `GOOGLE_DRIVE_FOLDER_ID`, `BASE_RESUME` — Google Docs integration
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` — Notifications

## Ports

- Frontend: 3000
- Backend API: 8000
- Langfuse: 3010

## Decision Log

Architecture decisions are recorded in `docs/decisions/`. Key decisions:
- [ADR-0001](docs/decisions/0001-remove-sqlite-fallback.md) — Removed SQLite fallback, consolidated on Supabase
- [ADR-0002](docs/decisions/0002-remove-lakehouse-subsystem.md) — Removed lakehouse subsystem (MinIO, Delta Lake, Bronze/Silver/Gold)
- [ADR-0003](docs/decisions/0003-fix-eval-filter-latency.md) — Fixed eval filter latency with database view (eliminated double round-trip)
- [ADR-0004](docs/decisions/0004-tailoring-quality-phase1.md) — Tailoring quality Phase 1: ATS bug fix, temperatures, structural validation
