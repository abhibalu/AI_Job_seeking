# ADR-0017: Structured Logging with Correlation IDs (stdlib, no structlog)

**Date:** 2026-03-19
**Status:** Accepted

---

## Context

An audit of the codebase identified four logging problems:

1. **Silent failures** — ~15 background task `except` blocks called `print()` or omitted `exc_info`, discarding stack traces.
2. **Zero traceability** — no request or run ID threaded through log lines, making it impossible to match an HTTP log entry to its downstream agent/DB calls.
3. **Missing observability** — LLM call durations, per-node graph timings, and routing decisions were not logged.
4. **Dead dependency** — `structlog>=24.0.0` was in `requirements.txt` but unused; all code used stdlib `logging`.

---

## Decision

### Keep stdlib logging; remove structlog

The existing `JSONFormatter` in `backend/logging.py` already produces structured JSON. Migrating to `structlog` would require touching ~26 import sites for no meaningful gain in a single-user app.

**Outcome:** `structlog` removed from `requirements.txt`.

### Add correlation IDs via `ContextVar`

New file `backend/log_context.py` provides:
- `_correlation_id: ContextVar[str | None]` — one value per asyncio task / OS thread
- `set_correlation_id(cid)` / `get_correlation_id()`
- `new_request_id()` — 8-char UUID prefix
- `CorrelationFilter` — `logging.Filter` subclass that injects `correlation_id` into every `LogRecord`

`setup_logging()` in `backend/logging.py` wires the filter onto all handlers after `dictConfig`. `JSONFormatter` reads `record.correlation_id` and writes it as a top-level JSON key on every line.

### Set correlation IDs at system entry points

| Entry point | Correlation ID format | Set/cleared in |
|---|---|---|
| HTTP request | `X-Request-ID` header or `new_request_id()` | `RequestLoggingMiddleware.dispatch()` |
| Eval worker (APScheduler thread) | `run:{run_id[:8]}` | `run_eval_worker()` entry + `finally` |
| Scrape worker (APScheduler thread) | `scrape:{run_id[:8]}` | `run_scrape_worker()` entry + end |

> **Why explicit in workers?** APScheduler's `BackgroundScheduler` runs in its own thread pool and does NOT copy `contextvars`. FastAPI background tasks and `run_in_threadpool` do propagate context automatically.

### Fix all silent failures

- Replace all `print()` calls in background tasks with `logger` calls
- Use `logger.exception(msg)` (≡ `logger.error(msg, exc_info=True)`) inside `except` blocks for errors
- Use `logger.warning(msg, exc_info=True)` inside `except` blocks for warnings
- `X-Request-ID` echoed back in HTTP responses

### Add timing observability

- **LLM calls** (`agents/base.py`): `time.perf_counter()` wraps each SDK call; `duration_ms`, `prompt_tokens`, `completion_tokens` added to the `logger.info` on success.
- **Subgraph nodes** (`agents/tailoring_subgraph.py`): `_timed_node(name, job_id)` context manager wraps each of the five node bodies; emits `[SubGraph] <node> complete` with `duration_ms`.

### Add routing visibility

- `route_after_evaluation()` logs `job_id`, `route`, `score`, `company`, `title` on every call.
- `route_after_parse()` logs success or error.
- `route_validate()` and `route_critique()` in the tailoring subgraph log every routing decision.
- `node_notify_apply` / `node_notify_tailored` capture and log the `ok` bool from the Telegram notifier.

---

## Consequences

- Every log line in production now carries `correlation_id`, making it straightforward to `grep` all log lines for a single HTTP request or worker run.
- LLM call latency and token usage are visible in structured logs without a Langfuse dashboard.
- `structlog` is no longer installed, removing a dependency that was never used.
- `backend/log_context.py` is the single place to add any future span/trace enrichment (e.g., `job_id` context var).
