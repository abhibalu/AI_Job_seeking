# ADR-0014: Tailoring Background Task + Cancel

**Date:** 2026-03-19
**Status:** Accepted

## Context

`POST /api/resumes/tailor/{job_id}` ran the full LangGraph tailoring subgraph synchronously —
the HTTP request blocked for 15-60s while 3-4 LLM calls executed sequentially. This caused:

1. No real progress feedback (TailoringStrip showed cosmetic animation, not actual pipeline state).
2. No way to cancel — the "Cancel" button cleared frontend state but the backend kept running,
   burning all remaining LLM credits.
3. No concurrency guard — clicking multiple cards fired parallel pipelines, each wasting credits.
4. Button label "Tailor & Approve" was misleading (approval is a separate step on TailoringReview).

The background task + SSE infrastructure already existed (proven in batch evaluation flow,
ADR-0009) but was orphaned for tailoring — `tailoringTaskId` was never set.

## Decision

1. **Convert to background task**: Endpoint creates a `task_id`, queues `run_tailoring_worker`
   via `BackgroundTasks`, and returns `{ task_id, message }` immediately. The worker runs
   individual subgraph node functions in sequence with `save_task_status()` at each boundary.

2. **Cancellation via status flag**: `POST /api/tasks/{task_id}/cancel` sets task status to
   `"cancelled"`. Worker checks `get_task_status()` before each node — if cancelled, exits
   early. SSE stream emits `run_complete` with `status: "cancelled"` and closes.

3. **Frontend guards**: One tailoring run at a time (App-level `tailoringJob` check).
   Dashboard card buttons disabled during active tailoring. `processing` status prevents
   duplicate runs for same job.

4. **Honest labels**: "Tailor & Approve" → "Tailor CV", "Tailor Anyway" → "Tailor CV".

## Consequences

- Worst-case cancel cost: one in-flight LLM call (vs. full 3-4 call pipeline before).
- TailoringStrip now shows real stage progress (planning/drafting/critiquing/saving) from SSE.
- No new endpoints beyond the cancel route — reuses existing SSE + task infrastructure.
- Worker bypasses `subgraph.invoke()` to call node functions directly — if subgraph routing
  logic changes, the worker must be updated in parallel.
