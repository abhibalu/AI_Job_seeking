-- Consolidate resumes and tailored_resumes into a single table
-- Add new columns to resumes table
ALTER TABLE resumes 
ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS job_id TEXT,  -- Changed from UUID to TEXT to support numeric Job IDs
ADD COLUMN IF NOT EXISTS version INTEGER;

-- Create index for new columns
CREATE INDEX IF NOT EXISTS idx_resumes_job_id ON resumes(job_id);
CREATE INDEX IF NOT EXISTS idx_resumes_status ON resumes(status);

-- Update existing master resumes to have status='master'
UPDATE resumes 
SET status = 'master' 
WHERE is_master = TRUE;

-- Migrate data from tailored_resumes to resumes
INSERT INTO resumes (id, job_id, version, content, status, created_at, name)
SELECT 
    id::uuid, 
    job_id, -- No cast to UUID needed, keep as TEXT
    version,
    content,
    status,
    created_at,
    'Tailored Resume V' || version
FROM tailored_resumes;

-- Drop foreign key constraint if it exists (check name or use generic drop)
-- ALTER TABLE tailored_resumes DROP CONSTRAINT IF EXISTS tailored_resumes_job_id_fkey;

-- We can keep is_master for now as a generated column or just drop it
-- Let's drop it to be clean, but verify migration first
ALTER TABLE resumes DROP COLUMN is_master;

-- Drop the old table
DROP TABLE IF EXISTS tailored_resumes;
