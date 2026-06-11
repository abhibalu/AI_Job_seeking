"""test/test_resume_roast.py.

Phase 3 / Task 17. Contract tests for POST /api/resumes/roast (transient).
LLM is mocked via roast_resume(); no real OpenRouter call.
"""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))
from _api_test_utils import build_client, neutralize_app_side_effects  # noqa: E402


class TestRoastEndpoint(unittest.TestCase):
    def setUp(self):
        neutralize_app_side_effects(self)
        self.client = build_client()

    @patch("backend.service_guard.require_service", lambda _name: None)
    @patch("api.routes.resume_roast.roast_resume")
    def test_returns_items(self, mock_roast):
        mock_roast.return_value = {
            "items": [{
                "section": "Summary",
                "quote": "Synergistic results-driven leader",
                "verdict": "Buzzword soup.",
                "fixed": "Engineering manager.",
            }]
        }
        resp = self.client.post("/api/resumes/roast", json={"resume_id": "r1"})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body["items"]), 1)
        self.assertEqual(body["items"][0]["section"], "Summary")
        mock_roast.assert_called_once_with(resume_id="r1")

    @patch("backend.service_guard.require_service", lambda _name: None)
    @patch("api.routes.resume_roast.roast_resume")
    def test_accepts_empty_body(self, mock_roast):
        mock_roast.return_value = {"items": []}
        resp = self.client.post("/api/resumes/roast", json={})
        self.assertEqual(resp.status_code, 200)
        mock_roast.assert_called_once_with(resume_id=None)


class TestRoastHelper(unittest.TestCase):
    @patch("agents.roast.get_master_resume")
    def test_returns_empty_items_when_no_master(self, mock_get):
        from agents.roast import roast_resume

        mock_get.return_value = None
        self.assertEqual(roast_resume(), {"items": []})

    @patch("agents.roast.get_master_resume")
    def test_returns_empty_items_when_master_content_empty(self, mock_get):
        from agents.roast import roast_resume

        mock_get.return_value = {"content": None}
        self.assertEqual(roast_resume(), {"items": []})

    @patch("agents.roast.ResumeRoastAgent")
    @patch("agents.roast.get_master_resume")
    def test_swallows_agent_failure(self, mock_get, mock_agent_cls):
        from agents.roast import roast_resume

        mock_get.return_value = {"content": {"basics": {"name": "X"}}}
        mock_agent_cls.return_value.run.side_effect = RuntimeError("LLM down")
        # Should NOT raise — the Settings UI just gets an empty roast.
        self.assertEqual(roast_resume(), {"items": []})

    @patch("agents.roast.ResumeRoastAgent")
    @patch("agents.roast.get_master_resume")
    def test_filters_non_list_items(self, mock_get, mock_agent_cls):
        from agents.roast import roast_resume

        mock_get.return_value = {"content": {"basics": {"name": "X"}}}
        mock_agent_cls.return_value.run.return_value = {"items": "not a list"}
        self.assertEqual(roast_resume(), {"items": []})

    @patch("agents.roast.ResumeRoastAgent")
    @patch("agents.roast.get_master_resume")
    def test_passes_through_items_list(self, mock_get, mock_agent_cls):
        from agents.roast import roast_resume

        mock_get.return_value = {"content": {"basics": {"name": "X"}}}
        mock_agent_cls.return_value.run.return_value = {
            "items": [
                {"section": "Summary", "quote": "Q", "verdict": "V", "fixed": "F"},
            ],
            "_model_used": "anthropic/claude-x",
            "_agent": "ResumeRoastAgent",
        }
        result = roast_resume()
        self.assertEqual(len(result["items"]), 1)
        # Metadata fields from BaseAgent.run() are dropped — only items in
        # the response shape.
        self.assertNotIn("_model_used", result)


if __name__ == "__main__":
    unittest.main()
