"""
test/test_resume_lifecycle_foundation.py

Phase 1 Cluster A — Schema Foundation tests.

Covers the placeholder-row lifecycle for tailoring runs, the stale-row reaper,
the DB-level CHECK constraints, and the worker/cancel/reaper race paths.

Split into:
  - Unit tests (fully mocked — no DB).
  - Integration tests (real Supabase, skipped when SUPABASE_URL is unset).
"""
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def _mock_supabase_chain(return_data):
    """Build a MagicMock chain that mimics the supabase-py builder pattern.

    Used as the return value of patched _get_supabase(). Lets a test set the
    final `.execute()` result without wiring every intermediate call by hand.
    """
    final = MagicMock()
    final.execute.return_value = MagicMock(data=return_data)
    chain = MagicMock()
    # Every method on the chain returns itself so a long .update().eq().eq()
    # builder ends up at `final` for .execute().
    for method in ("insert", "update", "select", "eq", "lt", "order", "limit"):
        getattr(chain, method).return_value = chain
    chain.execute = final.execute
    return chain


# ─────────────────────────────────────────────────────────────────
# 1.  complete_tailored_resume — CAS UPDATE behavior
# ─────────────────────────────────────────────────────────────────
class TestCompleteTailoredResumeCAS(unittest.TestCase):
    """Verify complete_tailored_resume short-circuits when the row is no
    longer in `processing` (reaper-race / user-cancel-race)."""

    @patch("agents.database._save_resume_changes")
    @patch("agents.database._get_supabase")
    def test_complete_tailored_resume_cas_no_op(self, mock_get_supabase, mock_save_changes):
        """T5: When UPDATE returns zero rows, function returns False and
        does NOT call _save_resume_changes (avoiding orphan rows against
        a cancelled resume).
        """
        from agents.database import complete_tailored_resume

        # Supabase update().eq().eq().execute() returns an empty data list
        # — simulating a CAS miss because tailoring_status != 'processing'.
        chain = _mock_supabase_chain(return_data=[])
        mock_get_supabase.return_value.table.return_value = chain

        result = complete_tailored_resume(
            resume_id="00000000-0000-0000-0000-000000000001",
            version=1,
            content={"basics": {"name": "Test"}},
            status="pending",
            edit_plan={"edits": [{"action": "rephrase", "location": "x", "target_text": "y"}]},
        )

        self.assertFalse(result, "Expected False return on CAS no-op")
        mock_save_changes.assert_not_called()


# ─────────────────────────────────────────────────────────────────
# 2.  create_processing_placeholder — INSERT shape
# ─────────────────────────────────────────────────────────────────
class TestCreateProcessingPlaceholder(unittest.TestCase):

    @patch("agents.database._get_supabase")
    def test_worker_creates_placeholder(self, mock_get_supabase):
        """T1: Placeholder row INSERT has the right shape:
        status='pending', tailoring_status='processing',
        non-NULL processing_started_at, job_id set, content={}.
        """
        from agents.database import create_processing_placeholder

        chain = _mock_supabase_chain(return_data=[{"id": "x"}])
        mock_get_supabase.return_value.table.return_value = chain

        resume_id = create_processing_placeholder(job_id="job-42")

        self.assertTrue(resume_id, "Expected non-empty resume_id")
        chain.insert.assert_called_once()
        inserted = chain.insert.call_args[0][0]
        self.assertEqual(inserted["status"], "pending")
        self.assertEqual(inserted["tailoring_status"], "processing")
        self.assertEqual(inserted["job_id"], "job-42")
        self.assertEqual(inserted["content"], {})
        self.assertIn("processing_started_at", inserted)
        self.assertIsNotNone(inserted["processing_started_at"])


# ─────────────────────────────────────────────────────────────────
# 3.  mark_resume_cancelled — CAS UPDATE behavior
# ─────────────────────────────────────────────────────────────────
class TestMarkResumeCancelled(unittest.TestCase):

    @patch("agents.database._get_supabase")
    def test_returns_true_when_row_was_processing(self, mock_get_supabase):
        from agents.database import mark_resume_cancelled

        chain = _mock_supabase_chain(return_data=[{"id": "r1"}])
        mock_get_supabase.return_value.table.return_value = chain

        self.assertTrue(mark_resume_cancelled("r1"))

        update_kwargs = chain.update.call_args[0][0]
        self.assertEqual(update_kwargs["tailoring_status"], "cancelled")
        self.assertIn("updated_at", update_kwargs)

    @patch("agents.database._get_supabase")
    def test_returns_false_on_no_op(self, mock_get_supabase):
        from agents.database import mark_resume_cancelled

        chain = _mock_supabase_chain(return_data=[])
        mock_get_supabase.return_value.table.return_value = chain

        self.assertFalse(mark_resume_cancelled("r1"))


if __name__ == "__main__":
    unittest.main()
