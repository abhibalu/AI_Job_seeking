-- Migration 020: extend tasks.status CHECK to include 'cancelled'.
-- Verified against 001_initial_schema.sql:85 — current CHECK is
-- ('queued','running','completed','failed'). Despite that, api/routes/tasks.py
-- and services/reeval_worker.py already write 'cancelled', so every cancel
-- attempt is silently violating CHECK at the DB level today.

ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_status_check;
ALTER TABLE tasks
  ADD CONSTRAINT tasks_status_check
  CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled'));
