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
