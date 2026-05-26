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
