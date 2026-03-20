"""
Pipeline Runs — Supabase log for background automation workers.

Inserts structured run summaries to the `pipeline_runs` table,
which powers the /api/scheduler/status endpoint and future DuckDB analytics.
"""
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from agents.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

RunType = str   # 'scrape' | 'evaluate' | 'tailor' | 'full_pipeline'
Status  = str   # 'running' | 'completed' | 'failed' | 'skipped'


def start_run(run_type: RunType, metadata: dict | None = None) -> str:
    """
    Insert a pipeline_run row with status='running' and return its UUID.
    Call finish_run() when the worker completes.
    """
    run_id = str(uuid4())
    try:
        client = get_supabase_client()
        client.table("pipeline_runs").insert({
            "id": run_id,
            "run_type": run_type,
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }).execute()
    except Exception as e:
        logger.warning("[pipeline_runs] Could not log run start: %s", e, exc_info=True)
    return run_id


def finish_run(
    run_id: str,
    status: Status,
    jobs_found: int | None = None,
    jobs_processed: int | None = None,
    jobs_skipped: int | None = None,
    error_detail: str | None = None,
    metadata: dict | None = None,
) -> None:
    """Update an existing pipeline_run row to its final state."""
    try:
        client = get_supabase_client()
        payload: dict[str, Any] = {
            "status": status,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
        if jobs_found is not None:
            payload["jobs_found"] = jobs_found
        if jobs_processed is not None:
            payload["jobs_processed"] = jobs_processed
        if jobs_skipped is not None:
            payload["jobs_skipped"] = jobs_skipped
        if error_detail:
            payload["error_detail"] = error_detail[:2000]   # cap for DB
        if metadata:
            payload["metadata"] = metadata

        client.table("pipeline_runs").update(payload).eq("id", run_id).execute()
    except Exception as e:
        logger.warning("[pipeline_runs] Could not log run finish: %s", e, exc_info=True)


def get_recent_runs(limit: int = 20) -> list[dict]:
    """Fetch the most recent pipeline runs (for /api/scheduler/status)."""
    try:
        client = get_supabase_client()
        result = (
            client.table("pipeline_runs")
            .select("*")
            .order("started_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.exception("[pipeline_runs] Failed to fetch recent runs")
        return []


def get_last_run(run_type: RunType) -> dict | None:
    """Fetch the most recent run of a specific type."""
    try:
        client = get_supabase_client()
        result = (
            client.table("pipeline_runs")
            .select("*")
            .eq("run_type", run_type)
            .order("started_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception as e:
        logger.exception("[pipeline_runs] Failed to fetch last %s run", run_type)
        return None
