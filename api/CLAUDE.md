# api/CLAUDE.md

Load me when: task touches `api/`, `routes/`, Pydantic schemas, or background tasks.

---

## Route URL pattern

`/api/{resource}/{id?}/{action?}` — one file per resource in `api/routes/`.

Registered in `api/main.py` via `app.include_router(...)`.

## Function naming in routes

| Pattern         | Example                         |
|-----------------|---------------------------------|
| `list_resource` | `list_jobs()`                   |
| `get_resource`  | `get_job(job_id)`               |
| `action_resource` | `evaluate_job(job_id)`, `batch_evaluate()` |

## Schema conventions (`api/schemas.py`)

All Pydantic schemas live in `api/schemas.py`. Naming:
- `{Resource}Result` — read response (e.g. `JobResult`)
- `{Resource}Stats` — aggregate stats (e.g. `EvaluationStats`)
- `{Resource}Request` — write body (e.g. `BatchRequest`)
- `{Resource}Data` — embedded sub-object

## Background task pattern (full sequence)

```python
import uuid
from agents.database import save_task_status

task_id = str(uuid.uuid4())
save_task_status(task_id, "queued", {"completed": 0, "total": n})
background_tasks.add_task(my_worker_fn, task_id, ...other_args)
return {"message": "...", "task_id": task_id}
```

Status enum (in order): `queued` → `running` → `completed` / `failed`

Worker function updates status via `save_task_status(task_id, "running", {...})` as it progresses.
Frontend polls `GET /api/tasks/{task_id}` to track progress.

## Pagination

- Query params: `skip=0`, `limit=20`
- Total count in response header: `X-Total-Count`
- Header is exposed via CORS `expose_headers=["X-Total-Count"]` (already wired in `main.py`)
- Frontend must use a manual `fetch()` call (not `apiClient.request`) to read response headers

## Middleware (already wired in `main.py` — do not re-add)

- `CORSMiddleware` — `allow_origins=["*"]`, exposes `X-Total-Count`
- `LangfuseMiddleware` — request-level tracing
- `RequestLoggingMiddleware` — structured request logging

## Adding a new route

1. Add Pydantic schema(s) to `api/schemas.py`.
2. Create handler(s) in `api/routes/{resource}.py`.
3. Register router in `api/main.py`: `app.include_router(resource.router, prefix="/api/{resource}", tags=[...])`.

## Key routes reference

| Method | Path                            | Purpose                            |
|--------|---------------------------------|------------------------------------|
| GET/POST | `/api/jobs`                   | Job CRUD and search                |
| GET    | `/api/evaluations`              | Evaluation results with filtering  |
| GET/POST | `/api/resumes`                | Master resume management           |
| POST   | `/api/resumes/tailor/{job_id}`  | Triggers tailoring subgraph        |
| POST   | `/api/resumes/export-gdoc/{id}` | Export to Google Docs              |
| GET    | `/api/tasks/{task_id}`          | Background task status polling     |
| GET    | `/api/scheduler`                | Scheduler job status               |

## Environment variables for API
- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` — required for all DB operations
- `OPENROUTER_API_KEY` — required for evaluation/tailoring routes
- `GOOGLE_DRIVE_FOLDER_ID` — required for GDoc export route

---

## Go deeper

- Full architecture map (import rules, data flow) → `docs/core/architecture.md`
- Background task DB functions → `agents/database.py` (`save_task_status`, `get_task_status_db`)
- Eval filter latency fix (DB view) → `docs/decisions/ADR-0003`
- Tailoring route internals → `api/routes/resumes.py`
