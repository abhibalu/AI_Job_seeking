-- Migration 016: Phase 1 preflight audit — NO DDL.
-- The operator runs these queries against Supabase before applying 017–020.
-- If any "violations" query returns rows, fix data BEFORE applying 018.

-- 1. Confirm status vocabulary matches the CHECK we are about to install.
--    Expected: only master, pending, approved, rejected, needs_review.
-- SELECT status, COUNT(*) FROM resumes GROUP BY status ORDER BY status;

-- 2. Master-row violations: master must have tailoring_status='not_started' AND job_id IS NULL.
-- SELECT id, status, tailoring_status, job_id, name
-- FROM resumes
-- WHERE status = 'master'
--   AND (tailoring_status != 'not_started' OR job_id IS NOT NULL);

-- 3. Confirm tasks.status CHECK currently lacks 'cancelled' (justifies migration 020).
-- SELECT pg_get_constraintdef(c.oid)
-- FROM pg_constraint c
-- JOIN pg_class t ON t.oid = c.conrelid
-- WHERE t.relname = 'tasks' AND c.contype = 'c';
