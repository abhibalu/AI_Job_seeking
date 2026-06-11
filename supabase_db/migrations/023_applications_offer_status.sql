-- Migration 023: Allow 'offer' in applications.status (OotoCV celebration state).
-- One-line CHECK extension; no data backfill needed.
-- Renders with pulse animation in the application tracker.

ALTER TABLE applications
  DROP CONSTRAINT IF EXISTS applications_status_check;

ALTER TABLE applications
  ADD CONSTRAINT applications_status_check
  CHECK (status IN (
    'applied', 'replied', 'interview', 'rejected', 'ghosting', 'offer'
  ));

COMMENT ON CONSTRAINT applications_status_check ON applications IS
  'OotoCV status set. "offer" added 2026-06-11; renders with pulse animation '
  'in the application tracker.';
