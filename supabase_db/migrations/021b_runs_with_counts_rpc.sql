-- Migration 021b: SQL function backing list_runs() / GET /api/runs aggregation.
-- One STABLE aggregation query per call; no triggers, no cached counters.
-- ADR-0025.
--
-- Counts are computed via FILTER on the 4-way OotoCV verdict set:
--   tailor / borderline / apply_direct / skip
-- Legacy verdicts ('apply') are intentionally not surfaced as a separate count
-- column — they predate the run model and live under run_id IS NULL.

CREATE OR REPLACE FUNCTION runs_with_counts(limit_n INT DEFAULT 50)
RETURNS TABLE (
  id                 UUID,
  started_at         TIMESTAMPTZ,
  finished_at        TIMESTAMPTZ,
  status             TEXT,
  jobs_found         INT,
  tailor_count       INT,
  borderline_count   INT,
  apply_direct_count INT,
  skip_count         INT
) LANGUAGE sql STABLE AS $$
  SELECT
    pr.id,
    pr.started_at,
    pr.finished_at,
    pr.status,
    pr.jobs_found,
    COUNT(*) FILTER (WHERE je.recommended_action = 'tailor')::int        AS tailor_count,
    COUNT(*) FILTER (WHERE je.recommended_action = 'borderline')::int    AS borderline_count,
    COUNT(*) FILTER (WHERE je.recommended_action = 'apply_direct')::int  AS apply_direct_count,
    COUNT(*) FILTER (WHERE je.recommended_action = 'skip')::int          AS skip_count
  FROM pipeline_runs pr
  LEFT JOIN jobs j             ON j.run_id = pr.id
  LEFT JOIN job_evaluations je ON je.job_id = j.id
  WHERE pr.run_type IN ('scrape', 'full_pipeline')
  GROUP BY pr.id
  ORDER BY pr.started_at DESC
  LIMIT limit_n;
$$;

COMMENT ON FUNCTION runs_with_counts(INT) IS
  'Returns recent scrape/full_pipeline runs with per-verdict aggregated counts. '
  'Backs agents.database.list_runs() and GET /api/runs.';
