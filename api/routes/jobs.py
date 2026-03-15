"""
Jobs routes - Read jobs directly from App DB (Supabase).
"""
import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from agents.supabase_client import get_supabase_client
from services.scraper_service import ScraperService
from api.schemas import JobBase, JobDetail, JobStats, DeleteRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=list[JobBase])
def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=10000),
    company: str | None = Query(None, description="Filter by company name"),
    is_evaluated: bool | None = Query(None, description="Filter by evaluation status"),
):
    """List jobs from App DB (paginated)."""
    client = get_supabase_client()

    # Use enriched view for is_evaluated computed column (single query, no ID storm)
    query = client.table("v_jobs_enriched").select("*").eq("status", "active")

    # Apply filters
    if company:
        query = query.ilike("company_name", f"%{company}%")

    if is_evaluated is not None:
        query = query.eq("is_evaluated", is_evaluated)
    
    # Pagination
    # Supabase range is inclusive
    end = skip + limit - 1
    
    logger.debug(f"Listing jobs skip={skip} limit={limit} company={company} is_evaluated={is_evaluated}")
    
    try:
        result = query.order("posted_at", desc=True).range(skip, end).execute()
        
        if not result.data:
            return []
            
        return result.data 
    except Exception as e:
        logger.error("Failed to list jobs", exc_info=True)
        raise HTTPException(status_code=500, detail="Database query failed")


@router.get("/stats", response_model=JobStats)
def get_job_stats(
    company: str | None = Query(None, description="Filter by company"),
    is_evaluated: bool | None = Query(None, description="Filter by evaluation status"),
):
    """Get aggregate job statistics."""
    client = get_supabase_client()
    
    # Use enriched view for is_evaluated computed column (single query, no ID storm)
    query = client.table("v_jobs_enriched").select("*", count="exact", head=True).eq("status", "active")

    if company:
        query = query.ilike("company_name", f"%{company}%")

    if is_evaluated is not None:
        query = query.eq("is_evaluated", is_evaluated)
    
    # Execute count
    try:
        total = query.execute().count or 0
        return {
            "total_jobs": total,
            "unique_companies": 0, # Placeholder until we add RPC or View
            "top_companies": []
        }
    except Exception as e:
        logger.error("Failed to get job stats", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch stats")


@router.get("/{job_id}", response_model=JobDetail)
def get_job(job_id: str):
    """Get single job details."""
    client = get_supabase_client()
    
    result = client.table("jobs").select("*").eq("id", job_id).execute()
    
    if not result.data:
        logger.warning(f"Job {job_id} not found")
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    return result.data[0]


@router.delete("", status_code=204)
def delete_jobs(request: DeleteRequest):
    """Bulk soft-delete jobs."""
    client = get_supabase_client()
    
    # Update status to 'deleted' for all IDs
    # Supabase 'in_' filter works for lists
    logger.info(f"Deleting {len(request.ids)} jobs")
    try:
        (
            client.table("jobs")
            .update({"status": "deleted"})
            .in_("id", request.ids)
            .execute()
        )
    except Exception as e:
        logger.error("Failed to delete jobs", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete jobs: {e}")
    
    return


class ImportRequest(BaseModel):
    url: str

@router.post("/import", status_code=201)
def import_job(request: ImportRequest):
    """Import a job from a LinkedIn URL via Apify."""
    logger.info(f"Importing job from URL: {request.url}")
    try:
        result = ScraperService.scrape_and_import(request.url)
        logger.info(f"Import successful. ID: {result.get('id')}")
        return result
    except Exception as e:
        logger.error(f"Import failed for {request.url}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
