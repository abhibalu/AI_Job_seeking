"""test/test_scrape_run_id.py — Task 19.

ScrapeWorker → ScraperService.scrape_and_import must thread run_id into
every upserted job row so the OotoCV feed can group jobs under their
producing pipeline_runs entry (ADR-0025).

Apify HTTP calls are bypassed via the existing 'mock' URL shortcut in
ScraperService._run_apify_sync. The Supabase client is mocked so we can
assert the upsert payload contains run_id.
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestScraperServiceStampsRunId(unittest.TestCase):
    @patch("backend.service_guard.require_service", lambda _n: None)
    @patch("services.scraper_service.get_supabase_client")
    def test_run_id_present_when_provided(self, mock_get_client):
        from services.scraper_service import ScraperService

        # The 'mock' shortcut in _run_apify_sync returns a fixed single-job
        # payload, bypassing the real HTTP call. See services/scraper_service.py.
        upsert_calls = []
        chain = MagicMock()
        def _capture_upsert(payload, on_conflict=None):
            upsert_calls.append(payload)
            return chain
        chain.upsert.side_effect = _capture_upsert
        chain.execute.return_value = MagicMock(data=[{"id": "1234567890"}])
        client = MagicMock()
        client.table.return_value = chain
        mock_get_client.return_value = client

        result = ScraperService.scrape_and_import(
            "https://linkedin.com/mock", run_id="run-abc-123"
        )

        self.assertEqual(result["count"], 1)
        self.assertEqual(len(upsert_calls), 1)
        self.assertEqual(upsert_calls[0]["run_id"], "run-abc-123")
        # Sanity: regular job fields still present.
        self.assertEqual(upsert_calls[0]["id"], "1234567890")
        self.assertEqual(upsert_calls[0]["company_name"], "Mock Company Inc.")

    @patch("backend.service_guard.require_service", lambda _n: None)
    @patch("services.scraper_service.get_supabase_client")
    def test_run_id_omitted_when_not_provided(self, mock_get_client):
        """Manual single-URL imports must not invent a fake FK."""
        from services.scraper_service import ScraperService

        upsert_calls = []
        chain = MagicMock()
        def _capture_upsert(payload, on_conflict=None):
            upsert_calls.append(payload)
            return chain
        chain.upsert.side_effect = _capture_upsert
        chain.execute.return_value = MagicMock(data=[{"id": "1234567890"}])
        client = MagicMock()
        client.table.return_value = chain
        mock_get_client.return_value = client

        ScraperService.scrape_and_import("https://linkedin.com/mock")
        self.assertNotIn("run_id", upsert_calls[0])

    @patch("backend.service_guard.require_service", lambda _n: None)
    @patch("services.scraper_service.get_supabase_client")
    def test_falsy_run_id_omitted(self, mock_get_client):
        """An empty/None run_id behaves the same as no run_id at all."""
        from services.scraper_service import ScraperService

        upsert_calls = []
        chain = MagicMock()
        def _capture_upsert(payload, on_conflict=None):
            upsert_calls.append(payload)
            return chain
        chain.upsert.side_effect = _capture_upsert
        chain.execute.return_value = MagicMock(data=[{"id": "1234567890"}])
        client = MagicMock()
        client.table.return_value = chain
        mock_get_client.return_value = client

        ScraperService.scrape_and_import("https://linkedin.com/mock", run_id="")
        self.assertNotIn("run_id", upsert_calls[0])


class TestScrapeWorkerThreadsRunId(unittest.TestCase):
    """End-to-end check inside run_scrape_worker — ensures the worker hands
    its start_run id to ScraperService and doesn't drop it on the floor."""

    @patch("backend.service_guard.is_service_enabled", lambda _n: True)
    @patch("services.scraper_worker.notify_scrape_complete", lambda *a, **k: None)
    @patch("services.scraper_worker.notify_scrape_failed", lambda *a, **k: None)
    @patch("services.scraper_worker.set_correlation_id", lambda *a, **k: None)
    @patch("services.scraper_worker._get_existing_ids", lambda: set())
    @patch("services.scraper_worker._get_search_urls", lambda: ["https://linkedin.com/mock"])
    @patch("services.scraper_worker.finish_run")
    @patch("services.scraper_worker.start_run")
    @patch("services.scraper_worker.ScraperService.scrape_and_import")
    def test_worker_passes_run_id_to_service(
        self, mock_scrape, mock_start_run, mock_finish_run,
    ):
        from services.scraper_worker import run_scrape_worker

        mock_start_run.return_value = "run-xyz-456"
        mock_scrape.return_value = {"count": 1, "ids": ["1234567890"], "first_job": None}

        run_scrape_worker()

        mock_scrape.assert_called_once_with(
            "https://linkedin.com/mock", run_id="run-xyz-456"
        )
        # And finish_run still wraps it.
        mock_finish_run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
