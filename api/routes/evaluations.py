"""
Evaluations routes - Evaluate jobs and get results.
"""
import json
from fastapi import APIRouter, HTTPException, BackgroundTasks

import polars as pl
from deltalake import DeltaTable

from backend.settings import settings
from api.schemas import EvaluationResult, EvaluationStats, BatchRequest, MessageResponse
from agents.database import (
    get_db_connection,
    is_job_evaluated,
    save_evaluation,
    get_evaluation,
    list_evaluations as list_evaluations_db,
    get_evaluation_statistics,
)
from agents.job_evaluator import JobEvaluatorAgent

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
    storage_options = get_storage_options()
    gold_path = f"s3://{settings.DELTA_LAKEHOUSE_BUCKET}/gold/jobs"
    dt = DeltaTable(gold_path, storage_options=storage_options)
    return pl.from_arrow(dt.to_pyarrow_table())


def get_job_by_id(job_id: str) -> dict | None:
    df = load_gold_jobs()
    job_df = df.filter(pl.col("id") == job_id)
    if job_df.is_empty():
        return None
    return job_df.row(0, named=True)


@router.get("", response_model=list[EvaluationResult])
def list_evaluations(
    skip: int = 0,
    limit: int = 20,
    action: str | None = None,
):
    """List all evaluations."""
    rows = list_evaluations_db(skip, limit, action)
    
    results = []
    for row_dict in rows:
        # Parse JSON fields
        for field in ["gaps", "improvement_suggestions", "interview_tips", "jd_keywords", "matched_keywords", "missing_keywords"]:
            if row_dict.get(field) and isinstance(row_dict[field], str):
                try:
                    row_dict[field] = json.loads(row_dict[field])
                except:
                    pass
        results.append(row_dict)
    
    return results


@router.get("/stats", response_model=EvaluationStats)
def get_evaluation_stats():
    """Get evaluation statistics."""
    """Get evaluation statistics."""
    return get_evaluation_statistics()


@router.get("/{job_id}", response_model=EvaluationResult)
def get_evaluation_result(job_id: str):
    """Get evaluation result for a job."""
    evaluation = get_evaluation(job_id)
    
    if not evaluation:
        raise HTTPException(status_code=404, detail=f"Evaluation for job {job_id} not found")
    
    # Parse JSON fields
    for field in ["gaps", "improvement_suggestions", "interview_tips", "jd_keywords", "matched_keywords", "missing_keywords"]:
        if evaluation.get(field):
            try:
                evaluation[field] = json.loads(evaluation[field])
            except:
                pass
    
    return evaluation




def run_batch_evaluation(task_id: str, max_jobs: int, only_unevaluated: bool, company_filter: str | None):
    """Background task for batch evaluation."""
    from agents.database import save_task_status
    
    df = load_gold_jobs()
    
    # Apply filters
    if company_filter:
        df = df.filter(pl.col("company_name").str.contains(company_filter, literal=False))
    
    processed = 0
    for row in df.iter_rows(named=True):
        if processed >= max_jobs:
            break
        
        job_id = str(row.get("id", ""))
        if only_unevaluated and is_job_evaluated(job_id):
            continue
        
        try:
            agent = JobEvaluatorAgent()
            result = agent.run(
                job_id=job_id,
                description_text=row.get("description_text", ""),
                company_name=row.get("company_name", "Unknown"),
                title=row.get("title", "Unknown"),
                job_url=row.get("link", "Unknown"),
            )
            save_evaluation(result)
            processed += 1
            
            # Update task progress
            save_task_status(task_id, "running", {"completed": processed, "total": max_jobs})
        except Exception as e:
            print(f"Error evaluating {job_id}: {e}")
    
    # Mark complete
    save_task_status(task_id, "completed", {"completed": processed, "total": max_jobs})


@router.post("/batch", response_model=MessageResponse)
def batch_evaluate(request: BatchRequest, background_tasks: BackgroundTasks):
    """Start batch evaluation (async)."""
    import uuid
    from agents.database import save_task_status
    
    task_id = str(uuid.uuid4())
    
    # Save initial task status
    save_task_status(task_id, "queued", {"completed": 0, "total": request.max_jobs})
    
    # Add background task
    background_tasks.add_task(
        run_batch_evaluation,
        task_id,
        request.max_jobs,
        request.only_unevaluated,
        request.company_filter,
    )
    
    return {
        "message": f"Batch evaluation started for up to {request.max_jobs} jobs",
        "task_id": task_id,
    }


@router.post("/{job_id}", response_model=MessageResponse)
def evaluate_job(job_id: str, force: bool = False):
    """Evaluate a single job (synchronous)."""
    # Check if already evaluated
    if is_job_evaluated(job_id) and not force:
        return {"message": "Job already evaluated", "job_id": job_id}
    
    # Get job from Gold table
    job = get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found in Gold table")
    
    # Run evaluation
    try:
        agent = JobEvaluatorAgent()
        result = agent.run(
            job_id=job_id,
            description_text=job.get("description_text", ""),
            company_name=job.get("company_name", "Unknown"),
            title=job.get("title", "Unknown"),
            job_url=job.get("link", "Unknown"),
        )
        save_evaluation(result)
        
        return {
            "message": f"Evaluation complete: {result.get('Verdict')} (Score: {result.get('job_match_score')})",
            "job_id": job_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")



