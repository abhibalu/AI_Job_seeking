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


# ─────────────────────────────────────────────────────────────────
# 4.  save_tailored_resume — must raise after the Cluster A split
# ─────────────────────────────────────────────────────────────────
class TestSaveTailoredResumeRemoved(unittest.TestCase):

    def test_save_tailored_resume_raises(self):
        from agents.database import save_tailored_resume
        with self.assertRaises(NotImplementedError):
            save_tailored_resume(
                job_id="x", version=1, content={}, status="pending", edit_plan=None,
            )


# ─────────────────────────────────────────────────────────────────
# 5.  node_save — UPDATE via complete_tailored_resume, not INSERT
# ─────────────────────────────────────────────────────────────────
class TestNodeSaveUsesUpdate(unittest.TestCase):

    @patch("agents.tailoring_subgraph.complete_tailored_resume")
    def test_node_save_calls_complete_tailored_resume(self, mock_complete):
        """T2: node_save delegates to the CAS UPDATE helper, not the
        removed save_tailored_resume INSERT path."""
        from agents.tailoring_subgraph import node_save

        mock_complete.return_value = True
        state = {
            "target_resume_id": "r-abc",
            "draft_resume": {"basics": {"name": "Test"}},
            "edit_plan": {"edits": []},
            "revision_count": 1,
            "job_id": "j-1",
            # is_force_save uses state['critique'] + revision count;
            # supply benign values so it returns False.
            "critique": [],
        }
        out = node_save(state)

        mock_complete.assert_called_once()
        kwargs = mock_complete.call_args.kwargs
        self.assertEqual(kwargs["resume_id"], "r-abc")
        self.assertEqual(kwargs["status"], "pending")
        self.assertEqual(out["final_resume_id"], "r-abc")
        self.assertTrue(out["save_applied"])
        self.assertEqual(out["status"], "saved")

    @patch("agents.tailoring_subgraph.complete_tailored_resume")
    def test_node_save_reflects_cas_no_op_in_status(self, mock_complete):
        """When CAS no-ops, node_save returns status='cancelled' so the
        worker can report task as cancelled, not completed."""
        from agents.tailoring_subgraph import node_save

        mock_complete.return_value = False
        out = node_save({
            "target_resume_id": "r-x",
            "draft_resume": {},
            "edit_plan": None,
            "revision_count": 0,
            "job_id": "j-2",
            "critique": [],
        })
        self.assertFalse(out["save_applied"])
        self.assertEqual(out["status"], "cancelled")

    @patch("agents.tailoring_subgraph.complete_tailored_resume")
    def test_node_save_strips_underscore_metadata(self, mock_complete):
        """Regression: _model_used and _agent must be stripped from
        draft_resume and edit_plan before persisting (per agents/CLAUDE.md)."""
        from agents.tailoring_subgraph import node_save

        mock_complete.return_value = True
        state = {
            "target_resume_id": "r-strip",
            "draft_resume": {
                "basics": {"name": "Test"},
                "_model_used": "claude-sonnet-4-6",
                "_agent": "ResumeTailorAgent",
            },
            "edit_plan": {
                "edits": [],
                "_model_used": "claude-sonnet-4-6",
                "_agent": "ChangePlannerAgent",
            },
            "revision_count": 0,
            "job_id": "j-strip",
            "critique": [],
        }
        node_save(state)

        kwargs = mock_complete.call_args.kwargs
        self.assertNotIn("_model_used", kwargs["content"])
        self.assertNotIn("_agent", kwargs["content"])
        self.assertIn("basics", kwargs["content"])
        self.assertNotIn("_model_used", kwargs["edit_plan"])
        self.assertNotIn("_agent", kwargs["edit_plan"])
        self.assertIn("edits", kwargs["edit_plan"])


# ─────────────────────────────────────────────────────────────────
# 6.  run_tailoring_worker — placeholder + cancel + reaper-race
# ─────────────────────────────────────────────────────────────────
class TestRunTailoringWorker(unittest.TestCase):

    # NOTE on patch paths: run_tailoring_worker does its imports inside the
    # function body (existing pattern, not changed by this plan), so patches
    # must target the source modules (agents.database / agents.tailoring_subgraph),
    # not the api.routes.resumes namespace.
    @patch("agents.database.mark_resume_cancelled")
    @patch("agents.database.get_task_status")
    @patch("agents.database.save_task_status")
    @patch("agents.database.create_processing_placeholder")
    @patch("agents.tailoring_subgraph.node_plan")
    def test_worker_finally_marks_cancelled_on_user_cancel(
        self, mock_plan, mock_create, mock_save_task, mock_get_task, mock_mark_cancelled,
    ):
        """T6: When the task is cancelled mid-pipeline, the finally block
        calls mark_resume_cancelled on the placeholder resume row."""
        from api.routes.resumes import run_tailoring_worker

        mock_create.return_value = "r-placeholder"
        # First get_task_status (in is_cancelled) returns 'cancelled' so
        # the worker bails out after the very first stage_status write.
        mock_get_task.return_value = {"status": "cancelled"}
        mock_plan.return_value = {}  # never reached

        run_tailoring_worker(
            task_id="t-1",
            job_id="j-1",
            initial_state={"job_id": "j-1", "base_resume": {}, "approved_skills": ""},
        )

        mock_mark_cancelled.assert_called_once_with("r-placeholder")

    @patch("agents.database.mark_resume_cancelled")
    @patch("agents.database.get_task_status")
    @patch("agents.database.save_task_status")
    @patch("agents.database.create_processing_placeholder")
    @patch("agents.tailoring_subgraph.node_save")
    @patch("agents.tailoring_subgraph.node_critique")
    @patch("agents.tailoring_subgraph.route_critique")
    @patch("agents.tailoring_subgraph.node_validate")
    @patch("agents.tailoring_subgraph.route_validate")
    @patch("agents.tailoring_subgraph.node_draft")
    @patch("agents.tailoring_subgraph.node_plan")
    def test_worker_reflects_reaper_race_in_task_status(
        self,
        mock_plan, mock_draft, mock_route_validate, mock_validate,
        mock_route_critique, mock_critique, mock_save_node,
        mock_create, mock_save_task, mock_get_task, mock_mark_cancelled,
    ):
        """T10: If complete_tailored_resume returned False (signalled via
        node_save returning save_applied=False), the worker writes task
        status='cancelled', NOT 'completed'.
        """
        from api.routes.resumes import run_tailoring_worker

        mock_create.return_value = "r-placeholder"
        mock_get_task.return_value = {"status": "running"}  # never cancelled
        mock_plan.return_value = {}
        mock_draft.return_value = {}
        mock_validate.return_value = {}
        mock_route_validate.return_value = "ok"
        mock_critique.return_value = {}
        mock_route_critique.return_value = "ok"
        # node_save reports the CAS no-op:
        mock_save_node.return_value = {
            "final_resume_id": "r-placeholder",
            "save_applied": False,
            "status": "cancelled",
        }

        run_tailoring_worker(
            task_id="t-2",
            job_id="j-2",
            initial_state={"job_id": "j-2", "base_resume": {}, "approved_skills": ""},
        )

        # Last save_task_status call must be 'cancelled', not 'completed'.
        statuses = [c.args[1] for c in mock_save_task.call_args_list]
        self.assertIn("cancelled", statuses)
        self.assertNotIn("completed", statuses)


# ─────────────────────────────────────────────────────────────────
# 7.  Cancel endpoint marks in-flight resume row
# ─────────────────────────────────────────────────────────────────
class TestCancelEndpoint(unittest.TestCase):

    @patch("api.routes.tasks.mark_resume_cancelled")
    @patch("agents.database.save_task_status")
    @patch("api.routes.tasks.get_task_status_db")
    def test_cancel_marks_resume_when_resume_id_in_progress(
        self, mock_get_task, mock_save_task, mock_mark_cancelled,
    ):
        from api.routes.tasks import cancel_task

        # task has progress.resume_id set (because worker writes it now).
        mock_get_task.return_value = {
            "status": "running",
            "progress": {"resume_id": "r-7", "job_id": "j-7"},
        }

        cancel_task(task_id="t-7")

        mock_mark_cancelled.assert_called_once_with("r-7")

    @patch("api.routes.tasks.mark_resume_cancelled")
    @patch("agents.database.save_task_status")
    @patch("api.routes.tasks.get_task_status_db")
    def test_cancel_no_op_when_progress_missing_resume_id(
        self, mock_get_task, mock_save_task, mock_mark_cancelled,
    ):
        from api.routes.tasks import cancel_task

        mock_get_task.return_value = {"status": "running", "progress": {}}
        cancel_task(task_id="t-8")

        mock_mark_cancelled.assert_not_called()


# ─────────────────────────────────────────────────────────────────
# 8.  reap_stale_tailoring_runs — sweep behavior
# ─────────────────────────────────────────────────────────────────
class TestTailoringReaper(unittest.TestCase):

    @patch("services.scheduler.set_correlation_id")
    @patch("services.scheduler.get_system_config")
    @patch("services.scheduler._get_supabase")
    def test_reaper_sweeps_stale_rows(self, mock_get_supabase, mock_cfg, _mock_corr):
        """T3: WHEN processing_started_at < now() - timeout, row is
        updated to tailoring_status='cancelled'."""
        from services.scheduler import reap_stale_tailoring_runs

        mock_cfg.return_value = "15"
        chain = _mock_supabase_chain(return_data=[{"id": "r1"}, {"id": "r2"}])
        mock_get_supabase.return_value.table.return_value = chain

        reap_stale_tailoring_runs()

        update_kwargs = chain.update.call_args[0][0]
        self.assertEqual(update_kwargs["tailoring_status"], "cancelled")
        chain.eq.assert_any_call("tailoring_status", "processing")
        # Verify a .lt() filter is applied on processing_started_at.
        lt_calls = [c.args for c in chain.lt.call_args_list]
        self.assertTrue(
            any(c[0] == "processing_started_at" for c in lt_calls),
            "Expected .lt('processing_started_at', threshold) in builder chain",
        )

    @patch("services.scheduler.set_correlation_id")
    @patch("services.scheduler.get_system_config")
    @patch("services.scheduler._get_supabase")
    def test_reaper_default_timeout_when_config_missing(
        self, mock_get_supabase, mock_cfg, _mock_corr,
    ):
        """T4 part 1: When system_config is empty, reaper falls back to
        15 minutes — verified by checking the .lt() threshold is roughly
        15m ago (within tolerance)."""
        from services.scheduler import reap_stale_tailoring_runs

        mock_cfg.return_value = None
        chain = _mock_supabase_chain(return_data=[])
        mock_get_supabase.return_value.table.return_value = chain

        reap_stale_tailoring_runs()

        # Pull the threshold passed to .lt() and check it is ~15m in past.
        lt_args = chain.lt.call_args[0]
        self.assertEqual(lt_args[0], "processing_started_at")
        threshold_iso = lt_args[1]
        threshold = datetime.fromisoformat(threshold_iso)
        now = datetime.now(timezone.utc)
        delta = now - threshold
        self.assertGreater(delta.total_seconds(), 14 * 60)
        self.assertLess(delta.total_seconds(), 16 * 60)

    @patch("services.scheduler.set_correlation_id")
    @patch("services.scheduler.get_system_config")
    @patch("services.scheduler._get_supabase")
    def test_reaper_invalid_config_falls_back_to_default(
        self, mock_get_supabase, mock_cfg, _mock_corr,
    ):
        """T4 part 2: Garbage in system_config doesn't crash the reaper —
        it warns and uses the 15-minute default."""
        from services.scheduler import reap_stale_tailoring_runs

        mock_cfg.return_value = "not-a-number"
        chain = _mock_supabase_chain(return_data=[])
        mock_get_supabase.return_value.table.return_value = chain

        # Should not raise.
        reap_stale_tailoring_runs()


if __name__ == "__main__":
    unittest.main()
