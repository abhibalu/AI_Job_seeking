-- Migration 017: Add CHECK constraint on resumes.status (R-RES-01).
-- Vocabulary was previously enforced only in Python (agents/database.py).

ALTER TABLE resumes DROP CONSTRAINT IF EXISTS resumes_status_check;
ALTER TABLE resumes
  ADD CONSTRAINT resumes_status_check
  CHECK (status IN ('master', 'pending', 'approved', 'rejected', 'needs_review'));

COMMENT ON CONSTRAINT resumes_status_check ON resumes IS
  'Vocabulary enforcement for resumes.status (Phase 1 Cluster A).';
