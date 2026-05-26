"""
Tasks routes - Track async task status.
"""
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException

from agents.database import (
    list_tasks as list_tasks_db,
    get_task_status as get_task_status_db,
    mark_resume_cancelled,
)
from api.schemas import TaskStatus

router = APIRouter()


@router.get("", response_model=list[TaskStatus])
def list_tasks(limit: int = 20):
    """List recent tasks."""
    rows = list_tasks_db(limit)
    
    results = []
    for row_dict in rows:
        if row_dict.get("progress") and isinstance(row_dict["progress"], str):
            try:
                row_dict["progress"] = json.loads(row_dict["progress"])
            except:
                pass
        results.append(row_dict)
    
    return results


@router.get("/{task_id}", response_model=TaskStatus)
def get_task_status(task_id: str):
    """Get status of a specific task."""
    result = get_task_status_db(task_id)

    if not result:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if result.get("progress") and isinstance(result["progress"], str):
        try:
            result["progress"] = json.loads(result["progress"])
        except:
            pass

    return result


@router.post("/{task_id}/cancel")
def cancel_task(task_id: str):
    """Cancel a running task. Worker checks status at node boundaries."""
    from agents.database import save_task_status

    task = get_task_status_db(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if task.get("status") in ("completed", "failed", "cancelled"):
        return {"status": task["status"], "message": "Task already terminated"}

    save_task_status(task_id, "cancelled", task.get("progress"))

    # Phase 1 Cluster A: also mark the in-flight resume row so UI flips
    # immediately without waiting for the worker's next boundary check.
    progress = task.get("progress") or {}
    resume_id = progress.get("resume_id")
    if resume_id:
        mark_resume_cancelled(resume_id)  # CAS — no-op if already terminal

    return {"status": "cancelled"}
