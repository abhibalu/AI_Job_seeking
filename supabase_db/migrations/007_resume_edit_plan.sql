-- Migration 007: Add edit_plan column to resumes table
-- Stores the structured edit plan alongside each tailored resume
-- for audit trail and change tracking.

ALTER TABLE resumes ADD COLUMN IF NOT EXISTS edit_plan JSONB DEFAULT NULL;

COMMENT ON COLUMN resumes.edit_plan IS 'Structured edit plan from ChangePlannerAgent — records what was changed and why';
