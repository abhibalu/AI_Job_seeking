"""
test/test_ootocv_schema.py

OotoCV adaptation (Phase 2) — unit tests for the database helpers added by
migrations 021–025 and ADRs 0023–0025. Fully mocked; no Supabase round-trip.

Covers:
  - list_runs / get_run               (Task 9 / ADR-0025)
  - get_pipeline_config / set_*       (Task 10 / ADR-0024)
  - compute_ghost_commentary          (Task 11)
  - record_change_feedback + cap      (related to migration 024)
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def _mock_supabase_chain(return_data):
    """Build a MagicMock chain that mimics the supabase-py builder pattern.

    Every method on the chain returns itself so a long .update().eq().eq()
    builder ends up at the same .execute() mock.
    """
    final = MagicMock()
    final.execute.return_value = MagicMock(data=return_data)
    chain = MagicMock()
    for method in (
        "insert", "update", "upsert", "select",
        "eq", "in_", "lt", "lte", "gt", "gte",
        "order", "limit", "rpc",
    ):
        getattr(chain, method).return_value = chain
    chain.execute = final.execute
    return chain


# ─────────────────────────────────────────────────────────────────
# 1.  list_runs / get_run (ADR-0025)
# ─────────────────────────────────────────────────────────────────
class TestListRuns(unittest.TestCase):
    @patch("agents.database._get_supabase")
    def test_list_runs_returns_rpc_rows(self, mock_get_supabase):
        from agents.database import list_runs

        rpc_rows = [
            {
                "id": "run-1",
                "started_at": "2026-06-11T17:00:00+00:00",
                "finished_at": "2026-06-11T17:02:00+00:00",
                "status": "completed",
                "jobs_found": 8,
                "tailor_count": 2,
                "borderline_count": 1,
                "apply_direct_count": 1,
                "skip_count": 4,
            }
        ]
        chain = _mock_supabase_chain(return_data=rpc_rows)
        mock_get_supabase.return_value.rpc.return_value = chain

        result = list_runs(limit=10)

        self.assertEqual(result, rpc_rows)
        mock_get_supabase.return_value.rpc.assert_called_once_with(
            "runs_with_counts", {"limit_n": 10}
        )

    @patch("agents.database._get_supabase")
    def test_list_runs_swallows_rpc_missing(self, mock_get_supabase):
        """When the RPC is not installed, returns [] (not 500)."""
        from agents.database import list_runs

        mock_get_supabase.return_value.rpc.side_effect = Exception("rpc not found")
        self.assertEqual(list_runs(limit=10), [])


class TestGetRun(unittest.TestCase):
    @patch("agents.database._get_supabase")
    def test_get_run_returns_row(self, mock_get_supabase):
        from agents.database import get_run

        chain = _mock_supabase_chain(return_data=[{"id": "r1", "status": "completed"}])
        mock_get_supabase.return_value.table.return_value = chain
        self.assertEqual(get_run("r1"), {"id": "r1", "status": "completed"})

    @patch("agents.database._get_supabase")
    def test_get_run_returns_none_when_empty(self, mock_get_supabase):
        from agents.database import get_run

        chain = _mock_supabase_chain(return_data=[])
        mock_get_supabase.return_value.table.return_value = chain
        self.assertIsNone(get_run("missing"))


# ─────────────────────────────────────────────────────────────────
# 2.  get_pipeline_config / set_pipeline_config (ADR-0024)
# ─────────────────────────────────────────────────────────────────
class TestGetPipelineConfig(unittest.TestCase):
    @patch("agents.database._get_supabase")
    def test_returns_defaults_when_missing(self, mock_get_supabase):
        """If nobody seeded migration 025, the helper still returns sane defaults."""
        from agents.database import get_pipeline_config

        chain = _mock_supabase_chain(return_data=[])
        mock_get_supabase.return_value.table.return_value = chain

        cfg = get_pipeline_config()
        self.assertEqual(cfg["scrape_mode"], "auto")
        self.assertEqual(cfg["evaluate_mode"], "auto")
        self.assertEqual(cfg["tailor_mode"], "manual")
        self.assertEqual(cfg["auto_send_threshold"], 0)

    @patch("agents.database._get_supabase")
    def test_returns_seeded_values(self, mock_get_supabase):
        from agents.database import get_pipeline_config

        chain = _mock_supabase_chain(return_data=[
            {"key": "pipeline_scrape_mode",   "value": "manual"},
            {"key": "pipeline_evaluate_mode", "value": "auto"},
            {"key": "pipeline_tailor_mode",   "value": "auto"},
            {"key": "auto_send_threshold",    "value": "3"},
        ])
        mock_get_supabase.return_value.table.return_value = chain

        cfg = get_pipeline_config()
        self.assertEqual(cfg["scrape_mode"], "manual")
        self.assertEqual(cfg["evaluate_mode"], "auto")
        self.assertEqual(cfg["tailor_mode"], "auto")
        self.assertEqual(cfg["auto_send_threshold"], 3)


class TestSetPipelineConfig(unittest.TestCase):
    @patch("agents.database.get_pipeline_config")
    @patch("agents.database.set_system_config")
    def test_writes_each_provided_key(self, mock_set, mock_get):
        from agents.database import set_pipeline_config

        mock_get.return_value = {
            "scrape_mode": "manual", "evaluate_mode": "auto",
            "tailor_mode": "manual", "auto_send_threshold": 2,
        }
        result = set_pipeline_config({
            "scrape_mode": "manual",
            "auto_send_threshold": 2,
        })

        # Both keys hit set_system_config exactly once.
        self.assertEqual(mock_set.call_count, 2)
        mock_set.assert_any_call("pipeline_scrape_mode", "manual")
        mock_set.assert_any_call("auto_send_threshold", "2")
        self.assertEqual(result["scrape_mode"], "manual")
        self.assertEqual(result["auto_send_threshold"], 2)

    @patch("agents.database.set_system_config")
    def test_rejects_unknown_short_key(self, _mock_set):
        from agents.database import set_pipeline_config

        with self.assertRaises(ValueError) as ctx:
            set_pipeline_config({"wat_mode": "auto"})
        self.assertIn("Unknown pipeline config key", str(ctx.exception))

    @patch("agents.database.set_system_config")
    def test_rejects_invalid_mode_value(self, _mock_set):
        from agents.database import set_pipeline_config

        with self.assertRaises(ValueError) as ctx:
            set_pipeline_config({"scrape_mode": "turbo"})
        self.assertIn("Invalid mode", str(ctx.exception))

    @patch("agents.database.set_system_config")
    def test_rejects_threshold_out_of_range(self, _mock_set):
        from agents.database import set_pipeline_config

        with self.assertRaises(ValueError) as ctx:
            set_pipeline_config({"auto_send_threshold": 9})
        self.assertIn("0..4", str(ctx.exception))


# ─────────────────────────────────────────────────────────────────
# 3.  compute_ghost_commentary
# ─────────────────────────────────────────────────────────────────
class TestGhostCommentary(unittest.TestCase):
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
# 4.  record_change_feedback + regeneration cap (R8 mitigation)
# ─────────────────────────────────────────────────────────────────
class TestRecordChangeFeedback(unittest.TestCase):
    @patch("agents.database._get_supabase")
    def test_records_feedback_and_bumps_counter(self, mock_get_supabase):
        from agents.database import record_change_feedback

        # First call (select current count) returns 1; second call (update) returns new row.
        select_chain = _mock_supabase_chain(return_data=[{"regeneration_count": 1}])
        update_chain = _mock_supabase_chain(return_data=[{
            "id": "c1", "review_action": "reject",
            "feedback_type": "too_formal", "regeneration_count": 2,
        }])
        # Each call to .table() returns a fresh chain.
        mock_get_supabase.return_value.table.side_effect = [select_chain, update_chain]

        row = record_change_feedback("c1", "too_formal")
        self.assertEqual(row["regeneration_count"], 2)
        self.assertEqual(row["feedback_type"], "too_formal")

    @patch("agents.database._get_supabase")
    def test_raises_when_cap_reached(self, mock_get_supabase):
        from agents.database import RegenerationCapReached, record_change_feedback

        select_chain = _mock_supabase_chain(return_data=[{"regeneration_count": 2}])
        mock_get_supabase.return_value.table.return_value = select_chain

        with self.assertRaises(RegenerationCapReached):
            record_change_feedback("c1", "other")

    def test_rejects_invalid_feedback_type(self):
        from agents.database import record_change_feedback

        with self.assertRaises(ValueError):
            record_change_feedback("c1", "bogus")


if __name__ == "__main__":
    unittest.main()
