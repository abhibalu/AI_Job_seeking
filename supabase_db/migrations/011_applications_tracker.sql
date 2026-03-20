-- Migration 011: OotoCV Tracker — applications table
-- Resolved: status_history JSONB on applications table
-- (simpler than application_events for v1; mode=sent uses ?mode query param in frontend)

CREATE TABLE IF NOT EXISTS applications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id          TEXT NOT NULL,

    -- Denormalized for display without a join
    job_title       TEXT,
    company_name    TEXT,

    resume_id       UUID REFERENCES resumes(id) ON DELETE SET NULL,
    cv_version      TEXT NOT NULL DEFAULT 'base'
                        CHECK (cv_version IN ('base', 'tailored')),

    status          TEXT NOT NULL DEFAULT 'applied'
                        CHECK (status IN ('applied', 'replied', 'interview', 'rejected', 'ghosting')),

    -- Append-only log: [{status, timestamp}]. Oldest first.
    status_history  JSONB NOT NULL DEFAULT '[]'::jsonb,

    applied_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE applications IS
    'OotoCV application tracker. Each row = one application the user sent. '
    'cv_version records which CV was used (base or tailored). '
    'job_title + company_name are denormalized from jobs for cheap display. '
    'status_history = [{status, timestamp}] is an append-only audit log.';

CREATE INDEX IF NOT EXISTS idx_applications_job_id  ON applications(job_id);
CREATE INDEX IF NOT EXISTS idx_applications_status  ON applications(status);

-- RLS
ALTER TABLE applications ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow all for authenticated" ON applications;
DROP POLICY IF EXISTS "Allow all for service_role"  ON applications;

CREATE POLICY "Allow all for authenticated" ON applications FOR ALL TO authenticated USING (true);
CREATE POLICY "Allow all for service_role"  ON applications FOR ALL TO service_role  USING (true);
