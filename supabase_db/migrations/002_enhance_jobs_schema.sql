-- Migration 002: Enhance Jobs Schema and Add Status
-- Adds richer fields from Silver layer and status column for soft deletes

-- 1. Add Status Column
ALTER TABLE jobs 
ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived', 'deleted'));

-- 2. Add Richer Job Details
ALTER TABLE jobs 
ADD COLUMN IF NOT EXISTS job_function JSONB DEFAULT '[]',
ADD COLUMN IF NOT EXISTS industries JSONB DEFAULT '[]',
ADD COLUMN IF NOT EXISTS salary_min NUMERIC,
ADD COLUMN IF NOT EXISTS salary_max NUMERIC,
ADD COLUMN IF NOT EXISTS salary_currency TEXT,
ADD COLUMN IF NOT EXISTS salary_interval TEXT CHECK (salary_interval IN ('hourly', 'monthly', 'yearly', NULL)),
ADD COLUMN IF NOT EXISTS salary_info TEXT,  -- Raw salary string
ADD COLUMN IF NOT EXISTS benefits JSONB DEFAULT '[]';

-- 3. Add Richer Company Details
ALTER TABLE jobs 
ADD COLUMN IF NOT EXISTS company_linkedin_url TEXT,
ADD COLUMN IF NOT EXISTS company_logo TEXT,
ADD COLUMN IF NOT EXISTS company_description TEXT,
ADD COLUMN IF NOT EXISTS company_slogan TEXT,
ADD COLUMN IF NOT EXISTS company_employees_count INTEGER,
ADD COLUMN IF NOT EXISTS company_city TEXT,
ADD COLUMN IF NOT EXISTS company_state TEXT,
ADD COLUMN IF NOT EXISTS company_country TEXT,
ADD COLUMN IF NOT EXISTS company_postal_code TEXT,
ADD COLUMN IF NOT EXISTS company_street_address TEXT;

-- 4. Add Job Poster Details
ALTER TABLE jobs 
ADD COLUMN IF NOT EXISTS job_poster_name TEXT,
ADD COLUMN IF NOT EXISTS job_poster_title TEXT,
ADD COLUMN IF NOT EXISTS job_poster_profile_url TEXT;

-- 5. Add Apply/Input URLs
ALTER TABLE jobs 
ADD COLUMN IF NOT EXISTS apply_url TEXT,
ADD COLUMN IF NOT EXISTS input_url TEXT;

-- 6. Add Indexes for new searchable columns
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_location_city ON jobs(company_city);
CREATE INDEX IF NOT EXISTS idx_jobs_location_country ON jobs(company_country);
