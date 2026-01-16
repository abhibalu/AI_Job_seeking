"""
Jobs routes - Read jobs directly from App DB (Supabase).
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from agents.supabase_client import get_supabase_client
from backend.settings import settings
from services.scraper_service import ScraperService
from api.schemas import JobBase, JobDetail, JobStats, DeleteRequest

router = APIRouter()


@router.get("", response_model=list[JobBase])
def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=10000),
    company: str | None = Query(None, description="Filter by company name"),
    is_evaluated: bool | None = Query(None, description="Filter by evaluation status"),
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

    if is_evaluated is not None:
        # Get all evaluated IDs (optimized: only select ID)
        # Note: If evaluated set is huge, this might need 
        # a better approach (e.g. view or RPC), but fine for <10k.
        eval_result = client.table("job_evaluations").select("job_id").execute()
        evaluated_ids = [r['job_id'] for r in eval_result.data]

        if is_evaluated:
            if not evaluated_ids:
                return [] # No evaluated jobs
            query = query.in_("id", evaluated_ids)
        else:
            if evaluated_ids:
                query = query.not_.in_("id", evaluated_ids)
    
    # Pagination
    # Supabase range is inclusive
    end = skip + limit - 1
    result = query.order("posted_at", desc=True).range(skip, end).execute()
    
    if not result.data:
        return []
        
    return result.data 


@router.get("/stats", response_model=JobStats)
def get_job_stats(
    company: str | None = Query(None, description="Filter by company"),
    is_evaluated: bool | None = Query(None, description="Filter by evaluation status"),
):
    """Get aggregate job statistics."""
    if not settings.USE_SUPABASE:
        raise HTTPException(status_code=503, detail="Supabase backend not enabled")
        
    client = get_supabase_client()
    
    # Base query
    query = client.table("jobs").select("*", count="exact", head=True).eq("status", "active")

    if company:
        query = query.ilike("company_name", f"%{company}%")

    if is_evaluated is not None:
        eval_result = client.table("job_evaluations").select("job_id").execute()
        evaluated_ids = [r['job_id'] for r in eval_result.data]

        if is_evaluated:
             if not evaluated_ids:
                 pass # Will resolve to 0 matches logically if we could force it, 
                      # but query builder is additive.
                      # Ideally we query .in_([], []) which returns 0.
                 query = query.in_("id", ["00000000-0000-0000-0000-000000000000"]) # Dummy
             else:
                 query = query.in_("id", evaluated_ids)
        else:
             if evaluated_ids:
                 query = query.not_.in_("id", evaluated_ids)
    
    # Execute count
    total = query.execute().count or 0
    
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

@router.delete("", status_code=204)
def delete_jobs(request: DeleteRequest):
    """Bulk soft-delete jobs."""
    if not settings.USE_SUPABASE:
        raise HTTPException(status_code=503, detail="Supabase backend not enabled")

    client = get_supabase_client()
    
    # Update status to 'deleted' for all IDs
    # Supabase 'in_' filter works for lists
    try:
        (
            client.table("jobs")
            .update({"status": "deleted"})
            .in_("id", request.ids)
            .execute()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete jobs: {e}")
    
    return

class ImportRequest(BaseModel):
    url: str

@router.post("/import", status_code=201)
def import_job(request: ImportRequest):
    """Import a job from a LinkedIn URL via Apify."""
    try:
        result = ScraperService.scrape_and_import(request.url)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
