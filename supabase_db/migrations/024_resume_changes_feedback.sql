-- Migration 024: Capture feedback chip on rejected changes + track regenerations.
-- Powers the OotoCV TailoringReview reject flow ("Too formal" / "Not accurate" /
-- "Other") and lets the UI cap regeneration retries (default cap: 2,
-- enforced in api/routes/resumes.py + agents/database.record_change_feedback)
-- before falling back to manual edit.

ALTER TABLE resume_changes
  ADD COLUMN IF NOT EXISTS feedback_type      TEXT,
  ADD COLUMN IF NOT EXISTS regenerated_at     TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS regeneration_count INTEGER NOT NULL DEFAULT 0;

ALTER TABLE resume_changes
  DROP CONSTRAINT IF EXISTS resume_changes_feedback_type_check;

ALTER TABLE resume_changes
  ADD CONSTRAINT resume_changes_feedback_type_check
  CHECK (feedback_type IS NULL OR feedback_type IN (
    'too_formal', 'not_accurate', 'other'
  ));

COMMENT ON COLUMN resume_changes.feedback_type IS
  'Reason the user rejected this change (OotoCV reject chip). '
  'NULL until the user picks a chip. Set on reject triggers regeneration.';
COMMENT ON COLUMN resume_changes.regenerated_at IS
  'Last time tailored_text was replaced by a regeneration. NULL = never regenerated.';
COMMENT ON COLUMN resume_changes.regeneration_count IS
  'Number of regenerations applied. Capped at 2 by api/routes/resumes.py; '
  'past the cap, the UI falls back to "edit manually" (R8 mitigation).';
