"""Shared helpers for API contract tests (OotoCV Phase 3).

Tests using `fastapi.testclient.TestClient` against `api.main:app` trigger the
`on_event("startup")` handler, which calls `init_database()`, `start_scheduler()`,
and `setup_logging()`. None of those should run offline. The `LangfuseMiddleware`
also POSTs to the Langfuse host on every request. This module patches all four
in one call so each test file doesn't repeat the wiring.
"""
import os
import sys
from unittest.mock import MagicMock, patch

# Ensure the project root is importable regardless of how pytest is invoked.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def neutralize_app_side_effects(testcase):
    """Activate startup + Langfuse patches for the lifetime of `testcase`.

    Use in `setUp()`:
        from test._api_test_utils import neutralize_app_side_effects
        class TestFoo(unittest.TestCase):
            def setUp(self):
                neutralize_app_side_effects(self)
                from fastapi.testclient import TestClient
                from api.main import app
                self.client = TestClient(app)
    """
    patches = [
        patch("agents.database.init_database", lambda: None),
        patch("services.scheduler.start_scheduler", lambda: None),
        patch("services.scheduler.stop_scheduler", lambda: None),
        patch("backend.logging.setup_logging", lambda: None),
        patch("api.middleware.langfuse", MagicMock()),
    ]
    for p in patches:
        p.start()
        testcase.addCleanup(p.stop)


def build_client():
    """Lazy import → TestClient. Call after `neutralize_app_side_effects()`."""
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)
