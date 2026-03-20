-- Migration 010: OotoCV Foundation — data model prerequisites
-- Adds tailoring_status, cover_letter, resume_changes table,
-- system_config table (for cron_tz), and cancelled status.

-- ============================================
-- 1. tailoring_status on resumes
--    Tracks pipeline state for tailored resumes.
--    'master' rows are exempt — status only meaningful for tailored rows.
-- ============================================
ALTER TABLE resumes
ADD COLUMN IF NOT EXISTS tailoring_status TEXT
    DEFAULT 'not_started'
    CHECK (tailoring_status IN ('not_started', 'processing', 'ready', 'cancelled', 'needs_review'));

COMMENT ON COLUMN resumes.tailoring_status IS
    'OotoCV pipeline state: not_started → processing → ready (or cancelled/needs_review). '
    'Distinct from status (pending/approved/rejected) which tracks user review decision.';

-- Backfill existing tailored rows from status column
UPDATE resumes
SET tailoring_status = CASE
    WHEN status = 'needs_review' THEN 'needs_review'
    WHEN status IN ('pending', 'approved', 'rejected') THEN 'ready'
    ELSE 'not_started'
END
WHERE status != 'master';


-- ============================================
-- 2. cover_letter on resumes
--    Stores the AI-generated + user-edited cover letter.
--    Nullable — not every tailored resume has a CL yet.
-- ============================================
ALTER TABLE resumes
ADD COLUMN IF NOT EXISTS cover_letter TEXT DEFAULT NULL;

COMMENT ON COLUMN resumes.cover_letter IS
    'AI-generated cover letter (editable by user). Saved on blur via PATCH /jobs/:id/cover_letter.';


-- ============================================
-- 3. resume_changes table
--    Normalised per-change records for OotoCV change review UI.
--    Replaces reading individual edits[] from the edit_plan JSONB.
--    Each row = one planned edit that the user can Accept / Reject / Keep original.
-- ============================================
CREATE TABLE IF NOT EXISTS resume_changes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id       UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    job_id          TEXT NOT NULL,

    -- Location in the resume JSON (e.g. "work[0].highlights[2]")
    location        TEXT NOT NULL,
    action_type     TEXT NOT NULL CHECK (action_type IN ('rephrase', 'add', 'remove')),

    -- Core ADR-0010 fields
    original_text   TEXT,           -- immutable: the pre-AI text (NULL for 'add' actions)
    tailored_text   TEXT,           -- AI output
    accepted_text   TEXT,           -- final value chosen by user (NULL = not yet reviewed)

    -- User review state
    review_action   TEXT CHECK (review_action IN ('accept', 'reject', 'keep_original', NULL)),

    -- Metadata
    reason          TEXT,           -- why this change was planned (from ChangePlannerAgent)
    confidence      REAL,           -- 0.0–1.0, lower = more uncertain (for sort in UI)
    approved_source TEXT,           -- which approved skill backs this edit

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE resume_changes IS
    'Per-change records for OotoCV TailoringReview UI. '
    'original_text is immutable (pre-AI). accepted_text is set by user action.';

CREATE INDEX IF NOT EXISTS idx_resume_changes_resume_id ON resume_changes(resume_id);
CREATE INDEX IF NOT EXISTS idx_resume_changes_job_id ON resume_changes(job_id);
CREATE INDEX IF NOT EXISTS idx_resume_changes_review_action ON resume_changes(review_action);

-- RLS
ALTER TABLE resume_changes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow all for authenticated" ON resume_changes;
DROP POLICY IF EXISTS "Allow all for service_role" ON resume_changes;

CREATE POLICY "Allow all for authenticated" ON resume_changes FOR ALL TO authenticated USING (true);
CREATE POLICY "Allow all for service_role" ON resume_changes FOR ALL TO service_role USING (true);

-- updated_at trigger
DROP TRIGGER IF EXISTS update_resume_changes_updated_at ON resume_changes;
CREATE TRIGGER update_resume_changes_updated_at
    BEFORE UPDATE ON resume_changes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ============================================
-- 4. system_config table
--    Key-value store for user-level system settings.
--    Stores cron_time + cron_tz as an IANA timezone pair.
-- ============================================
CREATE TABLE IF NOT EXISTS system_config (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE system_config IS
    'Key-value store for system-level settings. '
    'cron_time: HH:MM string. cron_tz: IANA timezone (e.g. Europe/Dublin). '
    'auto_send_threshold: integer 0–4.';

-- Seed defaults (idempotent)
INSERT INTO system_config (key, value) VALUES
    ('cron_time',             '17:00'),
    ('cron_tz',               'UTC'),
    ('auto_send_threshold',   '0')
ON CONFLICT (key) DO NOTHING;

-- RLS
ALTER TABLE system_config ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow all for authenticated" ON system_config;
DROP POLICY IF EXISTS "Allow all for service_role" ON system_config;

CREATE POLICY "Allow all for authenticated" ON system_config FOR ALL TO authenticated USING (true);
CREATE POLICY "Allow all for service_role" ON system_config FOR ALL TO service_role USING (true);
