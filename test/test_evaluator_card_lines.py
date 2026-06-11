"""test/test_evaluator_card_lines.py — Task 21.

Covers:
  - _normalize_red_flags: hyphen / en-dash / em-dash / non-strings / empties
  - save_evaluation_with_card_lines: delegates to save_evaluation, then
    issues a card-line UPDATE; skips the UPDATE when all card fields are
    absent (transition-window safety); swallows UPDATE errors.
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# ─────────────────────────────────────────────────────────────────
# 1. _normalize_red_flags
# ─────────────────────────────────────────────────────────────────
class TestNormalizeRedFlags(unittest.TestCase):
    def test_plain_hyphen_to_em_dash(self):
        from agents.evaluator_writer import _normalize_red_flags

        self.assertEqual(
            _normalize_red_flags(["Startup mentality - no processes"]),
            ["Startup mentality — no processes"],
        )

    def test_en_dash_to_em_dash(self):
        from agents.evaluator_writer import _normalize_red_flags

        self.assertEqual(
            _normalize_red_flags(["Title inflation – fake director title"]),
            ["Title inflation — fake director title"],
        )

    def test_em_dash_passthrough(self):
        from agents.evaluator_writer import _normalize_red_flags

        s = "Salary band missing — every JD without one in this region underpays."
        self.assertEqual(_normalize_red_flags([s]), [s])

    def test_drops_non_strings(self):
        from agents.evaluator_writer import _normalize_red_flags

        self.assertEqual(
            _normalize_red_flags(["good string - here", 42, None, {"x": 1}]),
            ["good string — here"],
        )

    def test_drops_empty_and_whitespace_only(self):
        from agents.evaluator_writer import _normalize_red_flags

        self.assertEqual(
            _normalize_red_flags(["", "   ", "real - flag"]),
            ["real — flag"],
        )

    def test_none_and_empty_input(self):
        from agents.evaluator_writer import _normalize_red_flags

        self.assertEqual(_normalize_red_flags(None), [])
        self.assertEqual(_normalize_red_flags([]), [])

    def test_only_dashes_with_whitespace_get_replaced(self):
        """A bare hyphen with no surrounding spaces should NOT be rewritten —
        we only catch the label/explanation separator pattern."""
        from agents.evaluator_writer import _normalize_red_flags

        # "co-located" stays — the regex needs whitespace on both sides.
        self.assertEqual(
            _normalize_red_flags(["co-located team - red flag"]),
            ["co-located team — red flag"],
        )


# ─────────────────────────────────────────────────────────────────
# 2. save_evaluation_with_card_lines
# ─────────────────────────────────────────────────────────────────
class TestSaveEvaluationWithCardLines(unittest.TestCase):
    @patch("agents.evaluator_writer._get_supabase")
    @patch("agents.evaluator_writer.save_evaluation")
    def test_delegates_then_updates_card_fields(self, mock_save, mock_get):
        from agents.evaluator_writer import save_evaluation_with_card_lines

        chain = MagicMock()
        for m in ("update", "eq"):
            getattr(chain, m).return_value = chain
        chain.execute.return_value = MagicMock(data=[{"job_id": "j1"}])
        mock_get.return_value.table.return_value = chain

        save_evaluation_with_card_lines({
            "job_id": "j1",
            "recommended_action": "tailor",
            "top_strength": "Snowflake/dbt match.",
            "red_flags": ["Salary missing - red"],
        })

        mock_save.assert_called_once()
        # The card-line UPDATE went through.
        chain.update.assert_called_once()
        update_payload = chain.update.call_args[0][0]
        self.assertEqual(update_payload["top_strength"], "Snowflake/dbt match.")
        self.assertEqual(update_payload["red_flags"], ["Salary missing — red"])
        # Other card fields are None for a TAILOR verdict.
        self.assertIsNone(update_payload["deciding_factor"])
        self.assertIsNone(update_payload["kill_shot"])
        chain.eq.assert_called_with("job_id", "j1")

    @patch("agents.evaluator_writer._get_supabase")
    @patch("agents.evaluator_writer.save_evaluation")
    def test_skips_card_update_when_all_fields_absent(self, mock_save, mock_get):
        """Transition-window safety — if the evaluator hasn't been redeployed
        yet, there's no card data to write; the second round-trip is wasted."""
        from agents.evaluator_writer import save_evaluation_with_card_lines

        save_evaluation_with_card_lines({
            "job_id": "j1",
            "recommended_action": "skip",
            # No top_strength / deciding_factor / kill_shot / red_flags.
        })

        mock_save.assert_called_once()
        # Supabase client was never even fetched for an UPDATE.
        mock_get.assert_not_called()

    @patch("agents.evaluator_writer._get_supabase")
    @patch("agents.evaluator_writer.save_evaluation")
    def test_skips_card_update_when_job_id_missing(self, mock_save, mock_get):
        """Defensive: a card-line UPDATE keyed on NULL job_id would be a
        catastrophic table-wide overwrite. Skip it and log."""
        from agents.evaluator_writer import save_evaluation_with_card_lines

        save_evaluation_with_card_lines({
            "kill_shot": "Visa required.",
            # job_id missing
        })

        mock_save.assert_called_once()
        mock_get.assert_not_called()

    @patch("agents.evaluator_writer._get_supabase")
    @patch("agents.evaluator_writer.save_evaluation")
    def test_swallows_update_failure(self, mock_save, mock_get):
        """A flaky card UPDATE must not bubble up — save_evaluation has
        already succeeded, the dashboard would otherwise show stale data."""
        from agents.evaluator_writer import save_evaluation_with_card_lines

        chain = MagicMock()
        chain.update.return_value = chain
        chain.eq.return_value = chain
        chain.execute.side_effect = Exception("network blip")
        mock_get.return_value.table.return_value = chain

        # Should NOT raise.
        save_evaluation_with_card_lines({
            "job_id": "j2",
            "kill_shot": "Visa required.",
        })
        mock_save.assert_called_once()


if __name__ == "__main__":
    unittest.main()
