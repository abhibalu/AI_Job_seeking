"""
Tasks routes - Track async task status.
"""
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException

from agents.database import list_tasks as list_tasks_db, get_task_status as get_task_status_db
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
