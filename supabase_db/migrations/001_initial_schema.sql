-- TailorAI Supabase Schema
-- Simpler schema using JSONB for nested data

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- CORE TABLES
-- ============================================

-- Jobs table (source of truth for job data)
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    company_name TEXT,
    title TEXT,
    location TEXT,
    description_text TEXT,
    job_url TEXT,
    posted_at TIMESTAMPTZ,
    seniority_level TEXT,
    employment_type TEXT,
    applicants_count INTEGER,
    company_website TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Job Evaluations (1:1 with jobs)
CREATE TABLE IF NOT EXISTS job_evaluations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id TEXT UNIQUE NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    
    -- Basic info (denormalized for convenience)
    company_name TEXT,
    title_role TEXT,
    job_url TEXT,
    
    -- Evaluation results
    verdict TEXT CHECK (verdict IN ('Strong Match', 'Moderate Match', 'Weak Match')),
    job_match_score INTEGER CHECK (job_match_score BETWEEN 0 AND 100),
    summary TEXT,
    required_exp TEXT,
    recommended_action TEXT CHECK (recommended_action IN ('apply', 'tailor', 'skip')),
    
    -- JSONB fields for nested data
    gaps JSONB DEFAULT '{}',
    improvement_suggestions JSONB DEFAULT '{}',
    interview_tips JSONB DEFAULT '{}',
    jd_keywords JSONB DEFAULT '[]',
    matched_keywords JSONB DEFAULT '[]',
    missing_keywords JSONB DEFAULT '[]',
    
    -- Metadata
    model_used TEXT,
    evaluated_at TIMESTAMPTZ DEFAULT NOW(),
    raw_response JSONB
);

-- JD Parsed Signals (1:1 with jobs)
CREATE TABLE IF NOT EXISTS jd_parsed (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id TEXT UNIQUE NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    
    -- Parsed fields
    domain TEXT,
    seniority TEXT CHECK (seniority IN ('junior', 'mid', 'senior', 'lead', 'unspecified', NULL)),
    
    -- JSONB fields for arrays
    must_haves JSONB DEFAULT '[]',
    nice_to_haves JSONB DEFAULT '[]',
    location_constraints JSONB DEFAULT '[]',
    ats_keywords JSONB DEFAULT '[]',
    normalized_skills JSONB DEFAULT '{}',
    
    -- Metadata
    model_used TEXT,
    parsed_at TIMESTAMPTZ DEFAULT NOW(),
    raw_response JSONB
);

-- Async Tasks
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id TEXT UNIQUE NOT NULL,
    status TEXT CHECK (status IN ('queued', 'running', 'completed', 'failed')),
    progress JSONB DEFAULT '{}',
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- ============================================
-- INDEXES
-- ============================================

CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company_name);
CREATE INDEX IF NOT EXISTS idx_evaluations_job_id ON job_evaluations(job_id);
CREATE INDEX IF NOT EXISTS idx_evaluations_verdict ON job_evaluations(verdict);
CREATE INDEX IF NOT EXISTS idx_evaluations_score ON job_evaluations(job_match_score);
CREATE INDEX IF NOT EXISTS idx_evaluations_action ON job_evaluations(recommended_action);
CREATE INDEX IF NOT EXISTS idx_jd_parsed_job_id ON jd_parsed(job_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_task_id ON tasks(task_id);

-- GIN indexes for JSONB querying
CREATE INDEX IF NOT EXISTS idx_evaluations_gaps ON job_evaluations USING GIN (gaps);
CREATE INDEX IF NOT EXISTS idx_evaluations_jd_keywords ON job_evaluations USING GIN (jd_keywords);
CREATE INDEX IF NOT EXISTS idx_jd_parsed_skills ON jd_parsed USING GIN (normalized_skills);

-- ============================================
-- ROW LEVEL SECURITY
-- ============================================

-- Enable RLS
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE jd_parsed ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

-- Allow all for service role (adjust for multi-user later)
DROP POLICY IF EXISTS "Allow all for authenticated" ON jobs;
DROP POLICY IF EXISTS "Allow all for authenticated" ON job_evaluations;
DROP POLICY IF EXISTS "Allow all for authenticated" ON jd_parsed;
DROP POLICY IF EXISTS "Allow all for authenticated" ON tasks;

CREATE POLICY "Allow all for authenticated" ON jobs FOR ALL TO authenticated USING (true);
CREATE POLICY "Allow all for authenticated" ON job_evaluations FOR ALL TO authenticated USING (true);
CREATE POLICY "Allow all for authenticated" ON jd_parsed FOR ALL TO authenticated USING (true);
CREATE POLICY "Allow all for authenticated" ON tasks FOR ALL TO authenticated USING (true);

-- Also allow service_role full access
DROP POLICY IF EXISTS "Allow all for service_role" ON jobs;
DROP POLICY IF EXISTS "Allow all for service_role" ON job_evaluations;
DROP POLICY IF EXISTS "Allow all for service_role" ON jd_parsed;
DROP POLICY IF EXISTS "Allow all for service_role" ON tasks;

CREATE POLICY "Allow all for service_role" ON jobs FOR ALL TO service_role USING (true);
CREATE POLICY "Allow all for service_role" ON job_evaluations FOR ALL TO service_role USING (true);
CREATE POLICY "Allow all for service_role" ON jd_parsed FOR ALL TO service_role USING (true);
CREATE POLICY "Allow all for service_role" ON tasks FOR ALL TO service_role USING (true);

-- ============================================
-- UPDATED_AT TRIGGER
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_jobs_updated_at ON jobs;
CREATE TRIGGER update_jobs_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
