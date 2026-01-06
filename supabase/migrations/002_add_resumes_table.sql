-- Add resumes table for storing parsed JSON resumes
CREATE TABLE IF NOT EXISTS resumes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    content JSONB,
    is_master BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for finding master resume quickly
CREATE INDEX IF NOT EXISTS idx_resumes_is_master ON resumes(is_master);

-- Trigger for updated_at
DROP TRIGGER IF EXISTS update_resumes_updated_at ON resumes;
CREATE TRIGGER update_resumes_updated_at
    BEFORE UPDATE ON resumes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- RLS
ALTER TABLE resumes ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow all for authenticated" ON resumes;
CREATE POLICY "Allow all for authenticated" ON resumes FOR ALL TO authenticated USING (true);

DROP POLICY IF EXISTS "Allow all for service_role" ON resumes;
CREATE POLICY "Allow all for service_role" ON resumes FOR ALL TO service_role USING (true);
