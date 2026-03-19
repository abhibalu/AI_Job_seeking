# services/CLAUDE.md

Load me when: task touches background workers, scheduler, Telegram, Google Docs, or Apify.

---

## Scheduler pattern (`services/scheduler.py`)

`get_scheduler()` returns a module-level singleton `BackgroundScheduler`.

Lifecycle (wired in `api/main.py`):
- `start_scheduler()` — called on FastAPI startup; registers ScrapeWorker + EvalWorker jobs
- `stop_scheduler()` — called on FastAPI shutdown; graceful shutdown (`wait=False`)

Trigger priority: cron expression (`SCRAPE_CRON` / `EVAL_CRON`) takes priority over interval
(`SCRAPE_INTERVAL_HOURS` / `EVAL_INTERVAL_HOURS`). Set `SCHEDULER_ENABLED=false` to disable
entirely (e.g. in CI).

Cron format: 5-field `'minute hour day month day_of_week'` (standard cron, not extended).

## Worker pattern

All workers follow this run-tracking wrapper:

```python
from services.pipeline_runs import start_run, finish_run
from services.telegram_notifier import notify_eval_complete, notify_pipeline_error
from backend.log_context import set_correlation_id, new_request_id

run_id = start_run("evaluate", metadata={...})
set_correlation_id(f"run:{run_id[:8]}")   # APScheduler threads do NOT inherit contextvars
try:
    # do work
    finish_run(run_id, status="completed", jobs_found=n, jobs_processed=m)
    notify_eval_complete(...)
except Exception as e:
    finish_run(run_id, status="failed", error_detail=str(e))
    notify_pipeline_error("WorkerName", str(e))
finally:
    set_correlation_id(None)
```

> **Why explicit?** APScheduler's `BackgroundScheduler` uses OS threads; `contextvars` are NOT
> copied into threads automatically. Always call `set_correlation_id` at the top of every
> APScheduler job function, and `set_correlation_id(None)` in `finally`.

## Logging conventions (ADR-0017)

- Inside `except` blocks: use `logger.exception(msg)` for errors, `logger.warning(msg, exc_info=True)` for warnings. Never bare `logger.error(f"... {e}")` — the stack trace is lost.
- Never use `print()` in worker functions. `print()` bypasses the JSON formatter and loses `correlation_id`, timestamps, and log rotation.

Files:
- `services/eval_worker.py` — evaluates pending jobs via LangGraph
- `services/scraper_worker.py` — triggers Apify LinkedIn scrape
- `services/pipeline_runs.py` — `start_run()` / `finish_run()` DB wrappers

## Telegram notifications

Never call the Telegram bot directly. Use the notifier functions:
- `notify_eval_complete(...)` — evaluation batch finished
- `notify_pipeline_error(worker_name, error_str)` — worker crashed
- `notify_high_match(company, title, score, job_id, action)` — high-score job found

Source: `services/telegram_notifier.py`.

## Google Docs integration (`services/google_docs.py`)

**Import**: Reuses `ResumeParserAgent` pipeline to parse raw GDoc text — no separate parsing logic.
Endpoint: `POST /api/resumes/import-gdoc` with `document_id`.

**Export**: Two paths controlled by `GOOGLE_BASE_RESUME_DOC_ID` env var (ADR-0015, ADR-0018):
- **Copy-and-fill** (when set): Copy base resume GDoc to company subfolder, apply two-phase update:
  1. `replaceAllText` for changed strings (rewording).
  2. `insertText` for additions — new skills lines or extra experience bullets (ADR-0018).
  Safety guards: skills format compatibility check (structured vs keywords → skip if mismatch);
  apostrophe escaping in Drive API queries.
- **Plain-text insert** (default): Create blank doc, insert resume as plain text. Works without a base template.

**OAuth error handling**: `get_credentials()` catches `RefreshError` when the cached token is
expired/revoked. On failure it deletes `google-token.json` and raises `ValueError` with an
actionable message. In server context, `run_local_server()` cannot open a browser — the user
must re-authenticate manually (delete token, run OAuth flow from terminal).

Env vars needed:
- `GOOGLE_DRIVE_FOLDER_ID` — target Drive folder for exports
- `GOOGLE_BASE_RESUME_DOC_ID` — optional; base resume GDoc ID for copy-and-fill exports

## Apify / Scraper

`APIFY_TOKEN`, `LINKEDIN_SEARCH_URLS` — configure in `.env`.
Scraper fetches raw JSON → `parse_raw_json()` → `map_job_record()` → Supabase.
`raw_json` field is preserved in DB for reprocessing without re-scraping.

---

## Go deeper

- Google Docs + GDrive import decisions → `docs/decisions/ADR-0005`
- Eval worker internals → `services/eval_worker.py`
- Scraper raw JSON mapping → `services/job_mapper.py`
