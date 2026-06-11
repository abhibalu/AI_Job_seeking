"""test/test_pipeline_mode_gate.py — Task 20.

The cron-fired scheduler wrappers (_gated_scrape_worker / _gated_eval_worker)
must:
  - no-op when pipeline_*_mode == 'manual'
  - call the underlying worker when mode == 'auto'

The manual /trigger/scrape route still spawns run_scrape_worker() directly
and bypasses this gate — see api/routes/scheduler.py.
"""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestScrapeGate(unittest.TestCase):
    @patch("services.scraper_worker.run_scrape_worker")
    @patch("agents.database.get_pipeline_config")
    def test_no_op_when_manual(self, mock_cfg, mock_worker):
        from services.scheduler import _gated_scrape_worker

        mock_cfg.return_value = {
            "scrape_mode": "manual", "evaluate_mode": "auto",
            "tailor_mode": "manual", "auto_send_threshold": 0,
        }
        _gated_scrape_worker()
        mock_worker.assert_not_called()

    @patch("services.scraper_worker.run_scrape_worker")
    @patch("agents.database.get_pipeline_config")
    def test_runs_when_auto(self, mock_cfg, mock_worker):
        from services.scheduler import _gated_scrape_worker

        mock_cfg.return_value = {
            "scrape_mode": "auto", "evaluate_mode": "auto",
            "tailor_mode": "manual", "auto_send_threshold": 0,
        }
        _gated_scrape_worker()
        mock_worker.assert_called_once()

    @patch("services.scraper_worker.run_scrape_worker")
    @patch("agents.database.get_pipeline_config")
    def test_runs_when_mode_missing(self, mock_cfg, mock_worker):
        """A missing scrape_mode key (transient DB hiccup) must NOT silently
        block the cron — fall through to running the worker."""
        from services.scheduler import _gated_scrape_worker

        mock_cfg.return_value = {}  # nothing
        _gated_scrape_worker()
        mock_worker.assert_called_once()


class TestEvalGate(unittest.TestCase):
    @patch("services.eval_worker.run_eval_worker")
    @patch("agents.database.get_pipeline_config")
    def test_no_op_when_manual(self, mock_cfg, mock_worker):
        from services.scheduler import _gated_eval_worker

        mock_cfg.return_value = {
            "scrape_mode": "auto", "evaluate_mode": "manual",
            "tailor_mode": "manual", "auto_send_threshold": 0,
        }
        _gated_eval_worker()
        mock_worker.assert_not_called()

    @patch("services.eval_worker.run_eval_worker")
    @patch("agents.database.get_pipeline_config")
    def test_runs_when_auto(self, mock_cfg, mock_worker):
        from services.scheduler import _gated_eval_worker

        mock_cfg.return_value = {
            "scrape_mode": "auto", "evaluate_mode": "auto",
            "tailor_mode": "manual", "auto_send_threshold": 0,
        }
        _gated_eval_worker()
        mock_worker.assert_called_once()


if __name__ == "__main__":
    unittest.main()
