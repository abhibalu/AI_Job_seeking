# ADR-0019: Service Kill Switches

**Status:** Accepted
**Date:** 2026-03-20

## Context

External API dependencies (OpenRouter, Apify, Google Docs) can experience outages or rate limits. Scraper + evaluator workers need to gracefully degrade without blocking the entire application. Currently, there is no way to disable services at runtime without code changes or container restarts.

## Decision

Introduce **service kill switches** stored in `system_config` table:

```python
SERVICE_KEYS = {
    "openrouter": "service_openrouter_enabled",      # LLM evaluations & tailoring
    "apify": "service_apify_enabled",                # LinkedIn scraping
    "google_docs": "service_google_docs_enabled",    # Resume exports
}
```

**Backend guard:** `backend/service_guard.py` exports two functions:
- `require_service(name)` — raises `503` if disabled (for HTTP routes)
- `is_service_enabled(name)` — returns bool (for background workers)

**API endpoint:** `PATCH /api/settings/services` allows toggling via UI.

## Rationale

1. **Fail-fast on routes**: `require_service("openrouter")` at the top of evaluation/tailoring routes prevents half-executed API calls.
2. **Graceful cron skipping**: Workers check `is_service_enabled()` and skip gracefully rather than retrying failed API calls 50 times.
3. **Runtime toggles**: No restart or code change needed — ops can disable a flaky service via Settings tab.
4. **Single source of truth**: `system_config` table already holds cron schedule & auto-send threshold; service toggles fit naturally.

## Consequences

- All external API calls must be guarded with `require_service()` at the route/node entry point.
- Default state is **enabled** (missing key = true). This ensures backward compatibility.
- Database schema: no migrations needed — `system_config` is key-value.
- Settings UI requires a new "Service Status" section showing toggle switches.

## Alternatives considered

1. **Environment variables** — would require container restart; rejected.
2. **Per-service circuit breaker** — detects failures automatically; too much complexity for current load (single-user, no extreme scale).
3. **Graceful degradation without toggles** — without explicit control, users can't fix a downed service quickly.
