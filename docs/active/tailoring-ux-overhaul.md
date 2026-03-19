# Plan: Tailoring UX Overhaul

**Status:** 🟡 In Progress
**Created:** 2026-03-19
**Branch:** feature/ootocv-build

## Goal

Convert the synchronous "Tailor & Approve" flow into a background-task + SSE architecture (reusing
the existing batch-evaluation pattern), add real cancel support that kills backend work, fix button
labels, and add concurrency/double-click guards. When done, one click fires a non-blocking pipeline,
the TailoringStrip shows real stage progress, and "Stop Tailoring" kills the run at the next node
boundary — saving LLM credits.

## Decisions Made

- **Reuse existing infra**: `save_task_status` / `get_task_status` + `/api/events/stream` SSE + `useSSE` hook — no new transport layer
- **Cancel via status flag**: worker checks task status at each node boundary; `cancelled` status = early exit. No thread/process kill needed.
- **Cancel endpoint**: `POST /api/tasks/{task_id}/cancel` (not DELETE — the task record is kept for debugging)
- **Button rename**: "Tailor & Approve →" → "Tailor CV →" (approval is a separate step on TailoringReview)
- **Concurrency**: one tailoring run at a time; App-level guard + Dashboard button disable

## Open Questions
- [ ] Should we show a toast on cancel confirming credits saved? (nice-to-have, skip for now)

## Out of Scope
- Batch tailoring (tailor multiple jobs at once)
- Resume caching / dedup (if same job is tailored twice)
- Retry on partial failure (e.g., critic failed but draft is usable)

---

## Implementation Checklist

### Phase 1 — Backend: background task + cancel

- [ ] **1a. Convert `POST /api/resumes/tailor/{job_id}` to background task pattern**
  - Create `task_id` via `save_task_status(task_id, "queued", {"completed": 0, "total": 4, "stage": "queued"})`
  - Move subgraph invocation into a worker function `run_tailoring(task_id, job_id, base_resume, jd_context, approved_skills)`
  - Fire via `background_tasks.add_task(run_tailoring, ...)`
  - Return `{"task_id": task_id, "message": "Tailoring started"}` immediately
  - Worker updates progress at each node boundary:
    - Before plan: `save_task_status(task_id, "running", {"completed": 0, "total": 4, "stage": "planning"})`
    - After plan: `{"completed": 1, "total": 4, "stage": "drafting"}`
    - After draft+validate: `{"completed": 2, "total": 4, "stage": "critiquing"}`
    - After critique: `{"completed": 3, "total": 4, "stage": "saving"}`
    - After save: `save_task_status(task_id, "completed", {"completed": 4, "total": 4, "stage": "done", "resume_id": record_id})`
  - On error: `save_task_status(task_id, "failed", {...}, error=str(e))`

- [ ] **1b. Add cancel endpoint `POST /api/tasks/{task_id}/cancel`**
  - In `api/routes/tasks.py`: set task status to `"cancelled"` via `save_task_status(task_id, "cancelled", ...)`
  - Return `{"status": "cancelled"}`

- [ ] **1c. Add cancellation checks in the tailoring worker**
  - Helper: `def is_task_cancelled(task_id): return get_task_status(task_id).get("status") == "cancelled"`
  - Check before each node call (plan, draft, critique, save). If cancelled, log + return early.
  - On cancel: set `tailoring_status` on the job back to `not_started` (so it can be re-triggered)

- [ ] **1d. Handle `cancelled` status in SSE stream (`api/routes/events.py`)**
  - Add `cancelled` as a terminal status alongside `completed` and `failed`
  - Emit `event: run_complete` with `status: "cancelled"` and close

- [ ] **1e. Guard against duplicate tailoring for same job**
  - In `tailor_resume` endpoint: if `tailoring_status == 'processing'`, return existing `task_id` from a lookup (or 409 Conflict)

### Phase 2 — Frontend: wire SSE, fix labels, add guards

- [ ] **2a. Update `apiClient.ts`**
  - `tailorResume(jobId)` now returns `{ task_id, message }` (not the full TailoredResume)
  - Add `cancelTask(taskId: string)` → `POST /api/tasks/{taskId}/cancel`

- [ ] **2b. Rewire `handleTailorStart` in `App.tsx`**
  - Call `tailorResume(jobId)` → get `task_id`
  - `setTailoringJob(job)` + `setTailoringTaskId(task_id)` — now SSE hook activates
  - Remove the synchronous `await` + navigate pattern; navigation now happens in `handleTailorComplete`
  - Add concurrency guard: if `tailoringJob` is already set, toast "Already tailoring {title}" and return
  - Add `processing` status guard: if `job.tailoring_status === 'processing'`, toast and return

- [ ] **2c. Rewire `handleTailorComplete` in `App.tsx`**
  - SSE `run_complete` fires `onComplete(jobId)` → existing handler fetches versions and navigates
  - Extract `resume_id` from SSE event data (progress.resume_id) to navigate directly without extra fetch

- [ ] **2d. Rewire `handleTailorCancel` in `App.tsx`**
  - Call `apiClient.cancelTask(tailoringTaskId)` before clearing state
  - Toast "Tailoring stopped" on success

- [ ] **2e. Update `TailoringStrip.tsx`**
  - Show real stage from SSE progress events (planning → drafting → critiquing → saving)
  - Replace hardcoded `processingMessages` with SSE-driven message
  - Change "Cancel" button text to "Stop Tailoring"
  - Add loading state on the stop button while cancel API call is in-flight

- [ ] **2f. Fix button labels**
  - `JobDetail.tsx`: "Tailor & Approve →" → "Tailor CV →"
  - `JobDetail.tsx`: "Tailor Anyway" → "Tailor CV →"
  - `Dashboard.tsx` TailorCard: same label changes
  - Keep "Review & Send →" as-is (it's accurate)

- [ ] **2g. Add disabled guard to Dashboard card buttons**
  - Pass `isTailoring: boolean` (derived from `!!tailoringJob`) to Dashboard
  - Dashboard passes it down to TailorCard; disable the quick-action button when truthy

- [ ] **2h. Update `useSSE` handlers for cancelled status**
  - `onRunComplete` already handles any terminal event — just ensure cancelled triggers cleanup

### Phase 3 — Polish

- [ ] **3a. Update types**
  - `apiClient.ts`: update `tailorResume` return type to `{ task_id: string; message: string }`

- [ ] **3b. Update CLAUDE.md docs**
  - `glassresumatch-ai/CLAUDE.md`: document new button labels, cancel flow, SSE-driven progress
  - `api/CLAUDE.md`: document background task pattern for tailoring, cancel endpoint

---

## Progress Log
<!-- Append-only. Format: `- YYYY-MM-DD: what done, surprises, what changed` -->
