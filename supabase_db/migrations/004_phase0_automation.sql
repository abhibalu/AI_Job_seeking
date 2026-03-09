-- Phase 0: Autonomous Pipeline Foundation
-- Migration 004: Add raw_json replay column to jobs + create pipeline_runs monitoring table

-- ============================================
-- 1. Add raw_json column to jobs table
--    Stores the original Apify payload for future replay/reprocessing
-- ============================================
ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS raw_json JSONB;

COMMENT ON COLUMN jobs.raw_json IS 
  'Original raw JSON payload from Apify scraper. Acts as Bronze layer safety net — allows full reprocessing without re-scraping.';


-- ============================================
-- 2. Create pipeline_runs monitoring table
--    Tracks every scheduled background job run for observability
-- ============================================
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_type        TEXT NOT NULL CHECK (run_type IN ('scrape', 'evaluate', 'tailor', 'full_pipeline')),
    status          TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed', 'skipped')),
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    jobs_found      INT,
    jobs_processed  INT,
    jobs_skipped    INT,
    error_detail    TEXT,
    metadata        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE pipeline_runs IS
  'Observability log for all background pipeline runs (scrape, evaluate, tailor). Powers the /api/scheduler/status endpoint.';

-- Index for fast status endpoint queries
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_run_type ON pipeline_runs(run_type);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at ON pipeline_runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON pipeline_runs(status);
