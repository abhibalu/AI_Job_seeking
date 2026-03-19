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

Status enum (in order): `queued` → `running` → `completed` / `failed` / `cancelled`

Worker function updates status via `save_task_status(task_id, "running", {...})` as it progresses.

**Cancellation**: `POST /api/tasks/{task_id}/cancel` sets status to `"cancelled"`. Workers check
`get_task_status(task_id)` at node boundaries and exit early if cancelled. At most one in-flight
LLM call is wasted.

**Push transport (ADR-0009):** Frontend streams progress via SSE (`GET /api/events/stream?task_id=...`)
rather than polling. `GET /api/tasks/{task_id}` remains for non-SSE callers but is no longer used
by the main UI.

## SSE endpoint (`api/routes/events.py`)

`GET /api/events/stream?task_id=<id>` — `StreamingResponse` with `text/event-stream`.

- Polls `get_task_status()` every 1s; emits `event: progress` while running.
- Emits `event: run_complete` and closes the generator on terminal status (`completed` / `failed` / `cancelled`).
- Sends `: keepalive` comment every 15s to prevent proxy/browser timeouts.
- Headers: `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`.
- No auth in phase 4 — `task_id` query param scopes the stream.

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

| Method | Path                                        | Purpose                                        |
|--------|---------------------------------------------|------------------------------------------------|
| GET/POST | `/api/jobs`                               | Job CRUD and search                            |
| GET    | `/api/evaluations`                          | Evaluation results with filtering              |
| GET/POST | `/api/resumes`                            | Master resume management                       |
| POST   | `/api/resumes/tailor/{job_id}`              | Background task: tailoring pipeline (returns `task_id`) |
| POST   | `/api/resumes/export-gdoc/{id}`             | Export to Google Docs                          |
| GET    | `/api/resumes/{resume_id}/changes`          | Per-change review records (OotoCV ADR-0010)    |
| PATCH  | `/api/resumes/{resume_id}/changes/{id}`     | Accept / Reject / Keep original on one change  |
| PATCH  | `/api/resumes/{resume_id}/changes/bulk`     | Bulk action on remaining or all changes        |
| PATCH  | `/api/resumes/{resume_id}/cover_letter`     | Save user-edited cover letter (ADR-0011)       |
| GET    | `/api/events/stream`                        | SSE progress stream for a task (ADR-0009)      |
| GET    | `/api/tasks/{task_id}`                      | Background task status (non-SSE callers)       |
| POST   | `/api/tasks/{task_id}/cancel`               | Cancel a running task (sets status=cancelled)  |
| GET    | `/api/applications`                         | List applications (tracker), newest first      |
| POST   | `/api/applications`                         | Record a new application (called on Apply)     |
| PATCH  | `/api/applications/{id}/status`             | Update status, append to status_history        |
| GET    | `/api/scheduler`                            | Scheduler job status                           |

## OotoCV schema additions (`api/schemas.py`)

New schemas added for OotoCV Phase 1:
- `ResumeChange` — per-change review record (fields: `original_text`, `tailored_text`, `accepted_text`, `review_action`, `confidence`)
- `ResumeChangeActionRequest` — body for single-change PATCH (`action: accept | reject | keep_original`)
- `ResumeChangeBulkActionRequest` — body for bulk PATCH (`action`, `scope: remaining | all`)
- `SystemConfigItem` / `CronConfigRequest` — system config read/write

`JobBase` includes `tailoring_status` (inherited by `JobDetail`). `JobDetail` adds `cover_letter`.
`tailoring_status` is surfaced via `v_jobs_enriched` view (migration 014) — both `list_jobs` and
`get_job` query this view, so the field is present on list and detail responses.

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
