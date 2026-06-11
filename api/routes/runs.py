"""
Runs feed (OotoCV) — read-only.

Backs the feed's run separators ("Today · 5:00 PM") and per-run action band
("2 tailor · 1 direct · 1 borderline"). See ADR-0025.

Counts are computed by the `runs_with_counts(limit_n)` SQL function defined
in migration 021b. The helper layer (agents.database.list_runs) returns []
with a logged warning if the RPC is not installed, so the endpoint stays 200
during partial migration apply.
"""
import logging

from fastapi import APIRouter, HTTPException, Query

from agents.database import get_run, list_runs

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("")
def list_runs_endpoint(limit: int = Query(50, ge=1, le=200)):
    """Recent scrape/full_pipeline runs with per-verdict counts."""
    return list_runs(limit=limit)


@router.get("/{run_id}")
def get_run_endpoint(run_id: str):
    """Single pipeline_runs row; 404 if absent."""
    row = get_run(run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="run not found")
    return row
