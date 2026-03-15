-- Migration 008: Add recruiter_email to job_evaluations
-- Backfills from raw_response JSONB (already captured from LLM output).
-- "Unknown" values are treated as NULL — no email found.

ALTER TABLE job_evaluations
    ADD COLUMN IF NOT EXISTS recruiter_email TEXT;

-- Backfill from raw_response where the LLM returned an actual email.
-- raw_response->>'recruiter_email' returns the string value or NULL.
-- NULLIF trims whitespace and converts "Unknown" / "" to NULL.
UPDATE job_evaluations
SET recruiter_email = NULLIF(
    TRIM(raw_response->>'recruiter_email'),
    'Unknown'
)
WHERE raw_response IS NOT NULL
  AND raw_response->>'recruiter_email' IS NOT NULL
  AND TRIM(raw_response->>'recruiter_email') NOT IN ('Unknown', '');
