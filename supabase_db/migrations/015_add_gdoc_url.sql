-- Migration 015: Add gdoc_url to resumes
-- Stores the Google Docs URL of the exported tailored resume so the UI can
-- surface it later (e.g. re-open link, verify export).

ALTER TABLE resumes
ADD COLUMN IF NOT EXISTS gdoc_url TEXT DEFAULT NULL;

COMMENT ON COLUMN resumes.gdoc_url IS
    'Google Docs URL of the exported tailored resume. Set by POST /api/resumes/export-gdoc.';
