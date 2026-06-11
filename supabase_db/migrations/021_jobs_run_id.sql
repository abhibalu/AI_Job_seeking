-- Migration 021: Link jobs to the pipeline_runs row that produced them.
-- Powers the OotoCV feed grouping ("Today · 5:00 PM" separators + action band).
-- Backfill strategy: leave NULL on historical rows; UI groups them under
-- a "Pre-runs" bucket. After two new scrape cycles the bucket is cosmetic.
--
-- Stamped by ScrapeWorker only (services/scraper_worker.py); never re-stamped
-- by EvalWorker or other downstream workers. ADR-0025.

ALTER TABLE jobs
  ADD COLUMN IF NOT EXISTS run_id UUID REFERENCES pipeline_runs(id);

COMMENT ON COLUMN jobs.run_id IS
  'pipeline_runs.id of the scrape run that produced this job. '
  'NULL for legacy rows imported before run-linking. '
  'Only stamped by ScrapeWorker; never re-stamped by other workers.';

CREATE INDEX IF NOT EXISTS idx_jobs_run_id ON jobs(run_id);
