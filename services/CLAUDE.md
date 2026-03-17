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

run_id = start_run("evaluate", metadata={...})
try:
    # do work
    finish_run(run_id, status="completed", jobs_found=n, jobs_processed=m)
    notify_eval_complete(...)
except Exception as e:
    finish_run(run_id, status="failed", error_detail=str(e))
    notify_pipeline_error("WorkerName", str(e))
```

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

Import: reuses `ResumeParserAgent` pipeline to parse raw GDoc text — no separate parsing logic.
Export: formats tailored resume JSON back to GDoc and uploads to Drive.

Env vars needed:
- `GOOGLE_DRIVE_FOLDER_ID` — target Drive folder for exports
- `BASE_RESUME` — document ID for the base resume GDoc import

## Apify / Scraper

`APIFY_TOKEN`, `LINKEDIN_SEARCH_URLS` — configure in `.env`.
Scraper fetches raw JSON → `parse_raw_json()` → `map_job_record()` → Supabase.
`raw_json` field is preserved in DB for reprocessing without re-scraping.

---

## Go deeper

- Google Docs + GDrive import decisions → `docs/decisions/ADR-0005`
- Eval worker internals → `services/eval_worker.py`
- Scraper raw JSON mapping → `services/job_mapper.py`
