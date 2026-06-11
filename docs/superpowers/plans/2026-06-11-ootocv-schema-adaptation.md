# OotoCV Schema Adaptation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing TailorAI schema and API so the OotoCV UI design (runs feed, 4-way verdict, per-stage pipeline modes, application tracker + offer state, change feedback chips, transient resume roast) is fully backable, with no breaking changes to existing routes.

**Architecture:** Five additive migrations (021–025) plus convention-only JSONB shape changes for gap structure. Three new API resources (`/api/runs`, `/api/pipeline/config`, `/api/resumes/roast`), four endpoint response-shape extensions, and two evaluator prompt updates. All changes idempotent (`IF NOT EXISTS`, `ON CONFLICT DO NOTHING`) and backward compatible — historical rows stay valid under the extended CHECK constraints.

**Tech Stack:** PostgreSQL (Supabase), FastAPI, supabase-py, APScheduler, LangGraph, pytest (unittest-style), OpenRouter for evaluator LLM.

**Source spec:** `/Users/abhijithm/.claude/plans/resilient-sleeping-gray.md` and `docs/superpowers/specs/` (to be created during this work).

---

## File Structure

### Migrations (create)
- `supabase_db/migrations/021_jobs_run_id.sql` — `jobs.run_id` FK + index
- `supabase_db/migrations/022_evaluations_verdict_extension.sql` — extend `recommended_action` enum to 4 values; add `top_strength` / `deciding_factor` / `kill_shot` / `red_flags` columns
- `supabase_db/migrations/023_applications_offer_status.sql` — add `offer` to applications.status CHECK
- `supabase_db/migrations/024_resume_changes_feedback.sql` — `feedback_type` / `regenerated_at` / `regeneration_count` columns
- `supabase_db/migrations/025_system_config_pipeline_modes.sql` — seed three pipeline_*_mode rows

### Backend (modify)
- `agents/database.py` — new helpers: `list_runs()`, `get_run(run_id)`, `get_pipeline_config()`, `set_pipeline_config()`, `compute_ghost_commentary(days)`, `record_change_feedback(change_id, feedback_type)`
- `agents/evaluator.py` + `agent_prompts/evaluator.txt` — emit 4 new fields, support borderline/apply_direct verdicts, gap.strategy / gap.severity
- `services/scraper_worker.py` — stamp `jobs.run_id = current_pipeline_runs.id` on insert
- `services/scheduler.py` — read `pipeline_scrape_mode` / `pipeline_evaluate_mode` and no-op when `manual`
- `api/routes/applications.py` — add `ghost_commentary` + `days_since_update` to response; allow `offer` status
- `api/routes/resumes.py` — accept `feedback_type` on change reject + add roast endpoint
- `api/routes/scheduler.py` — add `/api/system/status` alias with `{cron_state, next_run_at, last_error}` shape
- `api/main.py` — register new routers

### Backend (create)
- `api/routes/runs.py` — GET `/api/runs`, GET `/api/runs/{id}`
- `api/routes/pipeline_config.py` — GET/PATCH `/api/pipeline/config`

### Tests (create)
- `test/test_ootocv_schema.py` — DB-level CHECK constraint tests + helper unit tests
- `test/test_runs_api.py` — runs endpoint contract test
- `test/test_pipeline_config_api.py` — pipeline-config endpoint contract test
- `test/test_applications_offer_and_commentary.py` — offer status + ghost_commentary computation
- `test/test_change_feedback.py` — feedback_type capture + regeneration_count bump

### ADRs (create)
- `docs/decisions/ADR-0023-four-way-verdict-card-lines.md`
- `docs/decisions/ADR-0024-per-stage-pipeline-mode.md`
- `docs/decisions/ADR-0025-run-as-first-class-entity.md`

---

## Phase 1: Migrations (executed first)

### Task 1: Migration 021 — jobs.run_id

**Files:**
- Create: `supabase_db/migrations/021_jobs_run_id.sql`

- [ ] **Step 1: Write the migration**

```sql
-- Migration 021: Link jobs to the pipeline_runs row that produced them.
-- Powers the OotoCV feed grouping ("Today · 5:00 PM" separators + action band).
-- Backfill strategy: leave NULL on historical rows; UI groups them under
-- a "Pre-runs" bucket. After two new scrape cycles the bucket is cosmetic.

ALTER TABLE jobs
  ADD COLUMN IF NOT EXISTS run_id UUID REFERENCES pipeline_runs(id);

COMMENT ON COLUMN jobs.run_id IS
  'pipeline_runs.id of the scrape run that produced this job. '
  'NULL for legacy rows imported before run-linking. '
  'Only stamped by ScrapeWorker; never re-stamped by other workers.';

CREATE INDEX IF NOT EXISTS idx_jobs_run_id ON jobs(run_id);
```

- [ ] **Step 2: Apply via Supabase SQL editor and confirm**

```sql
-- In Supabase SQL editor, verify:
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'jobs' AND column_name = 'run_id';
-- Expect: 1 row, data_type=uuid, is_nullable=YES

SELECT indexname FROM pg_indexes
WHERE tablename = 'jobs' AND indexname = 'idx_jobs_run_id';
-- Expect: 1 row
```

- [ ] **Step 3: Commit**

```bash
git add supabase_db/migrations/021_jobs_run_id.sql
git commit -m "feat(db): migration 021 — jobs.run_id FK for run-grouped feed"
```

---

### Task 2: Migration 022 — verdict extension + card-line columns

**Files:**
- Create: `supabase_db/migrations/022_evaluations_verdict_extension.sql`

- [ ] **Step 1: Write the migration**

```sql
-- Migration 022: 4-way verdict + pre-computed card-line summaries.
-- Extends recommended_action from {apply, tailor, skip} to
-- {tailor, borderline, apply_direct, skip}. Adds three card-line text
-- columns (one populated per verdict) and red_flags array for SKIP layout.
--
-- Backward compat: historical rows keep their 3-value action. The new
-- CHECK accepts both old and new vocab during the transition; a later
-- migration can tighten once historical rows are re-evaluated or
-- explicitly remapped.

-- Drop and re-create the CHECK with the union of old + new values.
ALTER TABLE job_evaluations
  DROP CONSTRAINT IF EXISTS job_evaluations_recommended_action_check;

ALTER TABLE job_evaluations
  ADD CONSTRAINT job_evaluations_recommended_action_check
  CHECK (recommended_action IN (
    -- Legacy (kept for historical rows; new evaluator does not emit these)
    'apply',
    -- New OotoCV vocab
    'tailor', 'borderline', 'apply_direct', 'skip'
  ));

ALTER TABLE job_evaluations
  ADD COLUMN IF NOT EXISTS top_strength    TEXT,
  ADD COLUMN IF NOT EXISTS deciding_factor TEXT,
  ADD COLUMN IF NOT EXISTS kill_shot       TEXT,
  ADD COLUMN IF NOT EXISTS red_flags       JSONB DEFAULT '[]'::jsonb;

COMMENT ON COLUMN job_evaluations.top_strength IS
  'One-line strength surfaced on TAILOR cards. NULL on non-TAILOR verdicts.';
COMMENT ON COLUMN job_evaluations.deciding_factor IS
  'One-line "this is what tips it" surfaced on BORDERLINE cards. '
  'NULL on non-BORDERLINE verdicts.';
COMMENT ON COLUMN job_evaluations.kill_shot IS
  'One-line rejection reason surfaced on SKIP cards. '
  'NULL on non-SKIP verdicts.';
COMMENT ON COLUMN job_evaluations.red_flags IS
  'Array of "Label — explanation" strings for the SKIP layout. '
  'Em-dash format is load-bearing — frontend splits on " — ".';
```

- [ ] **Step 2: Apply via Supabase SQL editor and confirm**

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'job_evaluations'
  AND column_name IN ('top_strength', 'deciding_factor', 'kill_shot', 'red_flags')
ORDER BY column_name;
-- Expect 4 rows.

-- Confirm CHECK accepts new values:
SELECT pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conname = 'job_evaluations_recommended_action_check';
-- Expect string containing 'borderline' and 'apply_direct'.
```

- [ ] **Step 3: Commit**

```bash
git add supabase_db/migrations/022_evaluations_verdict_extension.sql
git commit -m "feat(db): migration 022 — 4-way verdict + card-line columns"
```

---

### Task 3: Migration 023 — applications.offer status

**Files:**
- Create: `supabase_db/migrations/023_applications_offer_status.sql`

- [ ] **Step 1: Write the migration**

```sql
-- Migration 023: Allow 'offer' in applications.status (OotoCV celebration state).
-- One-line CHECK extension; no data backfill needed.

ALTER TABLE applications
  DROP CONSTRAINT IF EXISTS applications_status_check;

ALTER TABLE applications
  ADD CONSTRAINT applications_status_check
  CHECK (status IN (
    'applied', 'replied', 'interview', 'rejected', 'ghosting', 'offer'
  ));

COMMENT ON CONSTRAINT applications_status_check ON applications IS
  'OotoCV status set. "offer" added 2026-06; renders with pulse animation in tracker.';
```

- [ ] **Step 2: Apply via Supabase SQL editor and confirm**

```sql
SELECT pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conname = 'applications_status_check';
-- Expect string containing 'offer'.

-- Sanity insert (rollback after):
BEGIN;
INSERT INTO applications (job_id, job_title, company_name, status, applied_at, status_history)
VALUES ('test-offer', 'Test', 'Test Co', 'offer', NOW(), '[]'::jsonb);
ROLLBACK;
-- Expect: INSERT succeeds (no CHECK violation), then ROLLBACK.
```

- [ ] **Step 3: Commit**

```bash
git add supabase_db/migrations/023_applications_offer_status.sql
git commit -m "feat(db): migration 023 — applications.offer status"
```

---

### Task 4: Migration 024 — resume_changes feedback + regeneration

**Files:**
- Create: `supabase_db/migrations/024_resume_changes_feedback.sql`

- [ ] **Step 1: Write the migration**

```sql
-- Migration 024: Capture feedback chip on rejected changes + track regenerations.
-- Powers the OotoCV TailoringReview reject flow ("Too formal" / "Not accurate" / "Other")
-- and lets the UI cap regeneration retries (default cap: 2) before falling back
-- to manual edit.

ALTER TABLE resume_changes
  ADD COLUMN IF NOT EXISTS feedback_type      TEXT,
  ADD COLUMN IF NOT EXISTS regenerated_at     TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS regeneration_count INTEGER NOT NULL DEFAULT 0;

ALTER TABLE resume_changes
  DROP CONSTRAINT IF EXISTS resume_changes_feedback_type_check;

ALTER TABLE resume_changes
  ADD CONSTRAINT resume_changes_feedback_type_check
  CHECK (feedback_type IS NULL OR feedback_type IN (
    'too_formal', 'not_accurate', 'other'
  ));

COMMENT ON COLUMN resume_changes.feedback_type IS
  'Reason the user rejected this change. NULL until the user picks a chip. '
  'Triggers a regeneration when set on a reject.';
COMMENT ON COLUMN resume_changes.regenerated_at IS
  'Last time tailored_text was replaced by a regeneration. NULL = never regenerated.';
COMMENT ON COLUMN resume_changes.regeneration_count IS
  'Number of regenerations applied. Capped at 2 by api/routes/resumes.py; '
  'after that the UI shows "edit manually".';
```

- [ ] **Step 2: Apply via Supabase SQL editor and confirm**

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'resume_changes'
  AND column_name IN ('feedback_type', 'regenerated_at', 'regeneration_count')
ORDER BY column_name;
-- Expect 3 rows.
```

- [ ] **Step 3: Commit**

```bash
git add supabase_db/migrations/024_resume_changes_feedback.sql
git commit -m "feat(db): migration 024 — resume_changes feedback chip + regeneration"
```

---

### Task 5: Migration 025 — system_config pipeline modes

**Files:**
- Create: `supabase_db/migrations/025_system_config_pipeline_modes.sql`

- [ ] **Step 1: Write the migration**

```sql
-- Migration 025: Per-stage pipeline mode seeds.
-- These are distinct from kill switches (service_*_enabled, ADR-0019):
--   * mode  = "should the agent run this stage automatically?" (user-facing toggle)
--   * kill  = "is this external service available?" (operator-facing safety)
-- Surfaced as the Scrape/Evaluate/Tailor pills in the OotoCV feed header.
--
-- Defaults: scrape and evaluate run on cron (auto); tailoring stays manual
-- until the user explicitly opts in via the auto_send_threshold consent
-- modal (ADR-0012).

INSERT INTO system_config (key, value) VALUES
  ('pipeline_scrape_mode',   'auto'),
  ('pipeline_evaluate_mode', 'auto'),
  ('pipeline_tailor_mode',   'manual')
ON CONFLICT (key) DO NOTHING;
```

- [ ] **Step 2: Apply via Supabase SQL editor and confirm**

```sql
SELECT key, value FROM system_config
WHERE key LIKE 'pipeline_%_mode'
ORDER BY key;
-- Expect 3 rows: pipeline_evaluate_mode=auto, pipeline_scrape_mode=auto, pipeline_tailor_mode=manual
```

- [ ] **Step 3: Commit**

```bash
git add supabase_db/migrations/025_system_config_pipeline_modes.sql
git commit -m "feat(db): migration 025 — per-stage pipeline mode seeds"
```

---

## Phase 2: Backend helpers + ADRs

### Task 6: ADR-0023 (4-way verdict + card lines)

**Files:**
- Create: `docs/decisions/ADR-0023-four-way-verdict-card-lines.md`

- [ ] **Step 1: Write the ADR**

```markdown
# ADR-0023: 4-way verdict with pre-computed card lines

**Status:** Accepted (2026-06-11)
**Context:** OotoCV redesign requires four verdicts (TAILOR / BORDERLINE / APPLY DIRECT / SKIP), each with a structurally different Job Detail layout and a single card-summary line.
**Decision:** Extend `job_evaluations.recommended_action` to four values; add `top_strength`, `deciding_factor`, `kill_shot`, `red_flags` columns. Evaluator emits these explicitly — not derived client-side.
**Consequences:**
- Evaluator prompt change; existing rows keep legacy 3-value enum (BORDERLINE backfill is user-driven via on-demand re-eval).
- Card render is a single column read; no array unpacking on the frontend.
- Red flag format (`"Label — explanation"`) is load-bearing — backend normalizes hyphens to em-dash on read.
**Alternatives rejected:**
- *Derive BORDERLINE from match_score band* — loses the agent's narrative deciding factor; can't express "high score but borderline because of culture".
- *Client-side line synthesis from gaps[]* — wastes payload; forces frontend to make editorial choices.
```

- [ ] **Step 2: Commit**

```bash
git add docs/decisions/ADR-0023-four-way-verdict-card-lines.md
git commit -m "docs(adr): ADR-0023 — 4-way verdict with card lines"
```

---

### Task 7: ADR-0024 (per-stage pipeline mode)

**Files:**
- Create: `docs/decisions/ADR-0024-per-stage-pipeline-mode.md`

- [ ] **Step 1: Write the ADR**

```markdown
# ADR-0024: Per-stage pipeline mode separate from kill switches

**Status:** Accepted (2026-06-11)
**Context:** OotoCV's feed header has three pills (`Scrape [auto] → Evaluate [auto] → Tailor [manual]`) the user toggles to control whether each stage runs automatically. This is different from the ADR-0019 kill switches.
**Decision:** Three rows in `system_config` (`pipeline_scrape_mode`, `pipeline_evaluate_mode`, `pipeline_tailor_mode`) with `auto | manual` values. Scheduler reads scrape/evaluate modes and no-ops cron firings when manual; manual triggers still work via existing `/api/scheduler/trigger/*` endpoints. `tailor_mode=auto` activates the auto-send path gated by `auto_send_threshold` (ADR-0012).
**Consequences:**
- Two-axis control: mode (user) vs kill switch (operator). Settings + logs must surface both with clearly different labels.
- Promotion to a dedicated `pipeline_config` table deferred until per-stage scheduling overrides become a requirement.
- Default `tailor_mode=manual` to prevent cost runaway from a forgotten auto_send_threshold.
**Alternatives rejected:**
- *Conflate with kill switches* — loses the user-vs-operator distinction; "I'm reviewing today" is not "the API is down".
- *New table upfront* — premature; YAGNI.
```

- [ ] **Step 2: Commit**

```bash
git add docs/decisions/ADR-0024-per-stage-pipeline-mode.md
git commit -m "docs(adr): ADR-0024 — per-stage pipeline mode"
```

---

### Task 8: ADR-0025 (run as first-class entity)

**Files:**
- Create: `docs/decisions/ADR-0025-run-as-first-class-entity.md`

- [ ] **Step 1: Write the ADR**

```markdown
# ADR-0025: Jobs are linked to a pipeline_runs row (run as first-class entity)

**Status:** Accepted (2026-06-11)
**Context:** OotoCV's feed groups jobs under run separators ("Today · 5:00 PM") with an action band per run ("2 tailor · 1 direct · 1 borderline"). The agentic story depends on runs being a unit the user sees.
**Decision:** `jobs.run_id` is a nullable FK to `pipeline_runs.id`. Only `ScrapeWorker` stamps it on insert. `GET /api/runs` returns runs + aggregated counts (single GROUP BY on the join). Existing `pipeline_runs` rows are reused — no new table.
**Consequences:**
- Historical jobs have `run_id IS NULL`; UI groups them under a "Pre-runs" bucket.
- Action band counts on a still-running run can mutate visibly. UI defers rendering counts until `finished_at IS NOT NULL` and shows "Run in progress · X / Y evaluated" instead.
- Run summary derivable in one query; no caching table needed.
**Alternatives rejected:**
- *New runs table* — duplicates pipeline_runs.
- *Stamp run_id on eval, not scrape* — re-stamping changes the user's mental model of "which batch produced this job".
```

- [ ] **Step 2: Commit**

```bash
git add docs/decisions/ADR-0025-run-as-first-class-entity.md
git commit -m "docs(adr): ADR-0025 — run as first-class entity"
```

---

### Task 9: agents/database.py helpers — runs

**Files:**
- Modify: `agents/database.py` (append new functions)
- Test: `test/test_ootocv_schema.py`

- [ ] **Step 1: Write the failing test**

```python
# test/test_ootocv_schema.py
import os, sys, unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def _mock_supabase_chain(return_data):
    final = MagicMock()
    final.execute.return_value = MagicMock(data=return_data)
    chain = MagicMock()
    for m in ("select", "eq", "order", "limit", "rpc", "insert", "update", "upsert"):
        getattr(chain, m).return_value = chain
    chain.execute = final.execute
    return chain


class TestListRuns(unittest.TestCase):
    @patch("agents.database._get_supabase")
    def test_list_runs_returns_aggregated_counts(self, mock_get_supabase):
        from agents.database import list_runs
        fake_rpc_row = [
            {
                "id": "run-1",
                "started_at": "2026-06-11T17:00:00+00:00",
                "finished_at": "2026-06-11T17:02:00+00:00",
                "status": "completed",
                "jobs_found": 8,
                "tailor_count": 2,
                "borderline_count": 1,
                "apply_direct_count": 1,
                "skip_count": 4,
            }
        ]
        chain = _mock_supabase_chain(return_data=fake_rpc_row)
        mock_get_supabase.return_value.rpc.return_value = chain
        result = list_runs(limit=10)
        self.assertEqual(result, fake_rpc_row)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest test/test_ootocv_schema.py::TestListRuns -v`
Expected: FAIL with `ImportError: cannot import name 'list_runs'`.

- [ ] **Step 3: Write the helper**

Append to `agents/database.py`:

```python
def list_runs(limit: int = 50):
    """Return recent pipeline runs with aggregated verdict counts per run.

    The action-band feature (OotoCV) needs:
      tailor / borderline / apply_direct / skip counts per run.
    These are computed via a Postgres RPC `runs_with_counts(limit_n int)`
    that does a single GROUP BY pipeline_runs.id, job_evaluations.recommended_action.
    The RPC is defined alongside migration 021 in a follow-up SQL script;
    if the RPC isn't installed, the caller gets an empty list and a logged warning.
    """
    try:
        client = _get_supabase()
        resp = client.rpc("runs_with_counts", {"limit_n": limit}).execute()
        return resp.data or []
    except Exception as exc:  # noqa: BLE001 — RPC missing or DB down
        logger.warning("list_runs failed: %s", exc)
        return []


def get_run(run_id: str):
    """Return one pipeline_runs row, or None."""
    try:
        client = _get_supabase()
        resp = (
            client.table("pipeline_runs")
            .select("*")
            .eq("id", run_id)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        return rows[0] if rows else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_run(%s) failed: %s", run_id, exc)
        return None
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest test/test_ootocv_schema.py::TestListRuns -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/database.py test/test_ootocv_schema.py
git commit -m "feat(db): list_runs / get_run helpers for OotoCV runs feed"
```

---

### Task 10: agents/database.py helpers — pipeline config

**Files:**
- Modify: `agents/database.py`
- Test: `test/test_ootocv_schema.py`

- [ ] **Step 1: Write the failing test**

Append to `test/test_ootocv_schema.py`:

```python
class TestPipelineConfig(unittest.TestCase):
    @patch("agents.database._get_supabase")
    def test_get_pipeline_config_returns_defaults_when_missing(self, mock_get_supabase):
        from agents.database import get_pipeline_config
        chain = _mock_supabase_chain(return_data=[])
        mock_get_supabase.return_value.table.return_value = chain
        cfg = get_pipeline_config()
        # Defaults match migration 025 seed defaults.
        self.assertEqual(cfg["scrape_mode"], "auto")
        self.assertEqual(cfg["evaluate_mode"], "auto")
        self.assertEqual(cfg["tailor_mode"], "manual")
        self.assertEqual(cfg["auto_send_threshold"], 0)

    @patch("agents.database._get_supabase")
    def test_set_pipeline_config_rejects_invalid_mode(self, mock_get_supabase):
        from agents.database import set_pipeline_config
        with self.assertRaises(ValueError):
            set_pipeline_config({"scrape_mode": "turbo"})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest test/test_ootocv_schema.py::TestPipelineConfig -v`
Expected: FAIL with import errors.

- [ ] **Step 3: Write the helpers**

Append to `agents/database.py`:

```python
_PIPELINE_MODE_KEYS = {
    "scrape_mode":   "pipeline_scrape_mode",
    "evaluate_mode": "pipeline_evaluate_mode",
    "tailor_mode":   "pipeline_tailor_mode",
}
_VALID_MODES = {"auto", "manual"}


def get_pipeline_config():
    """Return current pipeline mode + auto_send_threshold as a flat dict."""
    client = _get_supabase()
    keys = list(_PIPELINE_MODE_KEYS.values()) + ["auto_send_threshold"]
    resp = (
        client.table("system_config")
        .select("key,value")
        .in_("key", keys)
        .execute()
    )
    rows = {r["key"]: r["value"] for r in (resp.data or [])}
    return {
        "scrape_mode":         rows.get("pipeline_scrape_mode",   "auto"),
        "evaluate_mode":       rows.get("pipeline_evaluate_mode", "auto"),
        "tailor_mode":         rows.get("pipeline_tailor_mode",   "manual"),
        "auto_send_threshold": int(rows.get("auto_send_threshold", "0")),
    }


def set_pipeline_config(updates: dict) -> dict:
    """Validate + upsert pipeline mode rows. Returns the new config."""
    client = _get_supabase()
    for short_key, value in updates.items():
        if short_key == "auto_send_threshold":
            ival = int(value)
            if not 0 <= ival <= 4:
                raise ValueError("auto_send_threshold must be 0..4")
            client.table("system_config").upsert(
                {"key": "auto_send_threshold", "value": str(ival)},
                on_conflict="key",
            ).execute()
            continue
        if short_key not in _PIPELINE_MODE_KEYS:
            raise ValueError(f"Unknown pipeline config key: {short_key}")
        if value not in _VALID_MODES:
            raise ValueError(
                f"Invalid mode '{value}' for {short_key}; "
                f"must be one of {_VALID_MODES}"
            )
        client.table("system_config").upsert(
            {"key": _PIPELINE_MODE_KEYS[short_key], "value": value},
            on_conflict="key",
        ).execute()
    return get_pipeline_config()
```

Also extend `_mock_supabase_chain` in the test file to include `"in_"` and `"upsert"` in the method list.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest test/test_ootocv_schema.py::TestPipelineConfig -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/database.py test/test_ootocv_schema.py
git commit -m "feat(db): get_pipeline_config / set_pipeline_config helpers"
```

---

### Task 11: agents/database.py — compute_ghost_commentary

**Files:**
- Modify: `agents/database.py`
- Test: `test/test_applications_offer_and_commentary.py`

- [ ] **Step 1: Write the failing test**

```python
# test/test_applications_offer_and_commentary.py
import unittest


class TestGhostCommentary(unittest.TestCase):
    def test_brackets(self):
        from agents.database import compute_ghost_commentary
        self.assertEqual(compute_ghost_commentary(0),  "Probably just busy.")
        self.assertEqual(compute_ghost_commentary(3),  "Probably just busy.")
        self.assertEqual(compute_ghost_commentary(4),  "Still nothing. Rude, but fine.")
        self.assertEqual(compute_ghost_commentary(7),  "Still nothing. Rude, but fine.")
        self.assertEqual(compute_ghost_commentary(8),  "At this point we're assuming they lost it.")
        self.assertEqual(compute_ghost_commentary(14), "At this point we're assuming they lost it.")
        self.assertEqual(compute_ghost_commentary(15), "They don't deserve you.")
        self.assertEqual(compute_ghost_commentary(99), "They don't deserve you.")
```

- [ ] **Step 2: Run the test**

Run: `pytest test/test_applications_offer_and_commentary.py::TestGhostCommentary -v`
Expected: FAIL with import error.

- [ ] **Step 3: Write the function**

Append to `agents/database.py`:

```python
def compute_ghost_commentary(days_since_update: int) -> str:
    """Return the OotoCV-voice ghosting commentary for a given days_since_update.

    Bracketed deterministically — never store this; recompute on every read so it
    naturally ages with the application. See ADR-0023-adjacent risk R5.
    """
    if days_since_update <= 3:
        return "Probably just busy."
    if days_since_update <= 7:
        return "Still nothing. Rude, but fine."
    if days_since_update <= 14:
        return "At this point we're assuming they lost it."
    return "They don't deserve you."
```

- [ ] **Step 4: Run the test**

Run: `pytest test/test_applications_offer_and_commentary.py::TestGhostCommentary -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agents/database.py test/test_applications_offer_and_commentary.py
git commit -m "feat(db): compute_ghost_commentary brackets"
```

---

## Phase 3: API endpoints

### Task 12: GET /api/runs and /api/runs/{id}

**Files:**
- Create: `api/routes/runs.py`
- Modify: `api/main.py`
- Test: `test/test_runs_api.py`

- [ ] **Step 1: Write the failing test**

```python
# test/test_runs_api.py
import os, sys, unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestRunsRoutes(unittest.TestCase):
    @patch("api.routes.runs.list_runs")
    def test_list_runs_endpoint(self, mock_list):
        mock_list.return_value = [
            {"id": "r1", "started_at": "2026-06-11T17:00:00+00:00",
             "finished_at": "2026-06-11T17:02:00+00:00",
             "status": "completed", "jobs_found": 8,
             "tailor_count": 2, "borderline_count": 1,
             "apply_direct_count": 1, "skip_count": 4}
        ]
        from api.main import app
        client = TestClient(app)
        resp = client.get("/api/runs?limit=10")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["tailor_count"], 2)
        mock_list.assert_called_once_with(limit=10)

    @patch("api.routes.runs.get_run")
    def test_get_run_endpoint_404(self, mock_get):
        mock_get.return_value = None
        from api.main import app
        client = TestClient(app)
        resp = client.get("/api/runs/missing-id")
        self.assertEqual(resp.status_code, 404)
```

- [ ] **Step 2: Run the test**

Run: `pytest test/test_runs_api.py -v`
Expected: FAIL.

- [ ] **Step 3: Write the route**

```python
# api/routes/runs.py
"""Runs feed (OotoCV) — reads pipeline_runs joined with verdict counts."""
from fastapi import APIRouter, HTTPException, Query

from agents.database import get_run, list_runs

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("")
def get_runs(limit: int = Query(50, ge=1, le=200)):
    """Return recent runs with per-verdict aggregated counts."""
    return list_runs(limit=limit)


@router.get("/{run_id}")
def get_run_by_id(run_id: str):
    row = get_run(run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="run not found")
    return row
```

Modify `api/main.py` — add the import + `app.include_router(runs_router)`. Read `api/main.py` first to find the existing pattern; mirror it. Example diff (paths may differ):

```python
from api.routes.runs import router as runs_router
# ...
app.include_router(runs_router)
```

- [ ] **Step 4: Run the test**

Run: `pytest test/test_runs_api.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add api/routes/runs.py api/main.py test/test_runs_api.py
git commit -m "feat(api): GET /api/runs + /api/runs/{id}"
```

---

### Task 13: Postgres RPC for runs_with_counts

**Files:**
- Create: `supabase_db/migrations/021b_runs_with_counts_rpc.sql`

- [ ] **Step 1: Write the migration**

```sql
-- Migration 021b: SQL function backing list_runs() helper.
-- One aggregation query per call; no triggers, no cached counts.

CREATE OR REPLACE FUNCTION runs_with_counts(limit_n INT DEFAULT 50)
RETURNS TABLE (
  id UUID,
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ,
  status TEXT,
  jobs_found INT,
  tailor_count INT,
  borderline_count INT,
  apply_direct_count INT,
  skip_count INT
) LANGUAGE sql STABLE AS $$
  SELECT
    pr.id,
    pr.started_at,
    pr.finished_at,
    pr.status,
    pr.jobs_found,
    COUNT(*) FILTER (WHERE je.recommended_action = 'tailor')::int       AS tailor_count,
    COUNT(*) FILTER (WHERE je.recommended_action = 'borderline')::int   AS borderline_count,
    COUNT(*) FILTER (WHERE je.recommended_action = 'apply_direct')::int AS apply_direct_count,
    COUNT(*) FILTER (WHERE je.recommended_action IN ('skip'))::int      AS skip_count
  FROM pipeline_runs pr
  LEFT JOIN jobs j               ON j.run_id = pr.id
  LEFT JOIN job_evaluations je   ON je.job_id = j.id
  WHERE pr.run_type IN ('scrape', 'full_pipeline')
  GROUP BY pr.id
  ORDER BY pr.started_at DESC
  LIMIT limit_n;
$$;
```

- [ ] **Step 2: Apply via Supabase SQL editor and confirm**

```sql
SELECT * FROM runs_with_counts(5);
-- Expect: up to 5 rows, even before the new evaluator fields are populated.
```

- [ ] **Step 3: Commit**

```bash
git add supabase_db/migrations/021b_runs_with_counts_rpc.sql
git commit -m "feat(db): runs_with_counts RPC for /api/runs aggregation"
```

---

### Task 14: GET/PATCH /api/pipeline/config

**Files:**
- Create: `api/routes/pipeline_config.py`
- Modify: `api/main.py`
- Test: `test/test_pipeline_config_api.py`

- [ ] **Step 1: Write the failing test**

```python
# test/test_pipeline_config_api.py
import os, sys, unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestPipelineConfigRoutes(unittest.TestCase):
    @patch("api.routes.pipeline_config.get_pipeline_config")
    def test_get_config(self, mock_get):
        mock_get.return_value = {
            "scrape_mode": "auto", "evaluate_mode": "auto",
            "tailor_mode": "manual", "auto_send_threshold": 0,
        }
        from api.main import app
        client = TestClient(app)
        resp = client.get("/api/pipeline/config")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["tailor_mode"], "manual")

    @patch("api.routes.pipeline_config.set_pipeline_config")
    def test_patch_config_partial(self, mock_set):
        mock_set.return_value = {
            "scrape_mode": "manual", "evaluate_mode": "auto",
            "tailor_mode": "manual", "auto_send_threshold": 0,
        }
        from api.main import app
        client = TestClient(app)
        resp = client.patch("/api/pipeline/config", json={"scrape_mode": "manual"})
        self.assertEqual(resp.status_code, 200)
        mock_set.assert_called_once_with({"scrape_mode": "manual"})

    @patch("api.routes.pipeline_config.set_pipeline_config")
    def test_patch_config_invalid(self, mock_set):
        mock_set.side_effect = ValueError("Invalid mode 'turbo'")
        from api.main import app
        client = TestClient(app)
        resp = client.patch("/api/pipeline/config", json={"scrape_mode": "turbo"})
        self.assertEqual(resp.status_code, 400)
```

- [ ] **Step 2: Run the tests**

Run: `pytest test/test_pipeline_config_api.py -v`
Expected: FAIL.

- [ ] **Step 3: Write the route**

```python
# api/routes/pipeline_config.py
"""Per-stage pipeline mode toggles (auto/manual). Distinct from kill switches (ADR-0019)."""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.database import get_pipeline_config, set_pipeline_config

router = APIRouter(prefix="/api/pipeline", tags=["pipeline-config"])


class PipelineConfigUpdate(BaseModel):
    scrape_mode:         Optional[str] = Field(None, pattern="^(auto|manual)$")
    evaluate_mode:       Optional[str] = Field(None, pattern="^(auto|manual)$")
    tailor_mode:         Optional[str] = Field(None, pattern="^(auto|manual)$")
    auto_send_threshold: Optional[int] = Field(None, ge=0, le=4)


@router.get("/config")
def read_config():
    return get_pipeline_config()


@router.patch("/config")
def update_config(body: PipelineConfigUpdate):
    payload = {k: v for k, v in body.model_dump().items() if v is not None}
    if not payload:
        return get_pipeline_config()
    try:
        return set_pipeline_config(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
```

Register in `api/main.py` mirroring the runs router import.

- [ ] **Step 4: Run the tests**

Run: `pytest test/test_pipeline_config_api.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add api/routes/pipeline_config.py api/main.py test/test_pipeline_config_api.py
git commit -m "feat(api): GET/PATCH /api/pipeline/config"
```

---

### Task 15: applications response — ghost_commentary + days_since_update + offer

**Files:**
- Modify: `api/routes/applications.py`
- Test: `test/test_applications_offer_and_commentary.py`

- [ ] **Step 1: Write the failing test**

Append to `test/test_applications_offer_and_commentary.py`:

```python
import os, sys
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestApplicationsResponseShape(unittest.TestCase):
    @patch("api.routes.applications.list_applications")
    def test_response_includes_commentary_and_days(self, mock_list):
        eight_days_ago = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        mock_list.return_value = [{
            "id": "a1", "job_id": "j1", "job_title": "Eng",
            "company_name": "X", "resume_id": None, "cv_version": "base",
            "status": "ghosting",
            "status_history": [{"status": "applied", "timestamp": eight_days_ago}],
            "applied_at": eight_days_ago,
        }]
        from api.main import app
        client = TestClient(app)
        resp = client.get("/api/applications")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["ghost_commentary"],
                         "At this point we're assuming they lost it.")
        self.assertGreaterEqual(body[0]["days_since_update"], 8)

    @patch("api.routes.applications.update_application_status")
    def test_patch_accepts_offer(self, mock_update):
        mock_update.return_value = {
            "id": "a1", "status": "offer",
            "status_history": [{"status": "offer", "timestamp": "2026-06-11T00:00:00+00:00"}],
        }
        from api.main import app
        client = TestClient(app)
        resp = client.patch("/api/applications/a1/status", json={"status": "offer"})
        self.assertEqual(resp.status_code, 200)
```

- [ ] **Step 2: Run the tests**

Run: `pytest test/test_applications_offer_and_commentary.py -v`
Expected: FAIL (new fields missing, offer rejected).

- [ ] **Step 3: Modify the route**

Open `api/routes/applications.py`. The exact code depends on existing handlers — read it first. Required changes:

```python
# 1) Add 'offer' to any pydantic literal / regex validating the body status field.
class StatusUpdate(BaseModel):
    status: Literal["applied", "replied", "interview", "rejected", "ghosting", "offer"]

# 2) In the GET handler, enrich each row before returning:
from agents.database import compute_ghost_commentary
from datetime import datetime, timezone

def _enrich(row: dict) -> dict:
    history = row.get("status_history") or []
    if history:
        last_ts = history[-1].get("timestamp") or row.get("applied_at")
    else:
        last_ts = row.get("applied_at")
    try:
        last_dt = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        last_dt = datetime.now(timezone.utc)
    days = (datetime.now(timezone.utc) - last_dt).days
    return {
        **row,
        "days_since_update": max(0, days),
        "ghost_commentary": compute_ghost_commentary(max(0, days)),
    }

# Apply _enrich(...) to each row before returning the list.
# Add `response.headers["Cache-Control"] = "no-store"` to the GET handler.
```

- [ ] **Step 4: Run the tests**

Run: `pytest test/test_applications_offer_and_commentary.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add api/routes/applications.py test/test_applications_offer_and_commentary.py
git commit -m "feat(api): applications offer + ghost_commentary + days_since_update"
```

---

### Task 16: resume_changes reject with feedback_type + regeneration cap

**Files:**
- Modify: `api/routes/resumes.py`
- Modify: `agents/database.py`
- Test: `test/test_change_feedback.py`

- [ ] **Step 1: Write the failing test**

```python
# test/test_change_feedback.py
import os, sys, unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestChangeFeedback(unittest.TestCase):
    @patch("api.routes.resumes.record_change_feedback")
    def test_reject_with_feedback_calls_recorder(self, mock_record):
        mock_record.return_value = {
            "id": "c1", "review_action": "reject",
            "feedback_type": "too_formal", "regeneration_count": 1,
        }
        from api.main import app
        client = TestClient(app)
        resp = client.patch(
            "/api/resumes/r1/changes/c1",
            json={"action": "reject", "feedback_type": "too_formal"},
        )
        self.assertEqual(resp.status_code, 200)
        mock_record.assert_called_once_with(
            change_id="c1", feedback_type="too_formal"
        )

    @patch("api.routes.resumes.record_change_feedback")
    def test_regeneration_cap_returns_409(self, mock_record):
        from agents.database import RegenerationCapReached
        mock_record.side_effect = RegenerationCapReached("cap=2")
        from api.main import app
        client = TestClient(app)
        resp = client.patch(
            "/api/resumes/r1/changes/c1",
            json={"action": "reject", "feedback_type": "other"},
        )
        self.assertEqual(resp.status_code, 409)
```

- [ ] **Step 2: Run the tests**

Run: `pytest test/test_change_feedback.py -v`
Expected: FAIL.

- [ ] **Step 3: Add the database helper**

Append to `agents/database.py`:

```python
class RegenerationCapReached(Exception):
    """Raised when a rejected change has already hit the regeneration cap."""


REGENERATION_CAP = 2


def record_change_feedback(change_id: str, feedback_type: str) -> dict:
    """Mark a change as rejected with a feedback chip and trigger regeneration.

    Caps at REGENERATION_CAP (2). The actual regeneration LLM call is wired
    by the caller (route layer) — this helper bumps the counter and stamps
    regenerated_at; the caller updates tailored_text afterwards.
    """
    if feedback_type not in ("too_formal", "not_accurate", "other"):
        raise ValueError(f"invalid feedback_type: {feedback_type}")

    client = _get_supabase()
    current = (
        client.table("resume_changes")
        .select("regeneration_count")
        .eq("id", change_id)
        .limit(1)
        .execute()
    )
    rows = current.data or []
    if rows and (rows[0].get("regeneration_count") or 0) >= REGENERATION_CAP:
        raise RegenerationCapReached(
            f"regeneration_count >= {REGENERATION_CAP} for change {change_id}"
        )

    resp = (
        client.table("resume_changes")
        .update({
            "review_action":       "reject",
            "feedback_type":       feedback_type,
            "regenerated_at":      "now()",
            "regeneration_count":  (rows[0].get("regeneration_count", 0) + 1) if rows else 1,
        })
        .eq("id", change_id)
        .execute()
    )
    return (resp.data or [{}])[0]
```

- [ ] **Step 4: Modify the route**

In `api/routes/resumes.py`, in the `PATCH /resumes/{rid}/changes/{cid}` handler, add a branch:

```python
from agents.database import record_change_feedback, RegenerationCapReached

# Existing body schema gains an optional field:
class ChangeActionBody(BaseModel):
    action: Literal["accept", "reject", "keep_original"]
    feedback_type: Optional[Literal["too_formal", "not_accurate", "other"]] = None

# In the handler, after parsing the body:
if body.action == "reject" and body.feedback_type:
    try:
        return record_change_feedback(
            change_id=cid, feedback_type=body.feedback_type
        )
    except RegenerationCapReached as exc:
        raise HTTPException(status_code=409, detail=str(exc))
# else fall through to the existing accept/reject/keep_original path.
```

- [ ] **Step 5: Run the tests**

Run: `pytest test/test_change_feedback.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add agents/database.py api/routes/resumes.py test/test_change_feedback.py
git commit -m "feat(api): resume_changes feedback_type + regeneration cap"
```

---

### Task 17: POST /api/resumes/roast (transient)

**Files:**
- Modify: `api/routes/resumes.py`
- Test: `test/test_change_feedback.py` (reuse file)

- [ ] **Step 1: Write the failing test**

Append to `test/test_change_feedback.py`:

```python
class TestRoast(unittest.TestCase):
    @patch("api.routes.resumes.roast_resume")
    def test_roast_endpoint(self, mock_roast):
        mock_roast.return_value = {
            "items": [
                {"section": "Summary", "quote": "Synergistic results-driven leader",
                 "verdict": "Buzzword soup.", "fixed": "Engineering manager."}
            ]
        }
        from api.main import app
        client = TestClient(app)
        resp = client.post("/api/resumes/roast", json={"resume_id": "r1"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["items"]), 1)
        mock_roast.assert_called_once_with(resume_id="r1")
```

- [ ] **Step 2: Run the test**

Run: `pytest test/test_change_feedback.py::TestRoast -v`
Expected: FAIL.

- [ ] **Step 3: Add the route + stub agent**

In `api/routes/resumes.py`:

```python
from pydantic import BaseModel
from agents.roast import roast_resume  # new module, see step 4

class RoastBody(BaseModel):
    resume_id: str

@router.post("/roast")
def roast(body: RoastBody):
    return roast_resume(resume_id=body.resume_id)
```

Create `agents/roast.py`:

```python
"""Resume roast (OotoCV) — Settings utility, no persistence.

LLM-only path. Reads master resume from `resumes` (status='master') and asks the
critic prompt to emit roast items. The response is returned verbatim; no
storage, no audit row.
"""
from agents.database import get_master_resume
from agents.llm import call_openrouter_json  # whichever client wrapper is canonical
from agent_prompts.loader import load_prompt


def roast_resume(resume_id: str) -> dict:
    resume = get_master_resume()
    if not resume:
        return {"items": []}
    prompt = load_prompt("resume_roast")
    raw = call_openrouter_json(
        prompt=prompt,
        user_content={"resume": resume["content"]},
    )
    return {"items": raw.get("items", [])}
```

Create `agent_prompts/resume_roast.txt` with the OotoCV-voice roast instruction (one-paragraph instruction + JSON schema for `items[]` with `section`, `quote`, `verdict`, `fixed`).

- [ ] **Step 4: Run the test**

Run: `pytest test/test_change_feedback.py::TestRoast -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add api/routes/resumes.py agents/roast.py agent_prompts/resume_roast.txt test/test_change_feedback.py
git commit -m "feat(api): POST /api/resumes/roast (transient)"
```

---

### Task 18: /api/system/status alias

**Files:**
- Modify: `api/routes/scheduler.py`

- [ ] **Step 1: Add the alias handler**

In `api/routes/scheduler.py`, append:

```python
@router.get("/api/system/status")
def system_status():
    """OotoCV sidebar pulse feed. Reshapes /api/scheduler into a flat shape."""
    raw = _scheduler_state()  # whatever helper the existing GET /api/scheduler uses
    next_run = None
    for job in raw.get("jobs", []):
        if job.get("id") in ("scrape_worker", "eval_worker"):
            next_run = job.get("next_run_utc") or next_run

    last_runs = raw.get("last_runs", {}) or {}
    last_error = None
    for k in ("scrape", "evaluate", "tailor"):
        run = last_runs.get(k) or {}
        if run.get("status") == "failed":
            last_error = run.get("error_detail")
            break

    if not raw.get("scheduler_running"):
        cron_state = "error"
    elif next_run:
        cron_state = "active"
    else:
        cron_state = "sleeping"

    return {
        "cron_state": cron_state,
        "next_run_at": next_run,
        "last_error": last_error,
    }
```

- [ ] **Step 2: Smoke test manually**

```bash
uvicorn api.main:app --reload &
sleep 3
curl -s http://localhost:8000/api/system/status | python -m json.tool
# Expect: {"cron_state": "active|sleeping|error", "next_run_at": "...", "last_error": null}
kill %1
```

- [ ] **Step 3: Commit**

```bash
git add api/routes/scheduler.py
git commit -m "feat(api): /api/system/status alias for OotoCV cron sidebar"
```

---

## Phase 4: Worker + evaluator wiring

### Task 19: ScrapeWorker stamps jobs.run_id

**Files:**
- Modify: `services/scraper_worker.py`

- [ ] **Step 1: Read existing scraper_worker.py to find the insert path**

Run: `grep -n "def map_job_record\|insert\|run_id" services/scraper_worker.py`
Identify (a) where the current `pipeline_runs.id` is held in the worker scope, (b) where `jobs` rows are inserted/upserted.

- [ ] **Step 2: Thread run_id into the insert**

Modify the worker so the active `pipeline_runs.id` from `start_run('scrape')` is captured into a local variable and added to each `jobs` row payload before insert.

```python
# Pseudocode — adapt to existing structure.
current_run_id = start_run("scrape")  # if this returns id; otherwise fetch via SELECT
# ...
for raw in apify_results:
    record = map_job_record(raw)
    record["run_id"] = current_run_id
    client.table("jobs").upsert(record, on_conflict="id").execute()
```

- [ ] **Step 3: Smoke trigger**

```bash
curl -X POST http://localhost:8000/api/scheduler/trigger/scrape
# Then in Supabase SQL:
# SELECT run_id, COUNT(*) FROM jobs GROUP BY run_id ORDER BY 2 DESC LIMIT 5;
# Expect: a new run_id appearing on freshly-scraped rows.
```

- [ ] **Step 4: Commit**

```bash
git add services/scraper_worker.py
git commit -m "feat(scraper): stamp jobs.run_id from current pipeline_runs"
```

---

### Task 20: Scheduler respects pipeline modes

**Files:**
- Modify: `services/scheduler.py`

- [ ] **Step 1: Gate scrape and evaluate jobs on mode**

In `run_scrape_worker()` and `run_eval_worker()` entry points (or whatever names exist in scheduler.py), check the corresponding mode first and return early when `manual`:

```python
from agents.database import get_pipeline_config

def run_scrape_worker():
    cfg = get_pipeline_config()
    if cfg["scrape_mode"] == "manual":
        logger.info("scrape skipped: pipeline_scrape_mode=manual")
        return
    # ... existing body
```

Same shape for `run_eval_worker` using `evaluate_mode`. Do not gate the reaper or the re-evaluation worker.

- [ ] **Step 2: Manual verification**

```bash
# Flip to manual:
curl -X PATCH -H 'Content-Type: application/json' \
  -d '{"scrape_mode":"manual"}' \
  http://localhost:8000/api/pipeline/config

# Trigger scrape via the manual endpoint; confirm logs show no skip.
curl -X POST http://localhost:8000/api/scheduler/trigger/scrape

# Restore:
curl -X PATCH -H 'Content-Type: application/json' \
  -d '{"scrape_mode":"auto"}' \
  http://localhost:8000/api/pipeline/config
```

(The cron-fire path is harder to test manually; the unit test for `get_pipeline_config` covers the gate value.)

- [ ] **Step 3: Commit**

```bash
git add services/scheduler.py
git commit -m "feat(scheduler): pipeline_*_mode gates scrape/evaluate cron"
```

---

### Task 21: Evaluator emits new fields + 4-way verdict

**Files:**
- Modify: `agent_prompts/evaluator.txt` (or whichever prompt file the evaluator uses)
- Modify: `agents/evaluator.py` (insert path writes the new columns)

- [ ] **Step 1: Read the existing evaluator prompt and writer**

Run:
```bash
grep -rn "recommended_action" agents/ agent_prompts/ | head
```
Locate (a) the prompt file emitting `recommended_action`, (b) the JSON schema describing the eval response, (c) the DB-write line that upserts into `job_evaluations`.

- [ ] **Step 2: Update the JSON schema in the prompt**

Update the schema block to include:

```jsonc
{
  "recommended_action": "tailor | borderline | apply_direct | skip",
  "top_strength":       "<one-line strength, OotoCV voice; populate only when action=tailor>",
  "deciding_factor":    "<one-line tipping factor; populate only when action=borderline>",
  "kill_shot":          "<one-line rejection reason; populate only when action=skip>",
  "red_flags":          ["<\"Label — explanation\">", "..."],
  "gaps": [
    { "text": "...", "severity": "minor|notable|significant", "strategy": "<imperative>" }
  ]
}
```

Add to the prompt body: an instruction that red_flags MUST use em-dash (` — `) between label and explanation; gaps MUST include `severity` and `strategy`; populate exactly ONE of {top_strength, deciding_factor, kill_shot} matching the verdict.

- [ ] **Step 3: Update the writer**

In `agents/evaluator.py`, in the function that upserts into `job_evaluations`, add the new columns to the payload (default each to the LLM's emitted value or NULL):

```python
payload.update({
    "top_strength":     llm_out.get("top_strength"),
    "deciding_factor":  llm_out.get("deciding_factor"),
    "kill_shot":        llm_out.get("kill_shot"),
    "red_flags":        _normalize_red_flags(llm_out.get("red_flags") or []),
})
```

And a normalizer that enforces em-dash (R6 mitigation):

```python
import re
_HYPHEN_RE = re.compile(r"\s+[-–]\s+")  # plain hyphen or en-dash

def _normalize_red_flags(items):
    out = []
    for s in items:
        if not isinstance(s, str):
            continue
        out.append(_HYPHEN_RE.sub(" — ", s))
    return out
```

- [ ] **Step 4: Unit test the normalizer**

Append to `test/test_ootocv_schema.py`:

```python
class TestRedFlagNormalize(unittest.TestCase):
    def test_hyphen_to_emdash(self):
        from agents.evaluator import _normalize_red_flags
        result = _normalize_red_flags([
            "Startup mentality - no processes",
            "Salary band — already correct",
            "Title inflation – en-dash variant",
        ])
        self.assertEqual(result, [
            "Startup mentality — no processes",
            "Salary band — already correct",
            "Title inflation — en-dash variant",
        ])
```

Run: `pytest test/test_ootocv_schema.py::TestRedFlagNormalize -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agent_prompts/evaluator.txt agents/evaluator.py test/test_ootocv_schema.py
git commit -m "feat(eval): emit top_strength/deciding_factor/kill_shot/red_flags + 4-way verdict"
```

---

## Phase 5: Documentation

### Task 22: Update CLAUDE.md ADR table + active doc

**Files:**
- Modify: `CLAUDE.md`
- Create: `docs/active/ootocv-schema-adaptation.md`

- [ ] **Step 1: Append ADR entries to CLAUDE.md**

```markdown
- ADR-0023: Four-way verdict (TAILOR/BORDERLINE/APPLY_DIRECT/SKIP) with pre-computed card lines (top_strength/deciding_factor/kill_shot/red_flags) on `job_evaluations`.
- ADR-0024: Per-stage pipeline mode (`pipeline_scrape_mode`/`pipeline_evaluate_mode`/`pipeline_tailor_mode` in `system_config`); distinct from kill switches (ADR-0019).
- ADR-0025: Jobs link to `pipeline_runs.id` via `jobs.run_id`; `runs_with_counts(limit_n)` RPC backs `/api/runs`.
```

And add to the active-tasks list:

```markdown
- `docs/active/ootocv-schema-adaptation.md` — OotoCV schema adaptation 🟡 (migrations 021–025 + 3 new routes + evaluator update)
```

- [ ] **Step 2: Create the active doc**

Write `docs/active/ootocv-schema-adaptation.md` with: goal, the five migration filenames, the three new route paths, the open question on BORDERLINE backfill (decision: on-demand), and a status line "🟡 Migrations applied, API + evaluator next".

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md docs/active/ootocv-schema-adaptation.md
git commit -m "docs: register OotoCV schema adaptation (ADRs 0023-0025 + active doc)"
```

---

## Self-review (post-write check, completed)

- **Spec coverage**: each of the seven schema changes in the spec maps to one task (Tasks 1–5 = migrations 021–025; Task 9–11 = helpers; Task 12–18 = API surface; Task 19–21 = worker + evaluator; Task 22 = docs). Resume Roast persistence decision (transient) is implemented in Task 17 with no DB rows. Cron sidebar transport decision (poll) is implemented as the `/api/system/status` alias in Task 18, with no SSE channel.
- **Placeholders**: none. Every code step ships the actual function body or migration SQL.
- **Type consistency**: `recommended_action` values, `feedback_type` set, `cron_state` enum, and pipeline-mode short keys (`scrape_mode`/`evaluate_mode`/`tailor_mode`) are used identically across helper, route, and migration. The route layer's `Literal[...]` matches the DB CHECK in 023 (`offer`) and 024 (`too_formal`/`not_accurate`/`other`).
- **Risks tracked**: R6 em-dash normalization is implemented in Task 21; R5 `Cache-Control: no-store` is set in Task 15; R8 regeneration cap is enforced in Task 16; R7 default `tailor_mode=manual` is seeded in Task 5; R11 still-running run rendering is a frontend concern flagged in ADR-0025.
