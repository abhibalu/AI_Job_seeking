"""
Tasks routes - Track async task status.
"""
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException

from agents.database import get_db_connection
from api.schemas import TaskStatus

router = APIRouter()


@router.get("", response_model=list[TaskStatus])
def list_tasks(limit: int = 20):
    """List recent tasks."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM tasks 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for row in rows:
        row_dict = dict(row)
        if row_dict.get("progress"):
            try:
                row_dict["progress"] = json.loads(row_dict["progress"])
            except:
                pass
        results.append(row_dict)
    
    return results


@router.get("/{task_id}", response_model=TaskStatus)
def get_task_status(task_id: str):
    """Get status of a specific task."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    result = dict(row)
    if result.get("progress"):
        try:
            result["progress"] = json.loads(result["progress"])
        except:
            pass
    
    return result
