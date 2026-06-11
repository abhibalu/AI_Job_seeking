"""test/test_runs_api.py — contract tests for GET /api/runs and /api/runs/{id}."""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))
from _api_test_utils import build_client, neutralize_app_side_effects  # noqa: E402


class TestListRunsEndpoint(unittest.TestCase):
    def setUp(self):
        neutralize_app_side_effects(self)
        self.client = build_client()

    @patch("api.routes.runs.list_runs")
    def test_returns_rpc_rows(self, mock_list):
        rows = [{
            "id": "r1", "started_at": "2026-06-11T17:00:00+00:00",
            "finished_at": "2026-06-11T17:02:00+00:00",
            "status": "completed", "jobs_found": 8,
            "tailor_count": 2, "borderline_count": 1,
            "apply_direct_count": 1, "skip_count": 4,
        }]
        mock_list.return_value = rows
        resp = self.client.get("/api/runs?limit=10")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["tailor_count"], 2)
        mock_list.assert_called_once_with(limit=10)

    @patch("api.routes.runs.list_runs")
    def test_default_limit(self, mock_list):
        mock_list.return_value = []
        resp = self.client.get("/api/runs")
        self.assertEqual(resp.status_code, 200)
        mock_list.assert_called_once_with(limit=50)

    def test_rejects_limit_out_of_range(self):
        self.assertEqual(self.client.get("/api/runs?limit=0").status_code, 422)
        self.assertEqual(self.client.get("/api/runs?limit=999").status_code, 422)


class TestGetRunEndpoint(unittest.TestCase):
    def setUp(self):
        neutralize_app_side_effects(self)
        self.client = build_client()

    @patch("api.routes.runs.get_run")
    def test_returns_row(self, mock_get):
        mock_get.return_value = {"id": "r1", "status": "completed"}
        resp = self.client.get("/api/runs/r1")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["id"], "r1")

    @patch("api.routes.runs.get_run")
    def test_returns_404_when_missing(self, mock_get):
        mock_get.return_value = None
        resp = self.client.get("/api/runs/nope")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
