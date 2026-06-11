"""test/test_applications_offer_and_commentary.py.

Phase 3 / Task 15. Covers:
  - compute_ghost_commentary bracket boundaries (helper-level)
  - GET /api/applications enrichment (ghost_commentary + days_since_update + no-store)
  - PATCH /api/applications/{id}/status accepts 'offer'
"""
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(__file__))
from _api_test_utils import build_client, neutralize_app_side_effects  # noqa: E402


# ─────────────────────────────────────────────────────────────────
# 1. helper-level (no API)
# ─────────────────────────────────────────────────────────────────
class TestGhostCommentaryBrackets(unittest.TestCase):
    def test_brackets(self):
        from agents.database import compute_ghost_commentary

        cases = [
            (0,  "Probably just busy."),
            (3,  "Probably just busy."),
            (4,  "Still nothing. Rude, but fine."),
            (7,  "Still nothing. Rude, but fine."),
            (8,  "At this point we're assuming they lost it."),
            (14, "At this point we're assuming they lost it."),
            (15, "They don't deserve you."),
            (99, "They don't deserve you."),
        ]
        for days, expected in cases:
            with self.subTest(days=days):
                self.assertEqual(compute_ghost_commentary(days), expected)


# ─────────────────────────────────────────────────────────────────
# 2. GET /api/applications enrichment
# ─────────────────────────────────────────────────────────────────
def _ts(days_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()


def _stub_supabase_select(rows: list[dict]) -> MagicMock:
    """Mock for `client.table('applications').select(...).order(...).execute()`."""
    final = MagicMock()
    final.execute.return_value = MagicMock(data=rows)
    chain = MagicMock()
    for method in ("select", "order"):
        getattr(chain, method).return_value = chain
    chain.execute = final.execute
    client = MagicMock()
    client.table.return_value = chain
    return client


class TestListApplicationsEnrichment(unittest.TestCase):
    def setUp(self):
        neutralize_app_side_effects(self)
        self.client = build_client()

    @patch("api.routes.applications.get_supabase_client")
    def test_enriches_each_row(self, mock_get_client):
        eight_days_ago = _ts(days_ago=8)
        rows = [{
            "id": "a1",
            "job_id": "j1",
            "job_title": "Eng",
            "company_name": "X",
            "resume_id": None,
            "cv_version": "base",
            "status": "ghosting",
            "status_history": [{"status": "applied", "timestamp": eight_days_ago}],
            "applied_at": eight_days_ago,
        }]
        mock_get_client.return_value = _stub_supabase_select(rows)

        resp = self.client.get("/api/applications")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("cache-control"), "no-store")
        body = resp.json()
        self.assertEqual(len(body), 1)
        self.assertGreaterEqual(body[0]["days_since_update"], 7)
        self.assertLessEqual(body[0]["days_since_update"], 9)
        self.assertEqual(
            body[0]["ghost_commentary"],
            "At this point we're assuming they lost it.",
        )

    @patch("api.routes.applications.get_supabase_client")
    def test_falls_back_to_applied_at_when_history_empty(self, mock_get_client):
        twenty_days_ago = _ts(days_ago=20)
        rows = [{
            "id": "a2",
            "job_id": "j2",
            "status": "applied",
            "status_history": [],
            "applied_at": twenty_days_ago,
        }]
        mock_get_client.return_value = _stub_supabase_select(rows)

        body = self.client.get("/api/applications").json()
        self.assertEqual(body[0]["ghost_commentary"], "They don't deserve you.")

    @patch("api.routes.applications.get_supabase_client")
    def test_handles_unparseable_timestamps(self, mock_get_client):
        """A garbage timestamp must not 500 the endpoint — fall through to 0 days."""
        rows = [{
            "id": "a3",
            "job_id": "j3",
            "status": "applied",
            "status_history": [{"status": "applied", "timestamp": "not-a-date"}],
            "applied_at": None,
        }]
        mock_get_client.return_value = _stub_supabase_select(rows)

        body = self.client.get("/api/applications").json()
        self.assertEqual(body[0]["days_since_update"], 0)
        self.assertEqual(body[0]["ghost_commentary"], "Probably just busy.")

    @patch("api.routes.applications.get_supabase_client")
    def test_empty_table(self, mock_get_client):
        mock_get_client.return_value = _stub_supabase_select([])
        resp = self.client.get("/api/applications")
        self.assertEqual(resp.json(), [])


# ─────────────────────────────────────────────────────────────────
# 3. PATCH accepts offer
# ─────────────────────────────────────────────────────────────────
def _stub_supabase_for_patch(existing_history: list[dict]) -> MagicMock:
    """Mock both the SELECT (history) and UPDATE (write back) chains."""
    select_final = MagicMock()
    select_final.execute.return_value = MagicMock(
        data={"status_history": existing_history}
    )
    select_chain = MagicMock()
    for m in ("select", "eq", "single"):
        getattr(select_chain, m).return_value = select_chain
    select_chain.execute = select_final.execute

    update_final = MagicMock()
    update_final.execute.return_value = MagicMock(data=[{
        "id": "a1", "status": "offer",
        "status_history": existing_history + [{"status": "offer", "timestamp": "x"}],
    }])
    update_chain = MagicMock()
    for m in ("update", "eq"):
        getattr(update_chain, m).return_value = update_chain
    update_chain.execute = update_final.execute

    client = MagicMock()
    # Two .table() calls in the handler: first for SELECT, second for UPDATE.
    client.table.side_effect = [select_chain, update_chain]
    return client


class TestPatchStatusAcceptsOffer(unittest.TestCase):
    def setUp(self):
        neutralize_app_side_effects(self)
        self.client = build_client()

    @patch("api.routes.applications.get_supabase_client")
    def test_offer_status_accepted(self, mock_get_client):
        mock_get_client.return_value = _stub_supabase_for_patch(
            existing_history=[{"status": "interview", "timestamp": "t1"}]
        )
        resp = self.client.patch(
            "/api/applications/a1/status", json={"status": "offer"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "offer")

    @patch("api.routes.applications.get_supabase_client")
    def test_rejects_unknown_status(self, mock_get_client):
        mock_get_client.return_value = _stub_supabase_for_patch(existing_history=[])
        resp = self.client.patch(
            "/api/applications/a1/status", json={"status": "ascended"}
        )
        self.assertEqual(resp.status_code, 422)


if __name__ == "__main__":
    unittest.main()
