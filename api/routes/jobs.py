"""
Jobs routes - Read jobs from Gold Delta table.
"""
from fastapi import APIRouter, HTTPException, Query

import polars as pl
from deltalake import DeltaTable

from backend.settings import settings
from api.schemas import JobBase, JobDetail, JobStats

router = APIRouter()


def get_storage_options() -> dict:
    return {
        "AWS_ENDPOINT_URL": f"http://{settings.MINIO_ENDPOINT}",
        "AWS_ACCESS_KEY_ID": settings.MINIO_ACCESS_KEY,
        "AWS_SECRET_ACCESS_KEY": settings.MINIO_SECRET_KEY,
        "AWS_REGION": "us-east-1",
        "AWS_ALLOW_HTTP": "true",
    }


def load_gold_jobs() -> pl.DataFrame:
    """Load jobs from Gold Delta table."""
    storage_options = get_storage_options()
    gold_path = f"s3://{settings.DELTA_LAKEHOUSE_BUCKET}/gold/jobs"
    
    try:
        dt = DeltaTable(gold_path, storage_options=storage_options)
        return pl.from_arrow(dt.to_pyarrow_table())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load Gold table: {e}")


@router.get("", response_model=list[JobBase])
def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    company: str | None = Query(None, description="Filter by company name"),
):
    """List jobs from Gold table (paginated)."""
    df = load_gold_jobs()
    
    # Apply filters
    if company:
        df = df.filter(pl.col("company_name").str.contains(company, literal=False))
    
    # Pagination
    total = len(df)
    df = df.slice(skip, limit)
    
    # Convert to list of dicts
    jobs = []
    for row in df.iter_rows(named=True):
        jobs.append({
            "id": str(row.get("id", "")),
            "title": row.get("title"),
            "company_name": row.get("company_name"),
            "location": row.get("location"),
            "posted_at": str(row.get("posted_at")) if row.get("posted_at") else None,
            "applicants_count": row.get("applicants_count"),
        })
    
    return jobs


@router.get("/stats", response_model=JobStats)
def get_job_stats():
    """Get aggregate job statistics."""
    df = load_gold_jobs()
    
    # Top companies
    top_companies = (
        df
        .group_by("company_name")
        .len()
        .sort("len", descending=True)
        .head(10)
    )
    
    return {
        "total_jobs": len(df),
        "unique_companies": df["company_name"].n_unique(),
        "top_companies": [
            {"name": row["company_name"], "count": row["len"]}
            for row in top_companies.iter_rows(named=True)
        ],
    }


@router.get("/{job_id}", response_model=JobDetail)
def get_job(job_id: str):
    """Get single job details."""
    df = load_gold_jobs()
    job_df = df.filter(pl.col("id") == job_id)
    
    if job_df.is_empty():
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    row = job_df.row(0, named=True)
    
    return {
        "id": str(row.get("id", "")),
        "title": row.get("title"),
        "company_name": row.get("company_name"),
        "location": row.get("location"),
        "posted_at": str(row.get("posted_at")) if row.get("posted_at") else None,
        "applicants_count": row.get("applicants_count"),
        "description_text": row.get("description_text"),
        "seniority_level": row.get("seniority_level"),
        "employment_type": row.get("employment_type"),
        "link": row.get("link"),
        "company_website": row.get("company_website"),
    }
