"""test/test_change_feedback.py.

Phase 3 / Task 16. Contract tests for the sibling endpoint
POST /api/resumes/{resume_id}/changes/{change_id}/feedback.

Roast endpoint (Task 17) tests live in test_resume_roast.py.
"""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))
from _api_test_utils import build_client, neutralize_app_side_effects  # noqa: E402


class TestSubmitChangeFeedback(unittest.TestCase):
    def setUp(self):
        neutralize_app_side_effects(self)
        self.client = build_client()

    @patch("api.routes.resume_change_feedback.record_change_feedback")
    def test_records_feedback_returns_row(self, mock_record):
        mock_record.return_value = {
            "id": "c1", "review_action": "reject",
            "feedback_type": "too_formal", "regeneration_count": 1,
        }
        resp = self.client.post(
            "/api/resumes/r1/changes/c1/feedback",
            json={"feedback_type": "too_formal"},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["regeneration_count"], 1)
        mock_record.assert_called_once_with(
            change_id="c1", feedback_type="too_formal"
        )

    @patch("api.routes.resume_change_feedback.record_change_feedback")
    def test_cap_reached_returns_409(self, mock_record):
        from agents.database import RegenerationCapReached

        mock_record.side_effect = RegenerationCapReached("cap=2")
        resp = self.client.post(
            "/api/resumes/r1/changes/c1/feedback",
            json={"feedback_type": "other"},
        )
        self.assertEqual(resp.status_code, 409)
        self.assertIn("cap=2", resp.json()["detail"])

    def test_pydantic_rejects_unknown_chip(self):
        resp = self.client.post(
            "/api/resumes/r1/changes/c1/feedback",
            json={"feedback_type": "bogus_chip"},
        )
        self.assertEqual(resp.status_code, 422)

    def test_missing_body_field(self):
        resp = self.client.post(
            "/api/resumes/r1/changes/c1/feedback",
            json={},
        )
        self.assertEqual(resp.status_code, 422)

    @patch("api.routes.resume_change_feedback.record_change_feedback")
    def test_helper_value_error_becomes_400(self, mock_record):
        mock_record.side_effect = ValueError("helper-side reject")
        resp = self.client.post(
            "/api/resumes/r1/changes/c1/feedback",
            json={"feedback_type": "not_accurate"},
        )
        self.assertEqual(resp.status_code, 400)


if __name__ == "__main__":
    unittest.main()
