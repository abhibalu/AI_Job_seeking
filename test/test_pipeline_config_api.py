"""test/test_pipeline_config_api.py — GET/PATCH /api/pipeline/config."""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))
from _api_test_utils import build_client, neutralize_app_side_effects  # noqa: E402


class TestReadPipelineConfig(unittest.TestCase):
    def setUp(self):
        neutralize_app_side_effects(self)
        self.client = build_client()

    @patch("api.routes.pipeline_config.get_pipeline_config")
    def test_returns_current_config(self, mock_get):
        mock_get.return_value = {
            "scrape_mode": "auto", "evaluate_mode": "auto",
            "tailor_mode": "manual", "auto_send_threshold": 0,
        }
        resp = self.client.get("/api/pipeline/config")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["tailor_mode"], "manual")


class TestPatchPipelineConfig(unittest.TestCase):
    def setUp(self):
        neutralize_app_side_effects(self)
        self.client = build_client()

    @patch("api.routes.pipeline_config.set_pipeline_config")
    def test_partial_update(self, mock_set):
        mock_set.return_value = {
            "scrape_mode": "manual", "evaluate_mode": "auto",
            "tailor_mode": "manual", "auto_send_threshold": 0,
        }
        resp = self.client.patch("/api/pipeline/config", json={"scrape_mode": "manual"})
        self.assertEqual(resp.status_code, 200)
        mock_set.assert_called_once_with({"scrape_mode": "manual"})
        self.assertEqual(resp.json()["scrape_mode"], "manual")

    @patch("api.routes.pipeline_config.get_pipeline_config")
    @patch("api.routes.pipeline_config.set_pipeline_config")
    def test_empty_body_returns_current_config(self, mock_set, mock_get):
        mock_get.return_value = {
            "scrape_mode": "auto", "evaluate_mode": "auto",
            "tailor_mode": "manual", "auto_send_threshold": 0,
        }
        resp = self.client.patch("/api/pipeline/config", json={})
        self.assertEqual(resp.status_code, 200)
        mock_set.assert_not_called()
        mock_get.assert_called_once()

    def test_invalid_mode_caught_by_pydantic(self):
        resp = self.client.patch("/api/pipeline/config", json={"scrape_mode": "turbo"})
        # Literal validator rejects pre-handler → 422.
        self.assertEqual(resp.status_code, 422)

    def test_threshold_out_of_range_caught_by_pydantic(self):
        resp = self.client.patch("/api/pipeline/config", json={"auto_send_threshold": 9})
        self.assertEqual(resp.status_code, 422)

    @patch("api.routes.pipeline_config.set_pipeline_config")
    def test_helper_value_error_becomes_400(self, mock_set):
        # If set_pipeline_config raises ValueError for any reason (race with a
        # bad config state, etc.), surface as 400 rather than 500.
        mock_set.side_effect = ValueError("invalid mode 'turbo' for scrape_mode")
        resp = self.client.patch("/api/pipeline/config", json={"scrape_mode": "auto"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("invalid mode", resp.json()["detail"])


if __name__ == "__main__":
    unittest.main()
