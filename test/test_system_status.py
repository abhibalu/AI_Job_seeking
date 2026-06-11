"""test/test_system_status.py — GET /api/system/status state derivation."""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(__file__))
from _api_test_utils import build_client, neutralize_app_side_effects  # noqa: E402


def _scheduler_mock(running: bool) -> MagicMock:
    sched = MagicMock()
    sched.running = running
    return sched


class TestSystemStatus(unittest.TestCase):
    def setUp(self):
        neutralize_app_side_effects(self)
        self.client = build_client()

    @patch("api.routes.system.get_last_run", lambda _t: None)
    @patch("api.routes.system.get_job_status")
    @patch("api.routes.system.get_scheduler")
    def test_active_when_running_and_next_run_present(self, mock_sched, mock_jobs):
        mock_sched.return_value = _scheduler_mock(running=True)
        mock_jobs.return_value = [
            {"id": "scrape_worker", "next_run_utc": "2026-06-12T17:00:00+00:00"},
            {"id": "eval_worker",   "next_run_utc": "2026-06-12T17:05:00+00:00"},
            {"id": "reap_stale_tailoring_runs", "next_run_utc": "2026-06-11T20:30:00+00:00"},
        ]
        body = self.client.get("/api/system/status").json()
        self.assertEqual(body["cron_state"], "active")
        # Earliest next_run across hunt jobs (reaper excluded).
        self.assertEqual(body["next_run_at"], "2026-06-12T17:00:00+00:00")
        self.assertIsNone(body["last_error"])

    @patch("api.routes.system.get_last_run", lambda _t: None)
    @patch("api.routes.system.get_job_status")
    @patch("api.routes.system.get_scheduler")
    def test_sleeping_when_running_but_no_hunt_next_run(self, mock_sched, mock_jobs):
        mock_sched.return_value = _scheduler_mock(running=True)
        # Only the reaper has a next run — counts as "sleeping" not "active".
        mock_jobs.return_value = [
            {"id": "reap_stale_tailoring_runs", "next_run_utc": "2026-06-11T20:30:00+00:00"}
        ]
        body = self.client.get("/api/system/status").json()
        self.assertEqual(body["cron_state"], "sleeping")
        self.assertIsNone(body["next_run_at"])

    @patch("api.routes.system.get_last_run", lambda _t: None)
    @patch("api.routes.system.get_job_status", lambda: [])
    @patch("api.routes.system.get_scheduler")
    def test_error_when_scheduler_not_running(self, mock_sched):
        mock_sched.return_value = _scheduler_mock(running=False)
        body = self.client.get("/api/system/status").json()
        self.assertEqual(body["cron_state"], "error")
        self.assertIsNone(body["next_run_at"])

    @patch("api.routes.system.get_job_status", lambda: [])
    @patch("api.routes.system.get_scheduler")
    @patch("api.routes.system.get_last_run")
    def test_last_error_surfaces_from_failed_run(self, mock_last, mock_sched):
        mock_sched.return_value = _scheduler_mock(running=False)
        def last(run_type):
            if run_type == "scrape":
                return None
            if run_type == "evaluate":
                return {"status": "failed", "error_detail": "OpenRouter 429"}
            return None
        mock_last.side_effect = last
        body = self.client.get("/api/system/status").json()
        self.assertEqual(body["cron_state"], "error")
        self.assertEqual(body["last_error"], "OpenRouter 429")

    @patch("api.routes.system.get_job_status", lambda: [])
    @patch("api.routes.system.get_scheduler")
    @patch("api.routes.system.get_last_run", lambda _t: {"status": "completed"})
    def test_completed_runs_do_not_set_last_error(self, mock_sched):
        mock_sched.return_value = _scheduler_mock(running=True)
        body = self.client.get("/api/system/status").json()
        self.assertIsNone(body["last_error"])


if __name__ == "__main__":
    unittest.main()
