# Plan: OotoCV Phase 4 — Infrastructure

**Status:** 🟡 In Progress
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
- [ ] SSE authentication: session cookie passthrough or explicit token in query param?
- [ ] EventSource reconnect: does the `useSSE` hook use native auto-reconnect or manual?
- [ ] auto_send modal: where does it live — `Settings.tsx` inline or a separate `AutoSendModal.tsx`?

## Out of Scope
- Cover letter agent (phase 3 dependency, not infrastructure)
- Application tracker (phase 5)

---

## Implementation Checklist

### Backend (agents/, api/, supabase_db/)
- [ ] `api/routes/events.py` (new): `GET /events/stream` — SSE endpoint, session-scoped
- [ ] SSE event types: `event: progress` (run progress, feeds TailoringStrip) + `event: run_complete` (cron completion, feeds announcement banner)
- [ ] Remove or gate `BackgroundTasks` polling endpoint once SSE is live

### Frontend (glassresumatch-ai/)
- [ ] `hooks/useSSE.ts` (new): single `EventSource` instance, reconnects on disconnect, exposes `progress` and `run_complete` event streams
- [ ] `TailoringStrip.tsx`: subscribe to `progress` events from `useSSE` instead of polling
- [ ] Announcement banner: subscribe to `run_complete` events from `useSSE`
- [ ] Delete polling logic from `apiClient.ts` (`GET /api/tasks/{task_id}` retry loop)
- [ ] Error rollback — Skip action: card returns to full opacity, restores original list position
- [ ] Error rollback — Approve action: card unmasks, badge count re-increments, `tailoringStatus` reverts to pre-approve state
- [ ] Error rollback — Apply Direct action: button returns to `Apply with [base|tailored] CV →` state
- [ ] All rollbacks: `toast.error("Couldn't save — tap to retry")` with retry callback in toast
- [ ] Establish rollback pattern once in shared action handler / `App.tsx`, apply consistently
- [ ] `AutoSendModal.tsx` (new) or inline in `Settings.tsx`: shown when slider moves above 0
- [ ] Modal copy: "CVs will be sent to employers without your review for jobs scoring X/4 or above. Confirm to enable."
- [ ] On modal confirm: save threshold + show amber header indicator "Auto-send ON · X+"
- [ ] On modal cancel: slider returns to 0, setting not saved
- [ ] `TypewriterWaitState.tsx`: read `sessionStorage.getItem('ootocv_hasLoaded')` on mount; write on every ref update

---

## Progress Log
<!-- Append-only. Format: `- YYYY-MM-DD: what done, surprises, what changed` -->
- 2026-03-19: Phase 4 plan created. SSE replaces polling (ADR-0009). auto_send modal required (ADR-0012).
