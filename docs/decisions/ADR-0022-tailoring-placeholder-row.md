# ADR-0022: Placeholder-row lifecycle for tailoring runs

**Status:** Accepted
**Date:** 2026-05-26
**Context:** Phase 1 Cluster A — Schema Foundation

## Context

Before this ADR, a tailored `resumes` row only existed after `node_save`
ran at end-of-pipeline. There was no row to attach `processing_started_at`
to (R-RES-05), no way for `v_jobs_enriched` to surface `processing`
during the multi-minute pipeline (R-RES-07), and no CAS target for the
user-cancel or reaper paths.

Three candidates were evaluated via the plan-evaluator skill:
A. Placeholder row at worker start, UPDATEd at node_save.
B. Separate `tailoring_runs` table.
C. Tasks-only tracking via a `v_jobs_enriched` JOIN with `tasks`.

## Decision

Adopt **A**: create a placeholder `resumes` row at
`run_tailoring_worker` entry with `tailoring_status='processing'`,
`processing_started_at=now()`, `content={}`. `node_save` UPDATEs the
row via CAS predicate `WHERE tailoring_status='processing'`.

## Consequences

- `save_tailored_resume` is split into three helpers
  (`create_processing_placeholder`, `complete_tailored_resume`,
  `mark_resume_cancelled`) and the original function becomes a
  `NotImplementedError` shim.
- `TailoringState` gains `target_resume_id` and `save_applied`.
- Every `save_task_status` progress payload threads `job_id` +
  `resume_id` so the cancel endpoint can route back to the in-flight
  row without an extra `tasks.job_id` schema column.
- A reaper (`services/scheduler.py:reap_stale_tailoring_runs`) sweeps
  rows past the operator-tunable timeout (default 15 min) and marks
  them cancelled.
- Accepted worst-case wasted-LLM window: 19m59s (15-min timeout +
  5-min reaper interval).

## Alternatives considered

- **B (separate `tailoring_runs` table)** rejected: requires
  `v_jobs_enriched` to JOIN both tables and does not satisfy R-RES-07's
  literal text (which asks for `tailoring_status='processing'` on the
  `resumes` row).
- **C (tasks-only)** rejected: the `tasks` table has no `job_id`
  column and adding one couples Resume-aggregate observability to the
  TASK aggregate (Phase 2 scope).
