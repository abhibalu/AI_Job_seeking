# Plan: OotoCV Schema Adaptation

**Status:** 🟡 Backend complete; frontend wiring next
**Created:** 2026-06-11
**Branch:** `feature/ootocv-schema-adaptation`
**Spec:** `/Users/abhijithm/.claude/plans/resilient-sleeping-gray.md`
**Plan:** `docs/superpowers/plans/2026-06-11-ootocv-schema-adaptation.md`

## Goal

Reframe the backend to support the OotoCV UI design's **agentic monitoring**
posture: runs as first-class user-facing units, four-way verdict with
pre-computed card lines, per-stage pipeline mode toggles, application
tracker with `offer` + ghost commentary, change-feedback chips with a
regeneration cap, and a transient resume roast utility. Anchored by
ADR-0023, ADR-0024, ADR-0025.

## Decisions Made

- **BORDERLINE is an explicit evaluator output**, not a derived band on
  `match_score` (loses the agent's narrative deciding factor). ADR-0023.
- **Pipeline modes live as three rows in `system_config`** (not a new
  table). YAGNI for per-stage scheduling overrides today. ADR-0024.
- **Roast is transient** — no DB persistence. `agents/roast.py` returns
  `{"items": []}` on any failure so the Settings UI never sees 500.
- **Cron sidebar polls `GET /api/system/status` every 30s.** No new SSE
  channel for system state; the 5s message rotation is client-side
  cosmetic.
- **`save_evaluation_with_card_lines` lives in `agents/evaluator_writer.py`**
  (sibling module), not in `agents/database.py`. Keeps this branch from
  colliding with Phase 1 Cluster A's WIP in `database.py`.
- **Resume-namespace API endpoints are sibling routers** on `/api/resumes`
  (`api/routes/resume_change_feedback.py`, `api/routes/resume_roast.py`)
  rather than edits to `api/routes/resumes.py`. Same WIP-avoidance.
- **`apply` is kept in the `recommended_action` CHECK** so historical
  rows stay valid. New evaluator does not emit it. No mass re-eval —
  re-evaluation is on-demand from the UI.
- **`run_id` is stamped only by `ScrapeWorker`**, never re-stamped by
  EvalWorker. Manual single-URL imports (`POST /api/jobs/import`) leave
  `run_id` NULL and surface under a "Pre-runs" bucket in the UI.

## Open Items

- **Frontend wiring** — connect the OotoCV `src/` tree to the new endpoints
  (`/api/runs`, `/api/pipeline/config`, `/api/resumes/roast`, …) and to
  the enriched response shapes (`top_strength` / `deciding_factor` /
  `kill_shot` / `red_flags`, `ghost_commentary`, `cron_state`).
- **Evaluator redeploy** — `save_evaluation_with_card_lines` is safe to
  call before the new prompt is live (it skips the card UPDATE when all
  card fields are absent). Once the prompt is redeployed, new evals get
  the new columns; legacy rows stay as-is.
- **`api/routes/evaluations.py`** has a dead `save_evaluation` import.
  Cleanup deferred until this branch merges back.
- **`agents/cli.py`** still calls `save_evaluation` directly. Dev tool;
  upgrade after merge.
- **`api/routes/resumes.py` consolidation** — once Phase 1 merges, fold
  the sibling routers (`resume_change_feedback`, `resume_roast`) into
  the main resumes router if preferred.
- **Regeneration LLM call** is not yet wired — Task 16 only stamps
  `feedback_type` and bumps `regeneration_count`. The actual second-pass
  rewrite happens in a follow-up task.

## What landed in this phase

| File | Change |
|---|---|
| `supabase_db/migrations/021_jobs_run_id.sql` | new |
| `supabase_db/migrations/021b_runs_with_counts_rpc.sql` | new |
| `supabase_db/migrations/022_evaluations_verdict_extension.sql` | new |
| `supabase_db/migrations/023_applications_offer_status.sql` | new |
| `supabase_db/migrations/024_resume_changes_feedback.sql` | new |
| `supabase_db/migrations/025_system_config_pipeline_modes.sql` | new |
| `docs/decisions/ADR-0023-four-way-verdict-card-lines.md` | new |
| `docs/decisions/ADR-0024-per-stage-pipeline-mode.md` | new |
| `docs/decisions/ADR-0025-run-as-first-class-entity.md` | new |
| `agents/database.py` | +6 helpers: `list_runs`, `get_run`, `get_pipeline_config`, `set_pipeline_config`, `compute_ghost_commentary`, `record_change_feedback` + `RegenerationCapReached` |
| `agents/evaluator_writer.py` | new — `_normalize_red_flags` + `save_evaluation_with_card_lines` |
| `agents/roast.py` | new — `ResumeRoastAgent` + `roast_resume()` |
| `agent_prompts/resume_roast.md` | new |
| `agent_prompts/job_evaluator.md` | 4-way `recommended_action`, card-line fields, em-dash rule |
| `api/routes/runs.py` | new — `GET /api/runs`, `GET /api/runs/{id}` |
| `api/routes/pipeline_config.py` | new — `GET/PATCH /api/pipeline/config` |
| `api/routes/resume_change_feedback.py` | new — `POST .../changes/{cid}/feedback` |
| `api/routes/resume_roast.py` | new — `POST /api/resumes/roast` |
| `api/routes/system.py` | new — `GET /api/system/status` |
| `api/routes/applications.py` | `offer` status; response enriched with `ghost_commentary` + `days_since_update`; `Cache-Control: no-store` |
| `api/main.py` | wire the 5 new routers |
| `services/scraper_service.py` | `scrape_and_import(url, run_id=...)` |
| `services/scraper_worker.py` | thread `start_run("scrape")` id into the service call |
| `services/scheduler.py` | `_gated_scrape_worker` / `_gated_eval_worker` wrappers; cron registers the gated versions |
| `services/eval_worker.py` | swap to `save_evaluation_with_card_lines` |
| `services/reeval_worker.py` | same swap |

## Test coverage

84 tests pass across Phase 1+2+3+4:

| Suite | Tests |
|---|---|
| `test/test_ootocv_schema.py` | 14 (DB helpers) |
| `test/test_runs_api.py` | 5 |
| `test/test_pipeline_config_api.py` | 6 |
| `test/test_applications_offer_and_commentary.py` | 7 |
| `test/test_change_feedback.py` | 5 |
| `test/test_resume_roast.py` | 7 |
| `test/test_system_status.py` | 5 |
| `test/test_scrape_run_id.py` | 4 |
| `test/test_pipeline_mode_gate.py` | 5 |
| `test/test_evaluator_card_lines.py` | 11 |
| `test/test_resume_lifecycle_foundation.py` (Phase 1 regression) | 15 |

`test/_api_test_utils.py` provides `neutralize_app_side_effects()` +
`build_client()` for offline `TestClient` use (skips startup
`init_database` / `start_scheduler` / `setup_logging` and stubs the
`LangfuseMiddleware` client).

## Notes for the merge

Most of the OotoCV adaptation lives in **new** files so this branch is
near-orthogonal to Phase 1 Cluster A. The two semantic touches on
WIP-modified files were resolved with snapshot+restore:

- `agents/database.py` — OotoCV helpers appended after Phase 2's reset.
- `services/scheduler.py` — gated wrappers + cron registration swap;
  WIP merged back via `git merge-file` (two cosmetic conflicts from
  WIP reflowing `_build_trigger()` calls — kept the gated wrappers,
  adopted the WIP reflow style).

Once Phase 1 merges to main, this branch should rebase cleanly. The
only follow-ups required after the rebase:
- Fold `save_evaluation_with_card_lines` into `agents/database.save_evaluation`.
- Decide whether to keep the sibling resume routers or fold them into
  `api/routes/resumes.py`.
