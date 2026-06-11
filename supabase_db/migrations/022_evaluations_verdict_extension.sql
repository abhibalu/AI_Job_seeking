-- Migration 022: 4-way verdict + pre-computed card-line summaries.
-- ADR-0023.
--
-- Extends recommended_action from {apply, tailor, skip} to the OotoCV set:
--   {tailor, borderline, apply_direct, skip}
-- The legacy 'apply' value is retained in the CHECK so historical rows stay
-- valid; the evaluator stops emitting it. Historical rows are re-evaluated
-- on-demand from the UI (no mass migration).
--
-- Adds three card-line text columns (exactly one populated per verdict) and
-- a red_flags JSONB array for the SKIP layout. red_flags use a load-bearing
-- em-dash format (" — ") between label and explanation — the frontend splits
-- on it. The evaluator writer normalizes hyphens to em-dash on read (R6).

ALTER TABLE job_evaluations
  DROP CONSTRAINT IF EXISTS job_evaluations_recommended_action_check;

ALTER TABLE job_evaluations
  ADD CONSTRAINT job_evaluations_recommended_action_check
  CHECK (recommended_action IN (
    -- Legacy (historical rows; evaluator no longer emits)
    'apply',
    -- OotoCV vocab
    'tailor', 'borderline', 'apply_direct', 'skip'
  ));

ALTER TABLE job_evaluations
  ADD COLUMN IF NOT EXISTS top_strength    TEXT,
  ADD COLUMN IF NOT EXISTS deciding_factor TEXT,
  ADD COLUMN IF NOT EXISTS kill_shot       TEXT,
  ADD COLUMN IF NOT EXISTS red_flags       JSONB NOT NULL DEFAULT '[]'::jsonb;

COMMENT ON COLUMN job_evaluations.top_strength IS
  'One-line strength surfaced on TAILOR feed cards. '
  'NULL on non-TAILOR verdicts. Pre-computed by evaluator.';
COMMENT ON COLUMN job_evaluations.deciding_factor IS
  'One-line "this is what tips it" surfaced on BORDERLINE feed cards and '
  'detail page hero. NULL on non-BORDERLINE verdicts.';
COMMENT ON COLUMN job_evaluations.kill_shot IS
  'One-line rejection reason surfaced on SKIP cards and detail page '
  '(red banner). NULL on non-SKIP verdicts.';
COMMENT ON COLUMN job_evaluations.red_flags IS
  'Array of "Label — explanation" strings for the SKIP layout. '
  'Em-dash separator is load-bearing — the frontend splits on " — ". '
  'Backend (agents/evaluator.py) normalizes hyphens/en-dashes to em-dash on read.';
