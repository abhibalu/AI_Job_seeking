# Phase 1 / Cluster A — Schema Foundation + State-Machine Persistence

**Status:** 🟡 Draft — awaiting user review
**Created:** 2026-05-26
**Branch:** `feature/phase1-schema-foundation`
**Spec source:** `docs/pipeline/runs/2026-05-24/domain-spec.md` (Implementation Roadmap, Phase 1)

## Goal

Lock down the data integrity foundation of the Resume aggregate so that every later
fix in Phase 1 (cluster B concurrency, cluster C validator correctness, cluster E
change-review integrity) has a stable schema and a real "tailoring in flight" row
to operate on. After this cluster ships, the `resumes` table enforces its own
vocabulary at the DB level, the master-row invariant is unforgeable, and a hung
tailoring run is reaped automatically rather than poisoning the UI forever.

Done looks like:
- `resumes.status` has a `CHECK` constraint matching the five-value vocabulary.
- A `master` row physically cannot have a `job_id` or a non-`not_started`
  `tailoring_status`.
- During a tailoring run, a placeholder `resumes` row exists with
  `tailoring_status='processing'` and `processing_started_at=now()`; `v_jobs_enriched`
  reports `processing` immediately on POST `/tailor`, not only at end-of-pipeline.
- A reaper sweeps `processing` rows older than an operator-tunable timeout
  (default 15 min) and transitions them to `cancelled` with a structured log line.
- User-initiated cancellation marks the resume row `cancelled` immediately,
  not after the next worker boundary.
- The reaper-race and cancel-race are both CAS-safe; no `resume_changes` orphans.

## In-scope requirements

| ID | Requirement | Source |
|----|-------------|--------|
| R-RES-01 | `CHECK` constraint on `resumes.status` vocabulary | MUST |
| R-RES-02 | DB-enforced `master` ↔ `(not_started, NULL job_id)` coupling | MUST |
| R-RES-05 | Processing timeout + stale-row reaper | MUST |
| R-RES-07 | Persist `tailoring_status='processing'` at subgraph entry | SHOULD |

R-RES-07 is pulled into cluster A because R-RES-05 needs a row to attach
`processing_started_at` to, and creating that row at worker start naturally
satisfies R-RES-07.

## Out of scope (explicit)

| Deferred to | Item |
|-------------|------|
| Cluster B | Per-job claim lock (R-RES-12), stale `base_resume` snapshot (R-RES-13) |
| Cluster C | Validator correctness (R-RES-09/10/11) |
| Cluster D | Critic JSON parsing, GDoc orphan cleanup (R-RES-15/16) |
| Cluster E | Resume-change UX integrity (R-CHG-01/04/07) |
| Cluster F | PII redaction (R-RES-18) |
| Phase 2 | `tasks.status='cancelled'` already a known gap (R-TASK-01); see Migration 020 below for the conditional one-line fix |

## Decisions made

- **Approach A wins** over (B) a separate `tailoring_runs` table and (C) a
  tasks-only JOIN. A satisfies R-RES-07's literal text ("tailoring_status='processing'
  on resumes"), needs no new view JOINs, and gives the cancel/reaper code a single
  CAS target. Decision evaluated against the 8-lens plan-evaluator framework.
- **Reaper lives in APScheduler** (`services/scheduler.py`). Interval 5 min,
  timeout configurable from `system_config['tailoring_processing_timeout_minutes']`,
  default 15.
- **CAS predicate `WHERE tailoring_status = 'processing'`** is the universal
  guard. Worker `finally`, the cancel endpoint, the reaper, and `node_save` all
  share it. Only one writer wins; the rest no-op.
- **Worst-case wasted LLM cost: 19m59s** (timeout 15m + reaper interval 5m,
  worst sweep alignment). Accepted because the alternative is per-node heartbeats,
  which is significantly more code and infrastructure.
- **Migration numbering: 016+.** 012 and 013 are missing in the current tree;
  treat them as truly unused (verify with `git log -- supabase_db/migrations/`).
- **Migration application is manual.** This project has no migration runner —
  SQL files are run against Supabase by the operator. The spec orders migrations
  so they apply cleanly top-to-bottom in numeric order.
- **`save_tailored_resume` is renamed/split, not amended.** It becomes a hard
  `ValueError` shim so any stragglers fail loud instead of silently double-INSERT.

## Schema migrations

All migrations are idempotent (use `ADD CONSTRAINT IF NOT EXISTS` where
supported; otherwise wrap in a DO block with `pg_constraint` lookup).

### `016_phase1_preflight_audit.sql` — no DDL

Commented-out queries the operator runs before applying 017–020. Catches
existing rows that would violate the new constraints. Examples:

```sql
-- Expected statuses today: master, pending, approved, rejected, needs_review
SELECT status, COUNT(*) FROM resumes GROUP BY status;

-- Master rows must already have tailoring_status='not_started' AND job_id IS NULL
SELECT id, status, tailoring_status, job_id
FROM resumes
WHERE status = 'master'
  AND (tailoring_status != 'not_started' OR job_id IS NOT NULL);

-- If the second query returns rows, fix data BEFORE running 018.
```

### `017_resumes_status_check.sql` — vocabulary CHECK (R-RES-01)

```sql
ALTER TABLE resumes
ADD CONSTRAINT resumes_status_check
CHECK (status IN ('master', 'pending', 'approved', 'rejected', 'needs_review'));
```

### `018_resumes_master_coupling.sql` — coupling CHECK (R-RES-02)

```sql
ALTER TABLE resumes
ADD CONSTRAINT resumes_master_coupling_check
CHECK (
  status != 'master'
  OR (tailoring_status = 'not_started' AND job_id IS NULL)
);
```

### `019_resumes_processing_metadata.sql` — processing timestamp (R-RES-05)

```sql
ALTER TABLE resumes
ADD COLUMN IF NOT EXISTS processing_started_at TIMESTAMPTZ DEFAULT NULL;

COMMENT ON COLUMN resumes.processing_started_at IS
  'Set to now() when worker creates placeholder row at subgraph entry. '
  'Used by stale-processing reaper (services/scheduler.py).';

CREATE INDEX IF NOT EXISTS idx_resumes_processing_started_at
ON resumes (processing_started_at)
WHERE tailoring_status = 'processing';

-- Seed the operator-tunable timeout into system_config.
INSERT INTO system_config (key, value) VALUES
  ('tailoring_processing_timeout_minutes', '15')
ON CONFLICT (key) DO NOTHING;
```

### `020_tasks_status_cancelled_check.sql` — one-line fix

Pulled in from Phase 2 R-TASK-01 because cancel can't work at the DB level
without it. Verified against `001_initial_schema.sql:85`: the current CHECK is
`('queued', 'running', 'completed', 'failed')` — `'cancelled'` is missing.
Despite that, `api/routes/tasks.py` and `services/reeval_worker.py` already
write `'cancelled'`, so every cancel attempt is silently failing the CHECK at
the DB level today.

```sql
ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_status_check;
ALTER TABLE tasks
  ADD CONSTRAINT tasks_status_check
  CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled'));
```

## Backend changes

### `agents/database.py`

Three new functions, one removed:

```python
def create_processing_placeholder(job_id: str) -> str:
    """INSERT placeholder resumes row at tailoring worker entry.

    Returns resume_id (UUID string). The row is in tailoring_status='processing'
    with content={} and processing_started_at=now().
    """
    record_id = str(uuid.uuid4())
    client = _get_supabase()
    client.table("resumes").insert({
        "id": record_id,
        "name": "Tailored Resume (in progress)",
        "content": {},
        "status": "pending",
        "job_id": job_id,
        "tailoring_status": "processing",
        "processing_started_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).execute()
    return record_id


def complete_tailored_resume(
    resume_id: str,
    version: int,
    content: dict,
    status: str = "pending",
    edit_plan: dict | None = None,
) -> bool:
    """CAS UPDATE the placeholder row with final content + tailoring_status.

    Returns True if applied, False if no-op (row was already cancelled by reaper
    or user). On False, resume_changes rows are NOT inserted — avoids orphans
    against a cancelled row.
    """
    tailoring_status_map = {
        "pending": "ready",
        "needs_review": "needs_review",
        "approved": "ready",
        "rejected": "ready",
    }
    client = _get_supabase()
    update = {
        "name": f"Tailored Resume V{version}",
        "content": content,
        "status": status,
        "version": version,
        "tailoring_status": tailoring_status_map.get(status, "ready"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if edit_plan is not None:
        update["edit_plan"] = edit_plan

    result = (
        client.table("resumes")
        .update(update)
        .eq("id", resume_id)
        .eq("tailoring_status", "processing")
        .execute()
    )
    if not result.data:
        logger.warning(
            "complete_tailored_resume.no_op",
            extra={"resume_id": resume_id, "reason": "row not in processing state"},
        )
        return False

    if edit_plan:
        _save_resume_changes(resume_id, result.data[0]["job_id"], edit_plan)
    return True


def mark_resume_cancelled(resume_id: str) -> bool:
    """CAS UPDATE: transition a processing row to cancelled.

    Idempotent — repeat callers (worker finally + cancel endpoint + reaper)
    safely no-op once one wins. Returns True on the winning call.
    """
    client = _get_supabase()
    result = (
        client.table("resumes")
        .update({
            "tailoring_status": "cancelled",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", resume_id)
        .eq("tailoring_status", "processing")
        .execute()
    )
    return bool(result.data)


def save_tailored_resume(*args, **kwargs):
    """REMOVED — use create_processing_placeholder + complete_tailored_resume.

    Hard error so any straggling call site is caught at runtime instead of
    silently double-INSERTing a tailored row.
    """
    raise NotImplementedError(
        "save_tailored_resume was split into create_processing_placeholder "
        "+ complete_tailored_resume in Phase 1 Cluster A (see ADR-0022)."
    )
```

### `agents/tailoring_subgraph.py`

`TailoringState` gains a required field:

```python
class TailoringState(TypedDict):
    # ... existing fields ...
    target_resume_id: str   # placeholder resume row id; set by worker at entry
    save_applied: bool      # True if node_save UPDATE was applied; False on CAS no-op
```

`node_save` is changed to UPDATE rather than INSERT:

```python
def node_save(state: TailoringState) -> dict:
    target_id = state["target_resume_id"]
    applied = complete_tailored_resume(
        resume_id=target_id,
        version=state.get("revision_count", 0),
        content=state["draft_resume"],
        status=("needs_review" if is_force_save(state) else "pending"),
        edit_plan=state.get("edit_plan"),
    )
    return {
        "final_resume_id": target_id,
        "save_applied": applied,
        "status": "saved" if applied else "cancelled",
    }
```

### `api/routes/resumes.py` — `run_tailoring_worker`

Three changes: placeholder row created at entry, `try/finally` for user-cancel
handling, CAS-aware terminal status, and **every `save_task_status` call now
threads `job_id` into the `progress` JSONB** so the cancel endpoint can route
back to the in-flight resume row without an extra schema change.

```python
def run_tailoring_worker(task_id: str, job_id: str, initial_state: dict):
    from agents.database import (
        create_processing_placeholder,
        mark_resume_cancelled,
        save_task_status,
        get_task_status,
    )
    # ... existing imports of node_* and route_* ...

    resume_id = create_processing_placeholder(job_id)
    state = dict(initial_state)
    state["target_resume_id"] = resume_id
    state.setdefault("errors", [])
    state.setdefault("status", "queued")
    state.setdefault("draft_resume", {})
    state.setdefault("save_applied", False)

    def progress(completed: int, stage: str, **extra) -> dict:
        """Every progress payload carries job_id + resume_id so the cancel
        endpoint can look up the in-flight resume row from the tasks table."""
        return {
            "completed": completed,
            "total": 4,
            "stage": stage,
            "job_id": job_id,
            "resume_id": resume_id,
            **extra,
        }

    def is_cancelled():
        task = get_task_status(task_id)
        return task and task.get("status") == "cancelled"

    try:
        # --- Stage 1: Planning ---
        save_task_status(task_id, "running", progress(0, "planning"))
        if is_cancelled(): return
        # ... existing node_plan, node_draft, node_validate, node_critique,
        # node_save body — every save_task_status call swapped to use progress(...) ...

        # After node_save:
        if not state.get("save_applied", False):
            save_task_status(
                task_id, "cancelled",
                progress(3, "saving"),
                error="row reaped or cancelled mid-save",
            )
            return

        record_id = state.get("final_resume_id", "")
        save_task_status(task_id, "completed",
                         progress(4, "done", resume_id=record_id))

    except Exception as e:
        logger.exception("Tailoring worker unhandled exception",
                         extra={"task_id": task_id, "job_id": job_id, "resume_id": resume_id})
        save_task_status(task_id, "failed",
                         progress(0, "error"), error=str(e))
        # Do NOT mark resume cancelled here — exceptions are involuntary;
        # the reaper handles the row after the timeout.
    finally:
        if is_cancelled():
            try:
                if mark_resume_cancelled(resume_id):
                    logger.info("tailoring.cancelled_by_user",
                                extra={"task_id": task_id, "job_id": job_id,
                                       "resume_id": resume_id})
            except Exception:
                logger.exception("Failed to mark resume cancelled in finally",
                                 extra={"resume_id": resume_id})
```

### `api/routes/tasks.py` — cancel endpoint

After flipping `tasks.status='cancelled'`, also mark the in-flight resume row.
Shortens UI staleness from "worker's next boundary check" (up to a few seconds
of LLM latency) to zero. Idempotent with the worker's `finally` via CAS.

`tasks` has no `job_id` column (`001_initial_schema.sql:82-90`), so we read
`progress.job_id` and `progress.resume_id` written by the worker.

```python
@router.post("/{task_id}/cancel")
def cancel_task(task_id: str):
    # ... existing tasks.status update ...

    # Best-effort: also mark the in-flight resume row.
    task = get_task_status(task_id)
    progress = (task or {}).get("progress") or {}
    resume_id = progress.get("resume_id")
    if resume_id:
        mark_resume_cancelled(resume_id)  # CAS — no-op if already terminal
    return {"ok": True}
```

This avoids a query: the worker already wrote the resume_id into `progress`,
so we read it directly rather than re-looking-up by `job_id`.

### `services/scheduler.py` — reaper job

```python
from datetime import datetime, timedelta, timezone

def reap_stale_tailoring_runs():
    """Mark resumes rows stuck in tailoring_status='processing' as cancelled."""
    from agents.database import get_system_config, _get_supabase

    timeout_min = int(get_system_config("tailoring_processing_timeout_minutes") or 15)
    threshold = datetime.now(timezone.utc) - timedelta(minutes=timeout_min)

    client = _get_supabase()
    result = (
        client.table("resumes")
        .update({"tailoring_status": "cancelled",
                 "updated_at": datetime.now(timezone.utc).isoformat()})
        .eq("tailoring_status", "processing")
        .lt("processing_started_at", threshold.isoformat())
        .execute()
    )
    reaped = len(result.data or [])
    if reaped:
        logger.warning(
            "reaper.cancelled_stale_processing",
            extra={"count": reaped, "timeout_minutes": timeout_min},
        )

# In scheduler setup:
scheduler.add_job(
    reap_stale_tailoring_runs,
    trigger="interval",
    minutes=5,
    id="reap_stale_tailoring_runs",
    coalesce=True,
    max_instances=1,
    replace_existing=True,
)
```

## Test plan

`test/test_resume_lifecycle_foundation.py` — 10 tests. Naming avoids collision
with the existing `test/test_phase1_pipeline.py` (which covers OotoCV Phase 1,
not this domain-spec Phase 1). Patterns follow `test/test_phase1_pipeline.py`
which splits unit (fully mocked) and integration (real Supabase) sections.

| # | Test | What it verifies |
|---|------|------------------|
| T1 | `test_worker_creates_placeholder` | After POST `/tailor`, a resumes row exists with `tailoring_status='processing'` and non-NULL `processing_started_at` |
| T2 | `test_node_save_updates_not_inserts` | Exactly one resumes row per tailoring run; placeholder row's `tailoring_status` flips to `ready` |
| T3 | `test_reaper_sweeps_stale_rows` | Row with `processing_started_at < now() - timeout` is marked `cancelled` |
| T4 | `test_reaper_skips_fresh_rows` | Row with `processing_started_at` within timeout is not touched |
| T5 | `test_complete_tailored_resume_cas_no_op` | Calling `complete_tailored_resume` on an already-cancelled row returns False and does NOT insert `resume_changes` |
| T6 | `test_worker_finally_marks_cancelled_on_user_cancel` | When user cancels, resume row's `tailoring_status='cancelled'` is set immediately |
| T7 | `test_status_check_rejects_invalid_value` | DB rejects `INSERT ... status='nonsense'` |
| T8 | `test_master_coupling_check_rejects` | DB rejects setting `job_id` on a `status='master'` row, and rejects setting `status='master'` on a row with non-NULL `job_id` |
| T9 | `test_preflight_audit_query_succeeds` | Audit queries in `016_phase1_preflight_audit.sql` parse and execute without error against current DB (no rows returned in violation queries) |
| T10 | `test_worker_reflects_reaper_race` | If `complete_tailored_resume` returns False, the worker calls `save_task_status(task_id, "cancelled", ...)`, NOT `"completed"` |

## Observability

| Event | Level | Logger key | Extra fields |
|-------|-------|-----------|--------------|
| Reaper sweeps ≥1 row | `WARNING` | `reaper.cancelled_stale_processing` | `count`, `timeout_minutes` |
| `complete_tailored_resume` no-op | `WARNING` | `complete_tailored_resume.no_op` | `resume_id`, `reason` |
| User-initiated cancel marks resume row | `INFO` | `tailoring.cancelled_by_user` | `task_id`, `job_id`, `resume_id` |
| Worker hits unhandled exception | `EXCEPTION` | `Tailoring worker unhandled exception` | `task_id`, `job_id`, `resume_id` |

All carry `correlation_id` automatically via ADR-0017's `ContextVar`.

## Migration application order (operator workflow)

1. Read and run `016_phase1_preflight_audit.sql` queries manually. If anything
   returns rows in the "master row violations" section, fix data first.
2. Apply `017_resumes_status_check.sql`.
3. Apply `018_resumes_master_coupling.sql`.
4. Apply `019_resumes_processing_metadata.sql`.
5. Apply `020_tasks_status_cancelled_check.sql`.
6. Deploy the backend code change (placeholder row + reaper + new helpers).

Rolling back a CHECK constraint: `ALTER TABLE resumes DROP CONSTRAINT resumes_status_check`.

## Trade-offs accepted

| Trade-off | Why accepted |
|-----------|--------------|
| Worst-case 19m59s of LLM cost on a truly hung worker | Cheaper than per-node heartbeat infrastructure; reaper interval halvable to 1 min later if needed |
| Placeholder rows briefly visible in `v_jobs_enriched` before completion | This is the intended observability win — UI sees `processing` from POST onward |
| Worker exceptions don't immediately cancel the resume row (only user cancels do) | Semantically distinct outcomes: voluntary (cancel) vs. involuntary (crash); reaper safety-nets the crash path |
| `save_tailored_resume` raises rather than being silently removed | Loud failure catches any straggling call site at runtime |

## Open follow-ups (not blocking this cluster)

- ADR-0022 to record the placeholder-row decision (write after this cluster ships).
- Once the per-job claim lock lands in Cluster B, the `processing_started_at`
  index can become `UNIQUE (job_id) WHERE tailoring_status='processing'` — this
  spec deliberately uses a non-unique index so Cluster A can ship before B.
- A future "retry from checkpoint" feature can read the `cancelled` rows to
  surface "we hung this job — want to retry?" — not in Phase 1 scope.
