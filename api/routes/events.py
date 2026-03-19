"""
SSE event stream — server → client push for task progress and run completion.
Single endpoint replaces all polling. ADR-0009.
"""
import asyncio
import json
import logging

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from agents.database import get_task_status

logger = logging.getLogger(__name__)
router = APIRouter()

POLL_INTERVAL = 1.0   # seconds between DB checks
KEEPALIVE_EVERY = 15  # send a comment ping every N seconds to prevent proxy timeout


@router.get("/stream")
async def event_stream(task_id: str = Query(..., description="Task ID to track")):
    """
    SSE stream for a single task. Emits:
      - event: progress   — while task is queued / running
      - event: run_complete — when task reaches completed or failed (then closes)

    Clients connect via EventSource; auto-reconnect is handled by the browser.
    """
    async def generate():
        ticks_since_keepalive = 0

        while True:
            # Keepalive comment to prevent idle proxy timeout
            if ticks_since_keepalive >= KEEPALIVE_EVERY:
                yield ": keepalive\n\n"
                ticks_since_keepalive = 0

            task = get_task_status(task_id)

            if task is None:
                # Not written yet — worker may still be starting
                ticks_since_keepalive += 1
                await asyncio.sleep(POLL_INTERVAL)
                continue

            status = task.get("status", "queued")
            progress = task.get("progress") or {}
            error = task.get("error")

            if status in ("queued", "running"):
                payload = json.dumps({
                    "task_id": task_id,
                    "status": status,
                    "progress": progress,
                })
                yield f"event: progress\ndata: {payload}\n\n"
                ticks_since_keepalive += 1
                await asyncio.sleep(POLL_INTERVAL)

            elif status == "completed":
                payload = json.dumps({
                    "task_id": task_id,
                    "status": "completed",
                    "progress": progress,
                })
                yield f"event: run_complete\ndata: {payload}\n\n"
                return

            elif status == "cancelled":
                payload = json.dumps({
                    "task_id": task_id,
                    "status": "cancelled",
                })
                yield f"event: run_complete\ndata: {payload}\n\n"
                return

            elif status == "failed":
                payload = json.dumps({
                    "task_id": task_id,
                    "status": "failed",
                    "error": error,
                })
                yield f"event: run_complete\ndata: {payload}\n\n"
                return

            else:
                ticks_since_keepalive += 1
                await asyncio.sleep(POLL_INTERVAL)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )
