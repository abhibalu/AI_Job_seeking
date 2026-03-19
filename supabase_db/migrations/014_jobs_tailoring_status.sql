-- 014: Extend v_jobs_enriched with tailoring_status from latest resume
-- Motivation: frontend checks job.tailoring_status to show "Review & Send" vs "Tailor & Approve"
-- but tailoring_status only lived on the resumes table. This view surfaces it on jobs.

CREATE OR REPLACE VIEW v_jobs_enriched AS
SELECT j.*,
  EXISTS (
    SELECT 1 FROM job_evaluations je WHERE je.job_id = j.id
  ) AS is_evaluated,
  (
    SELECT r.tailoring_status
    FROM resumes r
    WHERE r.job_id = j.id AND r.status != 'master'
    ORDER BY r.created_at DESC
    LIMIT 1
  ) AS tailoring_status
FROM jobs j;

GRANT SELECT ON v_jobs_enriched TO authenticated, anon, service_role;
