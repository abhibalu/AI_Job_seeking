# Plan: Phase 1 Cluster A — Schema Foundation

**Status:** 🟡 In Progress
**Created:** 2026-05-26
**Branch:** feature/phase1-schema-foundation
**Spec:** docs/superpowers/specs/2026-05-26-phase1-schema-foundation-design.md
**Plan:** docs/superpowers/plans/2026-05-26-phase1-schema-foundation.md

## Goal

Lock down data integrity of the `resumes` aggregate (status CHECK,
master-row coupling) and introduce a placeholder-row lifecycle for
in-flight tailoring runs so a stale-row reaper can detect hung
pipelines. Resolves R-RES-01, R-RES-02, R-RES-05, R-RES-07.

## Decisions Made

- Approach A (placeholder row) chosen over separate-table and
  tasks-only alternatives — see ADR-0022.
- Migrations 016–020 are manual-apply via Supabase SQL editor; the
  operator runs the preflight queries in 016 before applying 017–020.
- `save_tailored_resume` is a hard `NotImplementedError` shim — loud
  failure catches straggling call sites at runtime.
- Reaper timeout is operator-tunable
  (`system_config['tailoring_processing_timeout_minutes']`, default 15);
  reaper interval is fixed at 5 minutes.
- Every progress payload threads `job_id` + `resume_id` so the cancel
  endpoint avoids a `tasks.job_id` schema change.

## Open Items

- Apply migrations 016–020 against the production Supabase project.
- Cluster B (concurrency / idempotency) is the next sub-PR; it can
  later upgrade `idx_resumes_processing_started_at` to a UNIQUE
  partial index for the per-job claim lock.
