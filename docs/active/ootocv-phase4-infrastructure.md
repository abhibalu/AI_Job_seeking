# Plan: OotoCV Phase 4 — Infrastructure

**Status:** ✅ Complete
**Created:** 2026-03-19
**Branch:** feature/claude-skills

## Goal
Replace polling with SSE, implement consistent error rollback across all optimistic updates, add the auto_send consent modal, and persist the typewriter hasLoaded state. Phase 4 is complete when: a single SSE connection drives all server push, every action has a defined rollback, auto_send requires modal confirmation, and typewriter doesn't re-run on page refresh.

## Decisions Made
- SSE exclusively for all server→client push — see ADR-0009
- Single endpoint `GET /events/stream`, session-scoped, typed events: `progress` + `run_complete`
- Existing polling code in `apiClient.ts` (`GET /api/tasks/{task_id}`) deleted when SSE is live
- Error rollback defined per action before implementing (see checklist) — not invented per-engineer
- auto_send modal required before slider saves above 0 — see ADR-0012
- `sessionStorage` (not `localStorage`) for typewriter hasLoaded — session-scoped is correct

## Open Questions
- [x] SSE authentication: no auth in phase 4 (no sessions yet); `task_id` query param scopes the stream.
- [x] EventSource reconnect: native auto-reconnect (browser default); `useSSE` does NOT close on `onerror`.
- [x] auto_send modal: separate `AutoSendModal.tsx` (cleaner — inline in Settings would couple concerns).

## Out of Scope
- Cover letter agent (phase 3 dependency, not infrastructure)
- Application tracker (phase 5)

---

## Implementation Checklist

### Backend (agents/, api/, supabase_db/)
- [x] `api/routes/events.py` (new): `GET /events/stream` — SSE endpoint, task_id-scoped, 1s poll interval, 15s keepalive comment
- [x] SSE event types: `event: progress` + `event: run_complete` (closes stream on terminal)
- [x] `BackgroundTasks` polling remains for non-SSE callers; `getTaskStatus` endpoint kept

### Frontend (glassresumatch-ai/)
- [x] `hooks/useSSE.ts` (new): single `EventSource` per taskId, stable handler ref, native auto-reconnect, closes on `run_complete`
- [x] `BatchEvaluate.tsx`: replaced `setInterval` polling with `useSSE` (onProgress + onRunComplete)
- [ ] `TailoringStrip.tsx`: not yet in TailorAI codebase — deferred (component doesn't exist yet)
- [ ] Announcement banner: deferred (no run_complete UI surface yet)
- [x] Polling removed from `BatchEvaluate.tsx`; `getTaskStatus` import dropped from that file
- [x] Error rollback — Apply Direct: `unmarkActioned(id)` added to `useJobs` for rollback; `Toast.onRetry` prop added
- [x] Error rollback pattern: `markActioned` (optimistic) → `patchJobAction` → on fail: `unmarkActioned` + toast with retry
- [x] `AutoSendModal.tsx` (new): explicit confirmation before threshold > 0 saves; "Cancel — keep at 0" / "Confirm — enable auto-send" copy per ADR-0012
- [x] `TypewriterWaitState.tsx` (new): sequential typewriter with `sessionStorage` key `ootocv_tw_${sessionKey}`; skips on repeat visits; stable `onCompleteRef`

---

## Progress Log
<!-- Append-only. Format: `- YYYY-MM-DD: what done, surprises, what changed` -->
- 2026-03-19: Phase 4 plan created. SSE replaces polling (ADR-0009). auto_send modal required (ADR-0012).
