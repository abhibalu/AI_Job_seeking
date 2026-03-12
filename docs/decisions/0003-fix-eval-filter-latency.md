# ADR-0003: Fix Evaluation Filter Latency with Database View

**Date:** 2026-03-12
**Status:** Accepted

## Problem

Filtering jobs by evaluation status ("Evaluated" / "Not Evaluated") in the UI was unacceptably slow. The backend made two Supabase round-trips per request: first fetching ALL evaluated job IDs, then sending them back in a massive `IN(...)` / `NOT IN(...)` clause. With 5,000 evaluated jobs, this meant ~180KB of UUID text per query, PostgreSQL falling back to sequential scans, and the eval worker overfetching 3x then filtering in Python.

Three locations exhibited this pattern:
- `api/routes/jobs.py` — `list_jobs` endpoint
- `api/routes/jobs.py` — `get_job_stats` endpoint
- `services/eval_worker.py` — `_get_unevaluated_jobs` function

## Analysis

Four approaches were evaluated:

| Option | Approach | Verdict |
|--------|----------|---------|
| A. Denormalized Trigger | `is_evaluated` boolean on `jobs` + trigger | Adds hidden DB complexity + sync risk. Counter to project direction of removing hidden machinery. |
| B. Database View | View with computed `is_evaluated` via EXISTS | Clean, always consistent, zero maintenance. Leverages existing `idx_evaluations_job_id` index. |
| C. Inner Join Syntax | Supabase `!inner` / `!left` join | Incomplete — "not evaluated" path is fragile through the Python SDK. |
| D. RPC Function | PostgreSQL function via `client.rpc()` | Heavier than needed. Replaces familiar query builder with opaque calls. |

Performance at current scale (~5K jobs): Option A ~0.1ms, Option B ~1-2ms, current approach ~100-500ms. The difference between A and B is invisible; both are orders of magnitude better than the status quo.

## Decision

Option B — Create a `v_jobs_enriched` database view that adds a computed `is_evaluated` boolean column using EXISTS subquery. Replace all three double-round-trip locations with single queries against the view.

Rationale: `is_evaluated` is a *derived* state, not a core property. A view keeps it computed from the source of truth (`job_evaluations` table) with zero sync risk. Supabase/PostgREST exposes views as queryable tables, so existing `.eq()`, `.range()`, `.order()` patterns work unchanged.

## Consequences

- 3 files changed, ~30 lines removed, ~10 lines added
- New migration: `006_jobs_evaluated_view.sql`
- Single round-trip per filter request (was 2)
- No more ID payload bloat or client-side filtering
- Eval worker no longer overfetches 3x
- Dummy UUID hack in `get_job_stats` eliminated
- No new dependencies or infrastructure
