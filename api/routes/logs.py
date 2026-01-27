from fastapi import APIRouter, Request
import logging
import time
from pydantic import BaseModel
from typing import Optional, Any

router = APIRouter()

logger = logging.getLogger("frontend")

class LogEntry(BaseModel):
    level: str
    context: str
    message: str
    data: Optional[Any] = None
    timestamp: Optional[str] = None

@router.post("/")
async def ingest_logs(entry: LogEntry):
    """
    Ingest logs from the frontend.
    """
    # Map frontend levels to python logging levels
    level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warn": logging.WARNING,
        "error": logging.ERROR
    }
    
    log_level = level_map.get(entry.level.lower(), logging.INFO)
    
    # Format the message to clearly indicate it's from frontend
    log_msg = f"[FRONTEND] [{entry.context}] {entry.message}"
    
    # Add data to extra if present
    extra = {"data": entry.data} if entry.data else {}
    
    # Log it using the backend logger
    logger.log(log_level, log_msg, extra=extra)
    
    return {"status": "received"}
