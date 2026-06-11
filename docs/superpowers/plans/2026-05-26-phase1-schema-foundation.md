# Phase 1 Cluster A — Schema Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lock down `resumes` table data integrity at the DB level (status CHECK + master-row coupling), introduce a placeholder-row lifecycle for in-flight tailoring runs, and add a reaper that sweeps hung pipelines after an operator-tunable timeout.

**Architecture:** Resolves R-RES-01, R-RES-02, R-RES-05, R-RES-07 from the domain spec. A tailoring pipeline now creates a placeholder `resumes` row at worker entry (`tailoring_status='processing'`, `processing_started_at=now()`), then UPDATEs it on completion via CAS predicate `WHERE tailoring_status='processing'`. User cancel and reaper sweep both go through the same CAS path, so all three writers (worker, cancel endpoint, reaper) are idempotent. `save_tailored_resume` is hard-removed (replaced by a `NotImplementedError` shim) and split into `create_processing_placeholder` + `complete_tailored_resume` + `mark_resume_cancelled`.

**Tech Stack:** Python 3.11, FastAPI, Supabase (PostgreSQL), APScheduler, LangGraph, pytest+unittest.mock.

**Spec:** `docs/superpowers/specs/2026-05-26-phase1-schema-foundation-design.md`

**Branch:** `feature/phase1-schema-foundation`

---

## File Structure

**Created:**
- `supabase_db/migrations/016_phase1_preflight_audit.sql` — operator audit (no DDL)
- `supabase_db/migrations/017_resumes_status_check.sql` — CHECK on `resumes.status`
- `supabase_db/migrations/018_resumes_master_coupling.sql` — `master` row invariant CHECK
- `supabase_db/migrations/019_resumes_processing_metadata.sql` — `processing_started_at` column + index + `system_config` seed
- `supabase_db/migrations/020_tasks_status_cancelled_check.sql` — extend `tasks.status` CHECK with `cancelled`
- `test/test_resume_lifecycle_foundation.py` — 10 tests (unit + integration)
- `docs/decisions/ADR-0022-tailoring-placeholder-row.md` — decision record

**Modified:**
- `agents/database.py` — three new helpers; `save_tailored_resume` becomes `NotImplementedError` shim
- `agents/tailoring_subgraph.py` — `TailoringState` adds `target_resume_id` + `save_applied`; `node_save` rewritten to UPDATE-via-helper
- `api/routes/resumes.py` — `run_tailoring_worker` creates placeholder, adds `progress()` helper, wraps body in `try/finally`
- `api/routes/tasks.py` — cancel endpoint reads `progress.resume_id` and calls `mark_resume_cancelled`
- `services/scheduler.py` — registers `reap_stale_tailoring_runs` job (5-minute interval)
- `agents/CLAUDE.md` — document placeholder lifecycle + new helpers
- `api/CLAUDE.md` — document `progress.job_id`/`progress.resume_id` convention
- `services/CLAUDE.md` — document reaper job
- `CLAUDE.md` — add ADR-0022 to the decisions list; add an active doc entry
- `docs/active/phase1-schema-foundation.md` — track in-flight active doc

---

## Conventions

- **Commits per task.** Each task ends with a `git add ... && git commit` step using Conventional Commits.
- **TDD.** Tests come before implementation in every code-bearing task. Failing-test step is explicit.
- **Migrations are manual-apply.** The operator runs them against Supabase; the code lands with backend changes that depend on them. Backend tests mock Supabase so they don't require migrations to be applied first.
- **All new logger calls use structured form** per ADR-0017: `logger.warning("event.key", extra={...})`.
- **Test isolation pattern**: per `test/test_phase1_pipeline.py`, decorate with `@patch("agents.database._get_supabase")` returning a `MagicMock`, assert call args. Integration tests skip when `SUPABASE_URL` is not set.

---

## Task 1: Migrations 016–020

**Files:**
- Create: `supabase_db/migrations/016_phase1_preflight_audit.sql`
- Create: `supabase_db/migrations/017_resumes_status_check.sql`
- Create: `supabase_db/migrations/018_resumes_master_coupling.sql`
- Create: `supabase_db/migrations/019_resumes_processing_metadata.sql`
- Create: `supabase_db/migrations/020_tasks_status_cancelled_check.sql`

- [ ] **Step 1.1: Create migration 016 (preflight audit)**

Write `supabase_db/migrations/016_phase1_preflight_audit.sql`:

```sql
-- Migration 016: Phase 1 preflight audit — NO DDL.
-- The operator runs these queries against Supabase before applying 017–020.
-- If any "violations" query returns rows, fix data BEFORE applying 018.

-- 1. Confirm status vocabulary matches the CHECK we are about to install.
--    Expected: only master, pending, approved, rejected, needs_review.
-- SELECT status, COUNT(*) FROM resumes GROUP BY status ORDER BY status;

-- 2. Master-row violations: master must have tailoring_status='not_started' AND job_id IS NULL.
-- SELECT id, status, tailoring_status, job_id, name
-- FROM resumes
-- WHERE status = 'master'
--   AND (tailoring_status != 'not_started' OR job_id IS NOT NULL);

-- 3. Confirm tasks.status CHECK currently lacks 'cancelled' (justifies migration 020).
-- SELECT pg_get_constraintdef(c.oid)
-- FROM pg_constraint c
-- JOIN pg_class t ON t.oid = c.conrelid
-- WHERE t.relname = 'tasks' AND c.contype = 'c';
```

- [ ] **Step 1.2: Create migration 017 (resumes.status CHECK)**

Write `supabase_db/migrations/017_resumes_status_check.sql`:

```sql
-- Migration 017: Add CHECK constraint on resumes.status (R-RES-01).
-- Vocabulary was previously enforced only in Python (agents/database.py).

ALTER TABLE resumes DROP CONSTRAINT IF EXISTS resumes_status_check;
ALTER TABLE resumes
  ADD CONSTRAINT resumes_status_check
  CHECK (status IN ('master', 'pending', 'approved', 'rejected', 'needs_review'));

COMMENT ON CONSTRAINT resumes_status_check ON resumes IS
  'Vocabulary enforcement for resumes.status (Phase 1 Cluster A).';
```

- [ ] **Step 1.3: Create migration 018 (master coupling CHECK)**

Write `supabase_db/migrations/018_resumes_master_coupling.sql`:

```sql
-- Migration 018: Enforce master-row invariant at the DB level (R-RES-02).
-- A master resume must have tailoring_status='not_started' AND job_id IS NULL.
-- Run query #2 from migration 016 first; fix any violations before applying.

ALTER TABLE resumes DROP CONSTRAINT IF EXISTS resumes_master_coupling_check;
ALTER TABLE resumes
  ADD CONSTRAINT resumes_master_coupling_check
  CHECK (
    status != 'master'
    OR (tailoring_status = 'not_started' AND job_id IS NULL)
  );

COMMENT ON CONSTRAINT resumes_master_coupling_check ON resumes IS
  'Prevents a status=master row from slipping into the Tailored compound state.';
```

- [ ] **Step 1.4: Create migration 019 (processing metadata + system_config seed)**

Write `supabase_db/migrations/019_resumes_processing_metadata.sql`:

```sql
-- Migration 019: processing_started_at + index for the stale-tailoring reaper (R-RES-05).
-- Operator-tunable timeout stored in system_config (default 15 minutes).

ALTER TABLE resumes
  ADD COLUMN IF NOT EXISTS processing_started_at TIMESTAMPTZ DEFAULT NULL;

COMMENT ON COLUMN resumes.processing_started_at IS
  'Set to now() when the worker creates a placeholder row at subgraph entry. '
  'NULL on terminal rows. Used by services/scheduler.py reap_stale_tailoring_runs.';

CREATE INDEX IF NOT EXISTS idx_resumes_processing_started_at
  ON resumes (processing_started_at)
  WHERE tailoring_status = 'processing';

INSERT INTO system_config (key, value) VALUES
  ('tailoring_processing_timeout_minutes', '15')
ON CONFLICT (key) DO NOTHING;
```

- [ ] **Step 1.5: Create migration 020 (tasks.status CHECK adds 'cancelled')**

Write `supabase_db/migrations/020_tasks_status_cancelled_check.sql`:

```sql
-- Migration 020: extend tasks.status CHECK to include 'cancelled'.
-- Verified against 001_initial_schema.sql:85 — current CHECK is
-- ('queued','running','completed','failed'). Despite that, api/routes/tasks.py
-- and services/reeval_worker.py already write 'cancelled', so every cancel
-- attempt is silently violating CHECK at the DB level today.

ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_status_check;
ALTER TABLE tasks
  ADD CONSTRAINT tasks_status_check
  CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled'));
```

- [ ] **Step 1.6: Commit migrations**

```bash
git add supabase_db/migrations/016_phase1_preflight_audit.sql \
        supabase_db/migrations/017_resumes_status_check.sql \
        supabase_db/migrations/018_resumes_master_coupling.sql \
        supabase_db/migrations/019_resumes_processing_metadata.sql \
        supabase_db/migrations/020_tasks_status_cancelled_check.sql
git commit -m "feat(db): add migrations 016-020 for Phase 1 schema foundation

- 016: preflight audit queries (no DDL)
- 017: CHECK constraint on resumes.status vocabulary (R-RES-01)
- 018: master-row coupling invariant CHECK (R-RES-02)
- 019: processing_started_at column + reaper index +
  tailoring_processing_timeout_minutes seed (R-RES-05)
- 020: extend tasks.status CHECK to include cancelled

Operator runs SQL files manually against Supabase in order 016 -> 020.
Code changes in subsequent commits depend on these migrations being applied."
```

---

## Task 2: Test scaffolding + first unit test (T5 — `complete_tailored_resume` CAS no-op)

Write the failing test first; the implementation in Task 3 makes it pass.

**Files:**
- Create: `test/test_resume_lifecycle_foundation.py`

- [ ] **Step 2.1: Create test file skeleton**

Write `test/test_resume_lifecycle_foundation.py`:

```python
"""
test/test_resume_lifecycle_foundation.py

Phase 1 Cluster A — Schema Foundation tests.

Covers the placeholder-row lifecycle for tailoring runs, the stale-row reaper,
the DB-level CHECK constraints, and the worker/cancel/reaper race paths.

Split into:
  - Unit tests (fully mocked — no DB).
  - Integration tests (real Supabase, skipped when SUPABASE_URL is unset).
"""
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def _mock_supabase_chain(return_data):
    """Build a MagicMock chain that mimics the supabase-py builder pattern.

    Used as the return value of patched _get_supabase(). Lets a test set the
    final `.execute()` result without wiring every intermediate call by hand.
    """
    final = MagicMock()
    final.execute.return_value = MagicMock(data=return_data)
    chain = MagicMock()
    # Every method on the chain returns itself so a long .update().eq().eq()
    # builder ends up at `final` for .execute().
    for method in ("insert", "update", "select", "eq", "lt", "order", "limit"):
        getattr(chain, method).return_value = chain
    chain.execute = final.execute
    return chain


# ─────────────────────────────────────────────────────────────────
# 1.  complete_tailored_resume — CAS UPDATE behavior
# ─────────────────────────────────────────────────────────────────
class TestCompleteTailoredResumeCAS(unittest.TestCase):
    """Verify complete_tailored_resume short-circuits when the row is no
    longer in `processing` (reaper-race / user-cancel-race)."""

    @patch("agents.database._save_resume_changes")
    @patch("agents.database._get_supabase")
    def test_complete_tailored_resume_cas_no_op(self, mock_get_supabase, mock_save_changes):
        """T5: When UPDATE returns zero rows, function returns False and
        does NOT call _save_resume_changes (avoiding orphan rows against
        a cancelled resume).
        """
        from agents.database import complete_tailored_resume

        # Supabase update().eq().eq().execute() returns an empty data list
        # — simulating a CAS miss because tailoring_status != 'processing'.
        chain = _mock_supabase_chain(return_data=[])
        mock_get_supabase.return_value.table.return_value = chain

        result = complete_tailored_resume(
            resume_id="00000000-0000-0000-0000-000000000001",
            version=1,
            content={"basics": {"name": "Test"}},
            status="pending",
            edit_plan={"edits": [{"action": "rephrase", "location": "x", "target_text": "y"}]},
        )

        self.assertFalse(result, "Expected False return on CAS no-op")
        mock_save_changes.assert_not_called()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2.2: Run test to verify it fails (function not yet implemented)**

```bash
cd /Users/abhijithm/Documents/Code/TailorAI
pytest test/test_resume_lifecycle_foundation.py::TestCompleteTailoredResumeCAS::test_complete_tailored_resume_cas_no_op -v
```

Expected: FAIL with `ImportError: cannot import name 'complete_tailored_resume' from 'agents.database'`.

- [ ] **Step 2.3: Commit (test only, intentionally failing)**

```bash
git add test/test_resume_lifecycle_foundation.py
git commit -m "test: add failing CAS no-op test for complete_tailored_resume"
```

---

## Task 3: Implement `complete_tailored_resume`

**Files:**
- Modify: `agents/database.py` (around lines 351–388; current `save_tailored_resume`)

- [ ] **Step 3.1: Add `complete_tailored_resume` to `agents/database.py`**

Insert the following function in `agents/database.py` immediately after the existing `save_tailored_resume` body (we will replace `save_tailored_resume` itself in Task 6):

```python
def complete_tailored_resume(
    resume_id: str,
    version: int,
    content: dict,
    status: str = "pending",
    edit_plan: dict | None = None,
) -> bool:
    """CAS UPDATE a placeholder resumes row to its final tailored content.

    Predicate: WHERE id = resume_id AND tailoring_status = 'processing'.
    On zero rows updated, returns False and does NOT insert resume_changes
    (avoids orphans against a row already cancelled by the reaper or user).

    Returns:
        True if the UPDATE applied; False on CAS no-op.
    """
    tailoring_status_map = {
        "pending": "ready",
        "needs_review": "needs_review",
        "approved": "ready",
        "rejected": "ready",
    }

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

    client = _get_supabase()
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
        job_id = result.data[0].get("job_id")
        _save_resume_changes(resume_id, job_id, edit_plan)
    return True
```

Make sure `datetime` and `timezone` are imported at the top of `agents/database.py` (they already are — verify with `head -30 agents/database.py`).

- [ ] **Step 3.2: Run test to verify it passes**

```bash
pytest test/test_resume_lifecycle_foundation.py::TestCompleteTailoredResumeCAS::test_complete_tailored_resume_cas_no_op -v
```

Expected: PASS.

- [ ] **Step 3.3: Commit**

```bash
git add agents/database.py
git commit -m "feat(db): add complete_tailored_resume with CAS UPDATE

CAS predicate WHERE tailoring_status='processing' ensures the reaper-race
and user-cancel-race both no-op safely. Returns False on no-op; callers
treat that as a cancelled outcome (Task 8 wires this through the worker)."
```

---

## Task 4: Implement `create_processing_placeholder` (T1)

**Files:**
- Modify: `agents/database.py`
- Modify: `test/test_resume_lifecycle_foundation.py`

- [ ] **Step 4.1: Write failing test (T1)**

Append to `test/test_resume_lifecycle_foundation.py` after the existing test class:

```python
# ─────────────────────────────────────────────────────────────────
# 2.  create_processing_placeholder — INSERT shape
# ─────────────────────────────────────────────────────────────────
class TestCreateProcessingPlaceholder(unittest.TestCase):

    @patch("agents.database._get_supabase")
    def test_worker_creates_placeholder(self, mock_get_supabase):
        """T1: Placeholder row INSERT has the right shape:
        status='pending', tailoring_status='processing',
        non-NULL processing_started_at, job_id set, content={}.
        """
        from agents.database import create_processing_placeholder

        chain = _mock_supabase_chain(return_data=[{"id": "x"}])
        mock_get_supabase.return_value.table.return_value = chain

        resume_id = create_processing_placeholder(job_id="job-42")

        self.assertTrue(resume_id, "Expected non-empty resume_id")
        chain.insert.assert_called_once()
        inserted = chain.insert.call_args[0][0]
        self.assertEqual(inserted["status"], "pending")
        self.assertEqual(inserted["tailoring_status"], "processing")
        self.assertEqual(inserted["job_id"], "job-42")
        self.assertEqual(inserted["content"], {})
        self.assertIn("processing_started_at", inserted)
        self.assertIsNotNone(inserted["processing_started_at"])
```

- [ ] **Step 4.2: Run test to verify it fails**

```bash
pytest test/test_resume_lifecycle_foundation.py::TestCreateProcessingPlaceholder::test_worker_creates_placeholder -v
```

Expected: FAIL with `ImportError: cannot import name 'create_processing_placeholder'`.

- [ ] **Step 4.3: Add `create_processing_placeholder` to `agents/database.py`**

Insert this function in `agents/database.py` immediately above `complete_tailored_resume`:

```python
def create_processing_placeholder(job_id: str) -> str:
    """INSERT a placeholder resumes row at tailoring worker entry.

    The row is created with tailoring_status='processing',
    processing_started_at=now(), and an empty content={} which
    complete_tailored_resume() fills in at end-of-pipeline.

    Returns:
        resume_id (UUID string) of the newly-created placeholder row.
    """
    import uuid
    record_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    client = _get_supabase()
    client.table("resumes").insert({
        "id": record_id,
        "name": "Tailored Resume (in progress)",
        "content": {},
        "status": "pending",
        "job_id": job_id,
        "tailoring_status": "processing",
        "processing_started_at": now_iso,
        "updated_at": now_iso,
    }).execute()
    return record_id
```

- [ ] **Step 4.4: Run test to verify it passes**

```bash
pytest test/test_resume_lifecycle_foundation.py::TestCreateProcessingPlaceholder -v
```

Expected: PASS.

- [ ] **Step 4.5: Commit**

```bash
git add agents/database.py test/test_resume_lifecycle_foundation.py
git commit -m "feat(db): add create_processing_placeholder for tailoring worker entry

INSERTs a placeholder resumes row with tailoring_status='processing'
and processing_started_at=now(). The worker (Task 8) will create one
of these rows before invoking the tailoring subgraph so v_jobs_enriched
surfaces 'processing' immediately on POST /tailor."
```

---

## Task 5: Implement `mark_resume_cancelled`

**Files:**
- Modify: `agents/database.py`
- Modify: `test/test_resume_lifecycle_foundation.py`

- [ ] **Step 5.1: Write failing test**

Append to `test/test_resume_lifecycle_foundation.py`:

```python
# ─────────────────────────────────────────────────────────────────
# 3.  mark_resume_cancelled — CAS UPDATE behavior
# ─────────────────────────────────────────────────────────────────
class TestMarkResumeCancelled(unittest.TestCase):

    @patch("agents.database._get_supabase")
    def test_returns_true_when_row_was_processing(self, mock_get_supabase):
        from agents.database import mark_resume_cancelled

        chain = _mock_supabase_chain(return_data=[{"id": "r1"}])
        mock_get_supabase.return_value.table.return_value = chain

        self.assertTrue(mark_resume_cancelled("r1"))

        update_kwargs = chain.update.call_args[0][0]
        self.assertEqual(update_kwargs["tailoring_status"], "cancelled")
        self.assertIn("updated_at", update_kwargs)

    @patch("agents.database._get_supabase")
    def test_returns_false_on_no_op(self, mock_get_supabase):
        from agents.database import mark_resume_cancelled

        chain = _mock_supabase_chain(return_data=[])
        mock_get_supabase.return_value.table.return_value = chain

        self.assertFalse(mark_resume_cancelled("r1"))
```

- [ ] **Step 5.2: Run tests to verify they fail**

```bash
pytest test/test_resume_lifecycle_foundation.py::TestMarkResumeCancelled -v
```

Expected: FAIL with `ImportError: cannot import name 'mark_resume_cancelled'`.

- [ ] **Step 5.3: Add `mark_resume_cancelled` to `agents/database.py`**

Insert below `complete_tailored_resume`:

```python
def mark_resume_cancelled(resume_id: str) -> bool:
    """CAS UPDATE: transition a processing resumes row to cancelled.

    Idempotent — concurrent callers (worker `finally`, cancel endpoint,
    reaper) safely no-op once one wins.

    Returns:
        True if THIS call won the CAS; False if the row was already
        terminal (cancelled / ready / needs_review).
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
```

- [ ] **Step 5.4: Run tests to verify they pass**

```bash
pytest test/test_resume_lifecycle_foundation.py::TestMarkResumeCancelled -v
```

Expected: 2 tests PASS.

- [ ] **Step 5.5: Commit**

```bash
git add agents/database.py test/test_resume_lifecycle_foundation.py
git commit -m "feat(db): add mark_resume_cancelled CAS helper

Idempotent — called by worker finally block, cancel endpoint, and the
reaper. CAS predicate WHERE tailoring_status='processing' guarantees
only one writer wins on concurrent attempts."
```

---

## Task 6: Replace `save_tailored_resume` with `NotImplementedError` shim

**Files:**
- Modify: `agents/database.py` (lines 351–388: the existing `save_tailored_resume` body)

- [ ] **Step 6.1: Replace the function body**

In `agents/database.py`, find the existing `def save_tailored_resume(...)` (currently spanning lines 351–388) and replace its body with:

```python
def save_tailored_resume(*args, **kwargs):
    """REMOVED in Phase 1 Cluster A (ADR-0022).

    The old INSERT-at-end model has been replaced by:
      create_processing_placeholder(job_id) -> resume_id      (at worker entry)
      complete_tailored_resume(resume_id, ...)                (at node_save)
      mark_resume_cancelled(resume_id)                        (cancel/reaper)

    This shim raises NotImplementedError so any straggling call site is
    caught at runtime instead of silently double-INSERTing a tailored row.
    """
    raise NotImplementedError(
        "save_tailored_resume was split into create_processing_placeholder + "
        "complete_tailored_resume in Phase 1 Cluster A (ADR-0022). "
        "Call sites must thread target_resume_id through TailoringState."
    )
```

- [ ] **Step 6.2: Verify no other call sites exist in the repo**

```bash
grep -rn "save_tailored_resume" --include='*.py' /Users/abhijithm/Documents/Code/TailorAI/ | grep -v test_
```

Expected output: only `agents/database.py` (the shim itself) and `agents/tailoring_subgraph.py` (which Task 7 will replace).

- [ ] **Step 6.3: Add a regression test that the shim raises**

Append to `test/test_resume_lifecycle_foundation.py`:

```python
# ─────────────────────────────────────────────────────────────────
# 4.  save_tailored_resume — must raise after the Cluster A split
# ─────────────────────────────────────────────────────────────────
class TestSaveTailoredResumeRemoved(unittest.TestCase):

    def test_save_tailored_resume_raises(self):
        from agents.database import save_tailored_resume
        with self.assertRaises(NotImplementedError):
            save_tailored_resume(
                job_id="x", version=1, content={}, status="pending", edit_plan=None,
            )
```

- [ ] **Step 6.4: Run the new test + the whole file**

```bash
pytest test/test_resume_lifecycle_foundation.py -v
```

Expected: 5 tests PASS (1 + 1 + 2 + 1).

- [ ] **Step 6.5: Commit**

```bash
git add agents/database.py test/test_resume_lifecycle_foundation.py
git commit -m "refactor(db): replace save_tailored_resume with NotImplementedError shim

The function is split into create_processing_placeholder +
complete_tailored_resume (placeholder row pattern). The shim makes any
straggling call site fail loud instead of silently double-INSERTing."
```

---

## Task 7: `TailoringState` + `node_save` UPDATE (T2)

**Files:**
- Modify: `agents/tailoring_subgraph.py`
- Modify: `test/test_resume_lifecycle_foundation.py`

- [ ] **Step 7.1: Locate the current `node_save` and `TailoringState`**

```bash
grep -n "TailoringState\|def node_save\|save_tailored_resume\|is_force_save" /Users/abhijithm/Documents/Code/TailorAI/agents/tailoring_subgraph.py
```

Note the line numbers. The current `node_save` calls `save_tailored_resume(...)`; we replace that call.

- [ ] **Step 7.2: Add required fields to `TailoringState`**

In `agents/tailoring_subgraph.py`, find the `TailoringState` `TypedDict` and add these fields (preserving existing ones):

```python
class TailoringState(TypedDict):
    # ... existing fields preserved verbatim ...
    target_resume_id: str   # placeholder resume row id; set by worker at entry
    save_applied: bool      # True if node_save UPDATE was applied; False on CAS no-op
```

- [ ] **Step 7.3: Rewrite `node_save` to use `complete_tailored_resume`**

Replace the current body of `node_save` with:

```python
def node_save(state: TailoringState) -> dict:
    """Finalise the tailored resume by UPDATEing the placeholder row.

    Uses CAS (complete_tailored_resume) so that a reaper-cancelled or
    user-cancelled row is left alone and the worker reports the run
    as cancelled rather than completed (run_tailoring_worker checks
    state['save_applied']).
    """
    from agents.database import complete_tailored_resume

    target_id = state["target_resume_id"]
    is_force = is_force_save(state)  # existing helper
    status_value = "needs_review" if is_force else "pending"

    applied = complete_tailored_resume(
        resume_id=target_id,
        version=state.get("revision_count", 0),
        content=state["draft_resume"],
        status=status_value,
        edit_plan=state.get("edit_plan"),
    )

    logger.info(
        "[SubGraph] node_save complete",
        extra={
            "job_id": state.get("job_id"),
            "target_resume_id": target_id,
            "save_applied": applied,
            "save_status": status_value,
        },
    )

    return {
        "final_resume_id": target_id,
        "save_applied": applied,
        "status": "saved" if applied else "cancelled",
    }
```

- [ ] **Step 7.4: Write failing test (T2)**

Append to `test/test_resume_lifecycle_foundation.py`:

```python
# ─────────────────────────────────────────────────────────────────
# 5.  node_save — UPDATE via complete_tailored_resume, not INSERT
# ─────────────────────────────────────────────────────────────────
class TestNodeSaveUsesUpdate(unittest.TestCase):

    @patch("agents.tailoring_subgraph.complete_tailored_resume")
    def test_node_save_calls_complete_tailored_resume(self, mock_complete):
        """T2: node_save delegates to the CAS UPDATE helper, not the
        removed save_tailored_resume INSERT path."""
        from agents.tailoring_subgraph import node_save

        mock_complete.return_value = True
        state = {
            "target_resume_id": "r-abc",
            "draft_resume": {"basics": {"name": "Test"}},
            "edit_plan": {"edits": []},
            "revision_count": 1,
            "job_id": "j-1",
            # is_force_save uses state['critique'] + revision count;
            # supply benign values so it returns False.
            "critique": [],
        }
        out = node_save(state)

        mock_complete.assert_called_once()
        kwargs = mock_complete.call_args.kwargs
        self.assertEqual(kwargs["resume_id"], "r-abc")
        self.assertEqual(kwargs["status"], "pending")
        self.assertEqual(out["final_resume_id"], "r-abc")
        self.assertTrue(out["save_applied"])
        self.assertEqual(out["status"], "saved")

    @patch("agents.tailoring_subgraph.complete_tailored_resume")
    def test_node_save_reflects_cas_no_op_in_status(self, mock_complete):
        """When CAS no-ops, node_save returns status='cancelled' so the
        worker can report task as cancelled, not completed."""
        from agents.tailoring_subgraph import node_save

        mock_complete.return_value = False
        out = node_save({
            "target_resume_id": "r-x",
            "draft_resume": {},
            "edit_plan": None,
            "revision_count": 0,
            "job_id": "j-2",
            "critique": [],
        })
        self.assertFalse(out["save_applied"])
        self.assertEqual(out["status"], "cancelled")
```

- [ ] **Step 7.5: Run tests**

```bash
pytest test/test_resume_lifecycle_foundation.py::TestNodeSaveUsesUpdate -v
```

Expected: 2 tests PASS. If `is_force_save` import errors, ensure `complete_tailored_resume` is imported inside the function body (not at module top) so the test's `@patch("agents.tailoring_subgraph.complete_tailored_resume")` resolves — adjust to import at module top if needed, but keep the patch path consistent.

- [ ] **Step 7.6: Commit**

```bash
git add agents/tailoring_subgraph.py test/test_resume_lifecycle_foundation.py
git commit -m "feat(subgraph): node_save UPDATEs placeholder via CAS helper

TailoringState gains target_resume_id (set by worker at entry) and
save_applied (set by node_save based on CAS UPDATE outcome). node_save
no longer INSERTs — it delegates to complete_tailored_resume. The
returned 'status' field is 'saved' on success, 'cancelled' on CAS no-op,
which the worker uses to choose the correct task terminal status."
```

---

## Task 8: Worker placeholder + `progress()` helper + try/finally (T6, T10)

**Files:**
- Modify: `api/routes/resumes.py` (`run_tailoring_worker`, around lines 294–403)
- Modify: `test/test_resume_lifecycle_foundation.py`

- [ ] **Step 8.1: Rewrite `run_tailoring_worker`**

Replace the existing `run_tailoring_worker` (lines 294–403 in `api/routes/resumes.py`) with:

```python
def run_tailoring_worker(task_id: str, job_id: str, initial_state: dict):
    """Background worker that runs tailoring pipeline with per-stage
    progress, cancellation, and placeholder-row lifecycle.

    Creates a placeholder resumes row at entry (so v_jobs_enriched shows
    'processing' immediately). On user cancel (tasks.status='cancelled'),
    the finally block marks the resume row cancelled via CAS, so the UI
    flips to 'cancelled' at zero latency rather than waiting for the
    next worker boundary (or up to 15m for the reaper)."""
    from agents.database import (
        save_task_status, get_task_status,
        create_processing_placeholder, mark_resume_cancelled,
    )
    from agents.tailoring_subgraph import (
        node_plan, node_draft, node_validate, node_critique, node_save,
        route_validate, route_critique,
    )

    resume_id = create_processing_placeholder(job_id)
    state = dict(initial_state)
    state["target_resume_id"] = resume_id
    state.setdefault("errors", [])
    state.setdefault("status", "queued")
    state.setdefault("draft_resume", {})
    state.setdefault("final_resume_id", "")
    state.setdefault("save_applied", False)

    def progress(completed: int, stage: str, **extra) -> dict:
        """Threads job_id + resume_id into every progress payload so the
        cancel endpoint can route back to the in-flight resume row."""
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

        result = node_plan(state)
        state.update(result)
        if state.get("errors"):
            save_task_status(task_id, "failed", progress(0, "planning"),
                             error="; ".join(state["errors"]))
            return

        # --- Stage 2: Drafting + Validation (may loop) ---
        save_task_status(task_id, "running", progress(1, "drafting"))
        if is_cancelled(): return

        result = node_draft(state)
        state.update(result)
        if state.get("errors"):
            save_task_status(task_id, "failed", progress(1, "drafting"),
                             error="; ".join(state["errors"]))
            return

        result = node_validate(state)
        state.update(result)

        route = route_validate(state)
        while route == "revise":
            if is_cancelled(): return
            result = node_draft(state)
            state.update(result)
            if state.get("errors"):
                save_task_status(task_id, "failed", progress(1, "drafting"),
                                 error="; ".join(state["errors"]))
                return
            result = node_validate(state)
            state.update(result)
            route = route_validate(state)

        if route == "error":
            save_task_status(task_id, "failed", progress(1, "drafting"),
                             error="; ".join(state.get("errors", ["Unknown error"])))
            return

        # --- Stage 3: Critiquing (may loop back to draft) ---
        save_task_status(task_id, "running", progress(2, "critiquing"))
        if is_cancelled(): return

        result = node_critique(state)
        state.update(result)
        if state.get("errors"):
            save_task_status(task_id, "failed", progress(2, "critiquing"),
                             error="; ".join(state["errors"]))
            return

        route = route_critique(state)
        while route == "revise":
            if is_cancelled(): return
            save_task_status(task_id, "running", progress(2, "revising"))
            result = node_draft(state)
            state.update(result)
            if state.get("errors"):
                save_task_status(task_id, "failed", progress(2, "revising"),
                                 error="; ".join(state["errors"]))
                return
            result = node_validate(state)
            state.update(result)
            result = node_critique(state)
            state.update(result)
            if state.get("errors"):
                save_task_status(task_id, "failed", progress(2, "critiquing"),
                                 error="; ".join(state["errors"]))
                return
            route = route_critique(state)

        if route == "error":
            save_task_status(task_id, "failed", progress(2, "critiquing"),
                             error="; ".join(state.get("errors", ["Unknown error"])))
            return

        # --- Stage 4: Saving ---
        save_task_status(task_id, "running", progress(3, "saving"))
        if is_cancelled(): return

        result = node_save(state)
        state.update(result)
        if state.get("errors"):
            save_task_status(task_id, "failed", progress(3, "saving"),
                             error="; ".join(state["errors"]))
            return

        # T10: reaper-race or user-cancel race during save → not 'completed'
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
        # Do NOT mark resume cancelled on exception — exceptions are
        # involuntary; reaper handles the row after the timeout.
    finally:
        # T6: user cancel → immediately flip resume row to cancelled.
        if is_cancelled():
            try:
                if mark_resume_cancelled(resume_id):
                    logger.info(
                        "tailoring.cancelled_by_user",
                        extra={
                            "task_id": task_id, "job_id": job_id,
                            "resume_id": resume_id,
                        },
                    )
            except Exception:
                logger.exception(
                    "Failed to mark resume cancelled in finally",
                    extra={"resume_id": resume_id},
                )
```

- [ ] **Step 8.2: Write tests T6 and T10**

Append to `test/test_resume_lifecycle_foundation.py`:

```python
# ─────────────────────────────────────────────────────────────────
# 6.  run_tailoring_worker — placeholder + cancel + reaper-race
# ─────────────────────────────────────────────────────────────────
class TestRunTailoringWorker(unittest.TestCase):

    # NOTE on patch paths: run_tailoring_worker does its imports inside the
    # function body (existing pattern, not changed by this plan), so patches
    # must target the source modules (agents.database / agents.tailoring_subgraph),
    # not the api.routes.resumes namespace.
    @patch("agents.database.mark_resume_cancelled")
    @patch("agents.database.get_task_status")
    @patch("agents.database.save_task_status")
    @patch("agents.database.create_processing_placeholder")
    @patch("agents.tailoring_subgraph.node_plan")
    def test_worker_finally_marks_cancelled_on_user_cancel(
        self, mock_plan, mock_create, mock_save_task, mock_get_task, mock_mark_cancelled,
    ):
        """T6: When the task is cancelled mid-pipeline, the finally block
        calls mark_resume_cancelled on the placeholder resume row."""
        from api.routes.resumes import run_tailoring_worker

        mock_create.return_value = "r-placeholder"
        # First get_task_status (in is_cancelled) returns 'cancelled' so
        # the worker bails out after the very first stage_status write.
        mock_get_task.return_value = {"status": "cancelled"}
        mock_plan.return_value = {}  # never reached

        run_tailoring_worker(
            task_id="t-1",
            job_id="j-1",
            initial_state={"job_id": "j-1", "base_resume": {}, "approved_skills": ""},
        )

        mock_mark_cancelled.assert_called_once_with("r-placeholder")

    @patch("agents.database.mark_resume_cancelled")
    @patch("agents.database.get_task_status")
    @patch("agents.database.save_task_status")
    @patch("agents.database.create_processing_placeholder")
    @patch("agents.tailoring_subgraph.node_save")
    @patch("agents.tailoring_subgraph.node_critique")
    @patch("agents.tailoring_subgraph.route_critique")
    @patch("agents.tailoring_subgraph.node_validate")
    @patch("agents.tailoring_subgraph.route_validate")
    @patch("agents.tailoring_subgraph.node_draft")
    @patch("agents.tailoring_subgraph.node_plan")
    def test_worker_reflects_reaper_race_in_task_status(
        self,
        mock_plan, mock_draft, mock_route_validate, mock_validate,
        mock_route_critique, mock_critique, mock_save_node,
        mock_create, mock_save_task, mock_get_task, mock_mark_cancelled,
    ):
        """T10: If complete_tailored_resume returned False (signalled via
        node_save returning save_applied=False), the worker writes task
        status='cancelled', NOT 'completed'.
        """
        from api.routes.resumes import run_tailoring_worker

        mock_create.return_value = "r-placeholder"
        mock_get_task.return_value = {"status": "running"}  # never cancelled
        mock_plan.return_value = {}
        mock_draft.return_value = {}
        mock_validate.return_value = {}
        mock_route_validate.return_value = "ok"
        mock_critique.return_value = {}
        mock_route_critique.return_value = "ok"
        # node_save reports the CAS no-op:
        mock_save_node.return_value = {
            "final_resume_id": "r-placeholder",
            "save_applied": False,
            "status": "cancelled",
        }

        run_tailoring_worker(
            task_id="t-2",
            job_id="j-2",
            initial_state={"job_id": "j-2", "base_resume": {}, "approved_skills": ""},
        )

        # Last save_task_status call must be 'cancelled', not 'completed'.
        statuses = [c.args[1] for c in mock_save_task.call_args_list]
        self.assertIn("cancelled", statuses)
        self.assertNotIn("completed", statuses)
```

- [ ] **Step 8.3: Run tests**

```bash
pytest test/test_resume_lifecycle_foundation.py::TestRunTailoringWorker -v
```

Expected: 2 tests PASS. The patches target source modules (`agents.database.X`, `agents.tailoring_subgraph.X`) because `run_tailoring_worker` imports those names inside the function body — patching `api.routes.resumes.X` would not take effect.

- [ ] **Step 8.4: Commit**

```bash
git add api/routes/resumes.py test/test_resume_lifecycle_foundation.py
git commit -m "feat(worker): placeholder row + try/finally + progress(job_id, resume_id)

run_tailoring_worker now creates a placeholder resume row at entry
(so v_jobs_enriched flips to 'processing' on POST). Every progress
payload includes job_id + resume_id so the cancel endpoint can route
back to the in-flight row without a tasks.job_id schema change. On
user cancel, finally block marks the row cancelled at zero UI latency.
On CAS no-op during save (reaper or cancel race), task terminal status
is 'cancelled', not a false 'completed'."
```

---

## Task 9: Cancel endpoint marks the in-flight resume row

**Files:**
- Modify: `api/routes/tasks.py` (cancel endpoint)
- Modify: `test/test_resume_lifecycle_foundation.py`

- [ ] **Step 9.1: Locate the cancel endpoint**

```bash
grep -n "def cancel\|cancel.*task\|POST.*cancel" /Users/abhijithm/Documents/Code/TailorAI/api/routes/tasks.py
```

- [ ] **Step 9.2: Read the current cancel handler**

Open `api/routes/tasks.py` and find the cancel handler. Note the current return shape so we preserve it.

- [ ] **Step 9.3: Patch the cancel handler**

After the existing `save_task_status(task_id, "cancelled", ...)` (or equivalent UPDATE) call, add:

```python
# Phase 1 Cluster A: also mark the in-flight resume row so UI flips
# immediately without waiting for the worker's next boundary check.
from agents.database import mark_resume_cancelled, get_task_status as _get_task_status
task = _get_task_status(task_id)
progress = (task or {}).get("progress") or {}
resume_id = progress.get("resume_id")
if resume_id:
    mark_resume_cancelled(resume_id)  # CAS — no-op if already terminal
```

(If `mark_resume_cancelled` is already imported at the module level, drop the inline `from ... import`.)

- [ ] **Step 9.4: Write test**

Append to `test/test_resume_lifecycle_foundation.py`:

```python
# ─────────────────────────────────────────────────────────────────
# 7.  Cancel endpoint marks in-flight resume row
# ─────────────────────────────────────────────────────────────────
class TestCancelEndpoint(unittest.TestCase):

    @patch("api.routes.tasks.mark_resume_cancelled")
    @patch("api.routes.tasks.get_task_status")
    @patch("api.routes.tasks.save_task_status")
    def test_cancel_marks_resume_when_resume_id_in_progress(
        self, mock_save_task, mock_get_task, mock_mark_cancelled,
    ):
        from api.routes.tasks import cancel_task

        # task has progress.resume_id set (because worker writes it now).
        mock_get_task.return_value = {
            "status": "running",
            "progress": {"resume_id": "r-7", "job_id": "j-7"},
        }

        cancel_task(task_id="t-7")

        mock_mark_cancelled.assert_called_once_with("r-7")

    @patch("api.routes.tasks.mark_resume_cancelled")
    @patch("api.routes.tasks.get_task_status")
    @patch("api.routes.tasks.save_task_status")
    def test_cancel_no_op_when_progress_missing_resume_id(
        self, mock_save_task, mock_get_task, mock_mark_cancelled,
    ):
        from api.routes.tasks import cancel_task

        mock_get_task.return_value = {"status": "running", "progress": {}}
        cancel_task(task_id="t-8")

        mock_mark_cancelled.assert_not_called()
```

- [ ] **Step 9.5: Run tests**

```bash
pytest test/test_resume_lifecycle_foundation.py::TestCancelEndpoint -v
```

Expected: 2 tests PASS. If the cancel handler signature differs from `cancel_task(task_id="...")`, adapt the test arguments to match the actual function signature.

- [ ] **Step 9.6: Commit**

```bash
git add api/routes/tasks.py test/test_resume_lifecycle_foundation.py
git commit -m "feat(api): cancel endpoint also marks in-flight resume row

Reads progress.resume_id (written by the tailoring worker on every
progress tick) and calls mark_resume_cancelled. Idempotent with the
worker's finally block via CAS — only one writer wins."
```

---

## Task 10: Reaper job in scheduler (T3, T4)

**Files:**
- Modify: `services/scheduler.py` (add new job + handler function)
- Modify: `test/test_resume_lifecycle_foundation.py`

- [ ] **Step 10.1: Add the reaper handler to `services/scheduler.py`**

Add the following function in `services/scheduler.py`, after the existing `_build_trigger` helper:

```python
def reap_stale_tailoring_runs():
    """Sweep resumes rows stuck in tailoring_status='processing'.

    Timeout is operator-tunable via system_config[
    'tailoring_processing_timeout_minutes'] (default 15). Job runs every
    5 minutes (configured in start_scheduler()). Worst-case wasted-LLM
    window: 19m59s (timeout + interval).

    Per ADR-0017 the APScheduler thread does not inherit contextvars,
    so we set correlation_id explicitly at entry."""
    from datetime import datetime, timedelta, timezone
    from agents.database import get_system_config, _get_supabase
    from backend.log_context import set_correlation_id

    set_correlation_id("reaper")
    try:
        timeout_min = 15
        raw = get_system_config("tailoring_processing_timeout_minutes")
        if raw:
            try:
                timeout_min = int(raw)
            except (TypeError, ValueError):
                logger.warning(
                    "reaper.invalid_timeout_config",
                    extra={"raw_value": raw, "default_used": timeout_min},
                )
        threshold = datetime.now(timezone.utc) - timedelta(minutes=timeout_min)

        client = _get_supabase()
        result = (
            client.table("resumes")
            .update({
                "tailoring_status": "cancelled",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
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
    finally:
        set_correlation_id(None)
```

- [ ] **Step 10.2: Register the reaper job in `start_scheduler()`**

In `services/scheduler.py`, inside `start_scheduler()` after the existing `scheduler.add_job(... id="eval_worker" ...)`, append:

```python
    scheduler.add_job(
        reap_stale_tailoring_runs,
        trigger=IntervalTrigger(minutes=5),
        id="reap_stale_tailoring_runs",
        name="Tailoring Reaper",
        coalesce=True,
        max_instances=1,
        replace_existing=True,
    )
```

- [ ] **Step 10.3: Write tests T3 and T4**

Append to `test/test_resume_lifecycle_foundation.py`:

```python
# ─────────────────────────────────────────────────────────────────
# 8.  reap_stale_tailoring_runs — sweep behavior
# ─────────────────────────────────────────────────────────────────
class TestTailoringReaper(unittest.TestCase):

    @patch("services.scheduler.set_correlation_id")
    @patch("services.scheduler.get_system_config")
    @patch("services.scheduler._get_supabase")
    def test_reaper_sweeps_stale_rows(self, mock_get_supabase, mock_cfg, _mock_corr):
        """T3: WHEN processing_started_at < now() - timeout, row is
        updated to tailoring_status='cancelled'."""
        from services.scheduler import reap_stale_tailoring_runs

        mock_cfg.return_value = "15"
        chain = _mock_supabase_chain(return_data=[{"id": "r1"}, {"id": "r2"}])
        mock_get_supabase.return_value.table.return_value = chain

        reap_stale_tailoring_runs()

        update_kwargs = chain.update.call_args[0][0]
        self.assertEqual(update_kwargs["tailoring_status"], "cancelled")
        chain.eq.assert_any_call("tailoring_status", "processing")
        # Verify a .lt() filter is applied on processing_started_at.
        lt_calls = [c.args for c in chain.lt.call_args_list]
        self.assertTrue(
            any(c[0] == "processing_started_at" for c in lt_calls),
            "Expected .lt('processing_started_at', threshold) in builder chain",
        )

    @patch("services.scheduler.set_correlation_id")
    @patch("services.scheduler.get_system_config")
    @patch("services.scheduler._get_supabase")
    def test_reaper_default_timeout_when_config_missing(
        self, mock_get_supabase, mock_cfg, _mock_corr,
    ):
        """T4 part 1: When system_config is empty, reaper falls back to
        15 minutes — verified by checking the .lt() threshold is roughly
        15m ago (within tolerance)."""
        from services.scheduler import reap_stale_tailoring_runs

        mock_cfg.return_value = None
        chain = _mock_supabase_chain(return_data=[])
        mock_get_supabase.return_value.table.return_value = chain

        reap_stale_tailoring_runs()

        # Pull the threshold passed to .lt() and check it is ~15m in past.
        lt_args = chain.lt.call_args[0]
        self.assertEqual(lt_args[0], "processing_started_at")
        threshold_iso = lt_args[1]
        threshold = datetime.fromisoformat(threshold_iso)
        now = datetime.now(timezone.utc)
        delta = now - threshold
        self.assertGreater(delta.total_seconds(), 14 * 60)
        self.assertLess(delta.total_seconds(), 16 * 60)

    @patch("services.scheduler.set_correlation_id")
    @patch("services.scheduler.get_system_config")
    @patch("services.scheduler._get_supabase")
    def test_reaper_invalid_config_falls_back_to_default(
        self, mock_get_supabase, mock_cfg, _mock_corr,
    ):
        """T4 part 2: Garbage in system_config doesn't crash the reaper —
        it warns and uses the 15-minute default."""
        from services.scheduler import reap_stale_tailoring_runs

        mock_cfg.return_value = "not-a-number"
        chain = _mock_supabase_chain(return_data=[])
        mock_get_supabase.return_value.table.return_value = chain

        # Should not raise.
        reap_stale_tailoring_runs()
```

- [ ] **Step 10.4: Run tests**

```bash
pytest test/test_resume_lifecycle_foundation.py::TestTailoringReaper -v
```

Expected: 3 tests PASS. If `_get_supabase` is private and not exposed from `services.scheduler`, patch its real source: `agents.database._get_supabase`.

- [ ] **Step 10.5: Commit**

```bash
git add services/scheduler.py test/test_resume_lifecycle_foundation.py
git commit -m "feat(scheduler): add reap_stale_tailoring_runs APScheduler job

Sweeps resumes rows stuck in tailoring_status='processing' past the
operator-tunable timeout (system_config 'tailoring_processing_timeout_minutes',
default 15). Interval 5 minutes; coalesce + max_instances=1; sets
correlation_id='reaper' per ADR-0017. Logs reaper.cancelled_stale_processing
on every non-empty sweep."
```

---

## Task 11: Integration tests (T7, T8, T9) — skip without DB

**Files:**
- Modify: `test/test_resume_lifecycle_foundation.py`

These tests need a real Supabase connection. Skipped when `SUPABASE_URL` is not set; CI / local runs without the env var still pass the unit-test suite.

- [ ] **Step 11.1: Append integration test class**

Append to `test/test_resume_lifecycle_foundation.py`:

```python
# ─────────────────────────────────────────────────────────────────
# 9.  Integration tests (real Supabase) — skipped when env unset
# ─────────────────────────────────────────────────────────────────
@unittest.skipUnless(
    os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_KEY"),
    "Supabase env vars not set — skipping integration tests",
)
class TestPhase1Integration(unittest.TestCase):
    """T7, T8, T9: real-DB checks. Requires migrations 016-020 applied
    against the target Supabase project."""

    def setUp(self):
        from agents.database import _get_supabase
        self.client = _get_supabase()

    def test_status_check_rejects_invalid_value(self):
        """T7: DB CHECK rejects status outside the allowed vocabulary."""
        from postgrest.exceptions import APIError
        import uuid

        bad = {
            "id": str(uuid.uuid4()),
            "name": "T7 bad status",
            "content": {},
            "status": "definitely-not-a-real-status",
        }
        with self.assertRaises(APIError):
            self.client.table("resumes").insert(bad).execute()

    def test_master_coupling_check_rejects(self):
        """T8: cannot set job_id on a master row, nor status='master' on
        a row with a non-null job_id."""
        from postgrest.exceptions import APIError
        import uuid

        bad = {
            "id": str(uuid.uuid4()),
            "name": "T8 master with job_id",
            "content": {},
            "status": "master",
            "job_id": "some-job",
            "tailoring_status": "not_started",
        }
        with self.assertRaises(APIError):
            self.client.table("resumes").insert(bad).execute()

    def test_preflight_audit_query_succeeds(self):
        """T9: queries in 016_phase1_preflight_audit.sql parse and run.

        We execute the equivalent SELECTs through the Supabase client and
        confirm both return rows (or empty results) without raising.
        """
        r1 = self.client.table("resumes").select("status").execute()
        self.assertIsNotNone(r1.data)

        r2 = (
            self.client.table("resumes")
            .select("id, status, tailoring_status, job_id")
            .eq("status", "master")
            .execute()
        )
        # Any master row must already satisfy the coupling invariant.
        for row in r2.data or []:
            self.assertEqual(row.get("tailoring_status"), "not_started")
            self.assertIsNone(row.get("job_id"))
```

- [ ] **Step 11.2: Run the integration tests if `.env` has Supabase creds**

```bash
pytest test/test_resume_lifecycle_foundation.py::TestPhase1Integration -v
```

Expected: 3 tests PASS, **only if** migrations 017–020 are applied against the target Supabase. Otherwise skipped or T7/T8 fail (DB still permits invalid statuses).

- [ ] **Step 11.3: Run the full suite**

```bash
pytest test/test_resume_lifecycle_foundation.py -v
```

Expected: 5 unit-test classes (~13 tests) PASS; integration class either PASS (post-migration) or SKIP (no env).

- [ ] **Step 11.4: Commit**

```bash
git add test/test_resume_lifecycle_foundation.py
git commit -m "test: add integration tests T7, T8, T9 for Phase 1 CHECKs

Skipped when SUPABASE_URL is unset so local + CI runs without DB
remain green. Verifies that migrations 017 and 018 actually enforce
the vocabulary + master-row invariants in the live schema."
```

---

## Task 12: Documentation sync — CLAUDE.md + active doc + ADR-0022

**Files:**
- Modify: `agents/CLAUDE.md`
- Modify: `api/CLAUDE.md`
- Modify: `services/CLAUDE.md`
- Modify: `CLAUDE.md` (project root)
- Create: `docs/active/phase1-schema-foundation.md`
- Create: `docs/decisions/ADR-0022-tailoring-placeholder-row.md`

- [ ] **Step 12.1: Create ADR-0022**

Write `docs/decisions/ADR-0022-tailoring-placeholder-row.md`:

```markdown
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
```

- [ ] **Step 12.2: Create the active doc**

Write `docs/active/phase1-schema-foundation.md`:

```markdown
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
```

- [ ] **Step 12.3: Add the active doc and ADR to root `CLAUDE.md`**

In `CLAUDE.md`, find the `## Active tasks` list and append:

```markdown
- `docs/active/phase1-schema-foundation.md` — Phase 1 Cluster A: schema foundation 🟡
```

In the `## Architecture decisions` section, append:

```markdown
- ADR-0022: Tailoring uses placeholder-row lifecycle (create at worker entry → CAS UPDATE at node_save → reaper sweeps stale rows after operator-tunable timeout).
```

- [ ] **Step 12.4: Update `agents/CLAUDE.md`**

In `agents/CLAUDE.md`, replace the section titled `## DB helper: \`save_tailored_resume\`` (the part that describes `save_tailored_resume`) with a new section:

```markdown
## Tailoring lifecycle helpers (ADR-0022)

`save_tailored_resume` is REMOVED — calling it raises `NotImplementedError`.
The tailoring lifecycle is now three helpers:

| Helper | When | Returns |
|--------|------|---------|
| `create_processing_placeholder(job_id) -> resume_id` | Worker entry (before subgraph) | Placeholder row id |
| `complete_tailored_resume(resume_id, version, content, status, edit_plan) -> bool` | `node_save` at end-of-pipeline | True on CAS apply, False on no-op (reaper/cancel race) |
| `mark_resume_cancelled(resume_id) -> bool` | Cancel endpoint, worker `finally`, reaper | True if THIS call won the CAS |

All three use CAS predicate `WHERE tailoring_status = 'processing'` so the
three writers (worker save, user cancel, reaper sweep) interleave safely.

`TailoringState` has two required new fields: `target_resume_id` (set by the
worker at entry) and `save_applied` (set by `node_save` from the CAS UPDATE
return value). The worker reads `state["save_applied"]` to decide whether
the task ended in `completed` or `cancelled`.
```

- [ ] **Step 12.5: Update `api/CLAUDE.md`**

In `api/CLAUDE.md`, in the `## Background task pattern (full sequence)` section, append:

```markdown
**Progress payload convention (ADR-0022):** the tailoring worker writes
`job_id` and `resume_id` into every `save_task_status(task_id, status, progress)`
call's `progress` dict. The cancel endpoint reads `progress.resume_id` to
mark the in-flight resume row cancelled at zero UI latency. New workers
that own a resumes row should follow the same convention.
```

- [ ] **Step 12.6: Update `services/CLAUDE.md`**

In `services/CLAUDE.md`, in the `## Scheduler pattern` section, append:

```markdown
**Phase 1 Cluster A job (ADR-0022):** `reap_stale_tailoring_runs`
sweeps `resumes` rows stuck in `tailoring_status='processing'` past
`system_config['tailoring_processing_timeout_minutes']` (default 15).
Interval 5 minutes; `coalesce=True`, `max_instances=1`. Per ADR-0017
the APScheduler thread doesn't inherit contextvars, so the reaper sets
`set_correlation_id("reaper")` at entry and clears it in `finally`.
```

- [ ] **Step 12.7: Commit docs**

```bash
git add docs/decisions/ADR-0022-tailoring-placeholder-row.md \
        docs/active/phase1-schema-foundation.md \
        agents/CLAUDE.md api/CLAUDE.md services/CLAUDE.md CLAUDE.md
git commit -m "docs(phase1): add ADR-0022, active doc, and CLAUDE.md sync

ADR-0022 records the placeholder-row decision over separate-table and
tasks-only alternatives. agents/api/services CLAUDE.md sections updated
to document the three new helpers, the progress-payload convention,
and the reaper job."
```

---

## Task 13: Final verification — full test suite + manual smoke commands

- [ ] **Step 13.1: Run the full project test suite to confirm no regression**

```bash
cd /Users/abhijithm/Documents/Code/TailorAI
pytest -v
```

Expected: all existing tests still PASS, plus our new `test_resume_lifecycle_foundation.py` tests PASS.

- [ ] **Step 13.2: Lint and format**

```bash
ruff check agents/database.py agents/tailoring_subgraph.py \
           api/routes/resumes.py api/routes/tasks.py services/scheduler.py \
           test/test_resume_lifecycle_foundation.py
ruff format --check agents/database.py agents/tailoring_subgraph.py \
                    api/routes/resumes.py api/routes/tasks.py services/scheduler.py \
                    test/test_resume_lifecycle_foundation.py
```

Expected: no errors. If `ruff format --check` reports formatting drift, run without `--check` and inspect the changes before committing.

- [ ] **Step 13.3: Stage and commit any formatting changes**

```bash
git add -A
git diff --cached --stat
# If diff is non-empty:
git commit -m "style: ruff format Phase 1 Cluster A files"
```

- [ ] **Step 13.4: Push the branch**

```bash
git push -u origin feature/phase1-schema-foundation
```

- [ ] **Step 13.5: Open the PR**

```bash
gh pr create --base main --head feature/phase1-schema-foundation \
  --title "Phase 1 Cluster A — Schema foundation + tailoring placeholder lifecycle" \
  --body "$(cat <<'EOF'
## Summary

Cluster A of the Phase 1 domain-spec roadmap. Resolves R-RES-01, R-RES-02,
R-RES-05, R-RES-07. Spec at
`docs/superpowers/specs/2026-05-26-phase1-schema-foundation-design.md`.

- **Migrations 016–020** (manual-apply): preflight audit (no DDL),
  CHECK on `resumes.status` vocabulary, `master` row coupling invariant,
  `processing_started_at` column + reaper index + `system_config` seed,
  and an extension of `tasks.status` CHECK to include `cancelled`
  (which was already being written but silently rejected at DB level).
- **Placeholder-row lifecycle (ADR-0022)**: `save_tailored_resume` is
  REMOVED and replaced by three helpers (`create_processing_placeholder`,
  `complete_tailored_resume`, `mark_resume_cancelled`). All UPDATE
  helpers use CAS predicate `WHERE tailoring_status='processing'` so
  worker, cancel endpoint, and reaper interleave safely.
- **Reaper job**: `services/scheduler.py:reap_stale_tailoring_runs`
  runs every 5 minutes with an operator-tunable timeout
  (`system_config['tailoring_processing_timeout_minutes']`, default 15).
- **Worker rewrite**: `run_tailoring_worker` creates a placeholder row
  at entry, threads `job_id` + `resume_id` through every progress
  payload, wraps the body in `try/finally`, and treats `node_save`'s
  `save_applied=False` as a `cancelled` terminal status (not `completed`).
- **Cancel endpoint**: reads `progress.resume_id` and marks the
  in-flight resume row cancelled at zero UI latency.

## Test plan

- [ ] Unit tests pass: `pytest test/test_resume_lifecycle_foundation.py -v`
- [ ] Existing suite has no regressions: `pytest -v`
- [ ] After operator applies migrations 016–020, integration tests pass:
      `SUPABASE_URL=… SUPABASE_SERVICE_KEY=… pytest test/test_resume_lifecycle_foundation.py::TestPhase1Integration -v`
- [ ] Manual smoke: POST `/api/resumes/tailor/{job_id}` → observe a row
      appears immediately with `tailoring_status='processing'` and
      `processing_started_at` populated.
- [ ] Manual smoke: trigger cancel mid-pipeline →
      `tailoring_status` flips to `cancelled` within a second.
- [ ] Manual smoke: set
      `system_config['tailoring_processing_timeout_minutes']` = `'1'`,
      start a tailoring run, wait > 6 minutes →
      reaper marks the row `cancelled` and logs
      `reaper.cancelled_stale_processing` with `count=1`.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Expected: PR URL printed.

---

## Out of scope (deferred to later clusters / phases)

| Deferred to | Item |
|-------------|------|
| Cluster B | Per-job claim lock + UNIQUE partial index on `(job_id) WHERE tailoring_status='processing'` (R-RES-12) |
| Cluster B | Stale `base_resume` mid-pipeline (R-RES-13) |
| Cluster C | Validator correctness (R-RES-09, R-RES-10, R-RES-11) |
| Cluster D | Critic JSON parsing + GDoc orphan cleanup (R-RES-15, R-RES-16) |
| Cluster E | `resume_changes` UX integrity (R-CHG-01, R-CHG-04, R-CHG-07) |
| Cluster F | PII redaction (R-RES-18) |
| Phase 2 | The rest of the TASK aggregate fixes (R-TASK-01 was partially pulled in via migration 020 only because cancel-during-tailoring depended on it) |
