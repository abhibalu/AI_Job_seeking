# ADR-0025: Jobs are linked to a pipeline_runs row (run as first-class entity)

**Status:** Accepted (2026-06-11)

## Context

The OotoCV feed groups jobs under run separators
(`Today · 5:00 PM`, `Yesterday · 5:00 PM`) and renders an action band per
run showing the agent's batch decisions
(`2 tailor · 1 direct · 1 borderline`).

The agentic story depends on the user seeing runs as discrete units the
agent produced. The current schema has `pipeline_runs` for observability
but no link from `jobs` to the run that produced them — feeds can only be
date-grouped, losing the "what did this batch decide" framing.

## Decision

`jobs.run_id` is a nullable UUID FK to `pipeline_runs.id`. **Only
`ScrapeWorker` stamps it** on insert, from the active run id returned by
`start_run('scrape')`. `EvalWorker` and downstream workers never re-stamp.

`GET /api/runs` returns runs + aggregated counts via a `STABLE` SQL
function (`runs_with_counts(limit_n)`) that does a single GROUP BY on the
join with `job_evaluations`. No counter columns, no triggers, no cached
counts.

Historical jobs have `run_id IS NULL`; the UI groups them under a
"Pre-runs" / "Imported" bucket. After two new cron runs, the bucket is
cosmetic.

## Consequences

- Single round-trip to render the feed: one query for jobs filtered by
  `run_id`, one query for `runs_with_counts`.
- Re-stamping `run_id` on re-evaluation would change the user's mental
  model of "which batch produced this job" — explicitly prohibited.
- The action band counts on a still-running run can mutate visibly as
  evaluations land. The UI defers rendering counts until
  `finished_at IS NOT NULL` and shows "Run in progress · X / Y evaluated"
  in the interim (R11 mitigation).
- Run summary is fully derivable; no caching layer needed.

## Alternatives rejected

- **A new `runs` table** — duplicates `pipeline_runs`, which already has
  exactly the right shape (`started_at`, `finished_at`, `status`,
  `jobs_found`, `metadata`).
- **Stamp `run_id` on evaluation, not scrape** — re-stamping breaks the
  "which scrape batch produced this job" mental model and complicates
  observability when scrape and evaluate run on different schedules.
- **Add per-verdict counter columns to `pipeline_runs`** — needs triggers
  to stay consistent; the GROUP BY query is cheap enough that derivation
  is preferable.

## See also

- Migration `021_jobs_run_id.sql`
- Migration `021b_runs_with_counts_rpc.sql`
- `services/scraper_worker.py` (write site)
- `agents/database.list_runs` (read site)
