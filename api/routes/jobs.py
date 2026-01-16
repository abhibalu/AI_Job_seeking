"""
Jobs routes - Read jobs directly from App DB (Supabase).
"""
from fastapi import APIRouter, HTTPException, Query

from agents.supabase_client import get_supabase_client
from backend.settings import settings
from api.schemas import JobBase, JobDetail, JobStats

router = APIRouter()


@router.get("", response_model=list[JobBase])
def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    company: str | None = Query(None, description="Filter by company name"),
):
    """List jobs from App DB (paginated)."""
    if not settings.USE_SUPABASE:
        raise HTTPException(status_code=503, detail="Supabase backend not enabled")

    client = get_supabase_client()
    
    # Base query: Active jobs only
    query = client.table("jobs").select("*").eq("status", "active")
    
    # Apply filters
    if company:
        query = query.ilike("company_name", f"%{company}%")
    
    # Pagination
    # Supabase range is inclusive
    end = skip + limit - 1
    result = query.order("posted_at", desc=True).range(skip, end).execute()
    
    if not result.data:
        return []
        
    return result.data 


@router.get("/stats", response_model=JobStats)
def get_job_stats():
    """Get aggregate job statistics."""
    if not settings.USE_SUPABASE:
        raise HTTPException(status_code=503, detail="Supabase backend not enabled")
        
    client = get_supabase_client()
    
    # Total active jobs
    # HEAD request for count is efficient
    total = client.table("jobs").select("*", count="exact", head=True).eq("status", "active").execute().count or 0
    
    # Top companies (Aggregation requires View or RPC in generic PostgREST usually, 
    # but we can fetch company_names and aggregate in python if dataset is small, 
    # OR better: Assume user creates a view later. 
    # For now: Fetch company names of active jobs (limit to 1000 for perfs?)
    # or just simple return 0 if complicated.
    # Let's try fetching companies.)
    
    # Simplified stats for now to avoid heavy queries without RPC
    return {
        "total_jobs": total,
        "unique_companies": 0, # Placeholder until we add RPC or View
        "top_companies": []
    }


@router.get("/{job_id}", response_model=JobDetail)
def get_job(job_id: str):
    """Get single job details."""
    if not settings.USE_SUPABASE:
        raise HTTPException(status_code=503, detail="Supabase backend not enabled")
        
    client = get_supabase_client()
    
    result = client.table("jobs").select("*").eq("id", job_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    return result.data[0]
