-- Migration 025: Per-stage pipeline mode seeds.
-- ADR-0024.
--
-- These are distinct from kill switches (service_*_enabled, ADR-0019):
--   * mode  = "should the agent run this stage automatically?" (user-facing toggle)
--   * kill  = "is this external service available?"            (operator-facing safety)
-- Surfaced as the Scrape/Evaluate/Tailor pills in the OotoCV feed header.
--
-- Defaults: scrape and evaluate run on cron (auto); tailoring stays manual
-- until the user explicitly opts in via the auto_send_threshold consent
-- modal (ADR-0012). This prevents cost runaway from a forgotten threshold (R7).

INSERT INTO system_config (key, value) VALUES
  ('pipeline_scrape_mode',   'auto'),
  ('pipeline_evaluate_mode', 'auto'),
  ('pipeline_tailor_mode',   'manual')
ON CONFLICT (key) DO NOTHING;
