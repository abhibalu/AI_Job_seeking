-- Migration 006: Create v_jobs_enriched view
-- Fixes UI filter latency by eliminating double round-trip pattern.
-- See ADR-0003 for full context.

-- View: adds is_evaluated computed column to jobs
-- Uses EXISTS + indexed FK (idx_evaluations_job_id) for fast lookups.
CREATE OR REPLACE VIEW v_jobs_enriched AS
SELECT j.*,
  EXISTS (
    SELECT 1 FROM job_evaluations je WHERE je.job_id = j.id
  ) AS is_evaluated
FROM jobs j;

-- Grant access for Supabase roles
GRANT SELECT ON v_jobs_enriched TO authenticated, anon, service_role;
