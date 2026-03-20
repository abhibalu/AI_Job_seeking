# ADR-0013: Application tracker uses status_history JSONB, not a separate events table

**Date:** 2026-03-19
**Status:** Accepted

## Context

OotoCV phase 5 adds an application tracker so users can see every job they applied to and
follow its progress (`applied → replied → interview → rejected`). Two storage options:

1. **`application_events` table** — normalised event rows, one row per status transition.
   Queryable by event type, easy to aggregate, scales well if many events per application.
2. **`status_history JSONB` column** — append-only JSON array `[{status, timestamp}]` on
   the `applications` row. Single row per application, no join required to read history.

## Decision

Use `status_history JSONB` on the `applications` table (option 2).

## Reasons

- Single user, single-device app. History depth per application is bounded (4–5 statuses max).
- Reading tracker cards requires no join — one `SELECT *` returns everything needed.
- The append pattern (`history.append({...})`) is trivial in Python; no ORM needed.
- A separate events table adds DDL, RLS policies, and FK complexity for negligible gain at v1 scale.

## Consequences

- `status_history` is not independently queryable (e.g. "all apps that reached interview stage
  before date X"). If such queries become needed, migrate to `application_events` table then.
- PATCH `/api/applications/:id/status` reads the current `status_history`, appends, and writes
  back. This is a read-modify-write — acceptable for a single-user low-concurrency context.
