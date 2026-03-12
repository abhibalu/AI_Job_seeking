# ADR-0001: Remove SQLite Fallback

**Date:** 2026-03-10
**Status:** Accepted

## Problem

The database layer maintained dual SQLite/Supabase backends, controlled by a `USE_SUPABASE` toggle. Every DB function contained if/else branches to handle both paths. SQLite was never active in practice — `USE_SUPABASE=true` had been set since day one — resulting in ~400 lines of dead code that doubled the maintenance burden of every database change.

## Analysis

- Verified no SQLite `.db` files exist on disk
- All runtime data flows through Supabase exclusively
- The `USE_SUPABASE` toggle and `EVAL_DB_PATH` setting were never set to their SQLite-enabling values
- The dual-path pattern made DB functions harder to read and test

## Decision

Remove all SQLite code, the `USE_SUPABASE` toggle, and the `EVAL_DB_PATH` setting. Add startup validation that Supabase credentials (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`) are present, failing fast with a clear error instead of silently falling back to a nonexistent SQLite file.

## Consequences

- 10 files changed, ~550 lines removed
- Missing Supabase credentials now fail fast at startup
- Single code path simplifies all future DB work
- SQLite and `aiosqlite` dependencies can be removed if no other code uses them
