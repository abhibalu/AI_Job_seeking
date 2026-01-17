"""
Evaluations routes - Evaluate jobs and get results.
"""
import json
from fastapi import APIRouter, HTTPException, BackgroundTasks

from agents.supabase_client import get_supabase_client

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



def get_job_by_id(job_id: str) -> dict | None:
    client = get_supabase_client()
    # Query jobs table directly
    result = client.table("jobs").select("*").eq("id", job_id).execute()
    
    if not result.data:
        return None
    
    job = result.data[0]
    
    # Ensure compatibility fields if needed (Supabase usually uses snake_case matching schema)
    # The gold data had 'description_text' and 'link'. Supabase has 'description_text' and 'job_url'.
    if "link" not in job and "job_url" in job:
        job["link"] = job["job_url"]
        
    return job


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
    import concurrent.futures
    import traceback
    
    print(f"DEBUG: Starting batch evaluation task {task_id}")
    print(f"DEBUG: Starting batch evaluation task {task_id}")
    try:
        from agents.supabase_client import get_supabase_client
        client = get_supabase_client()
        
        # Build query for jobs
        query = client.table("jobs").select("*").eq("status", "active")
        
        # Apply filters
        if company_filter:
            query = query.ilike("company_name", f"%{company_filter}%")
            
        # Get all candidates (limit to max_jobs + buffer if filtering happens later, 
        # but here we can just fetch max_jobs if only_unevaluated is False.
        # If only_unevaluated is True, we might need to fetch more or filter in DB.
        
        # Fetching jobs...
        # Optimally we should exclude evaluated IDs in the query if possible, 
        # but `not.in` with subquery isn't direct in supabase-py simple client without rpc or 2 steps.
        # We will fetch a chunk and filter.
        
        # Fetch up to max_jobs * 2 to handle some skips
        result = query.order("posted_at", desc=True).limit(max_jobs * 2).execute()
        
        if not result.data:
            print("DEBUG: No jobs found in Supabase")
            jobs = []
        else:
            jobs = result.data
            
        print(f"DEBUG: Loaded {len(jobs)} candidate jobs from Supabase")

        # Collect jobs to process
        jobs_to_process = []
        
        for row in jobs:
            if len(jobs_to_process) >= max_jobs:
                break
                
            job_id = str(row.get("id", ""))
            
            # Ensure compatibility
            if "link" not in row and "job_url" in row:
                row["link"] = row["job_url"]
                
            if only_unevaluated and is_job_evaluated(job_id):
                continue
                
            jobs_to_process.append(row)
        
        total_jobs = len(jobs_to_process)
        processed_count = 0
        failed_count = 0
        last_error = None
        
        # Save initial count
        save_task_status(task_id, "running", {"completed": 0, "total": total_jobs, "failed": 0})
        
        def process_singe_job(row):
            job_id = str(row.get("id", ""))
            print(f"DEBUG: Processing job {job_id}")
            try:
                agent = JobEvaluatorAgent()
                print(f"DEBUG: Running agent for {job_id}")
                result = agent.run(
                    job_id=job_id,
                    description_text=row.get("description_text", ""),
                    company_name=row.get("company_name", "Unknown"),
                    title=row.get("title", "Unknown"),
                    job_url=row.get("link", "Unknown"),
                )
                print(f"DEBUG: Agent finished for {job_id}")
                
                # --- Smart Conditional Parsing Logic ---
                from agents.jd_parser import run_jd_parser_task
                action = result.get("recommended_action")
                # User Policy: Only parse 'tailor' jobs. 'Apply' jobs are good enough as-is.
                if action == "tailor":
                    # Run synchronously in this thread since it's already a background worker
                    try:
                        run_jd_parser_task(job_id, row.get("description_text", ""))
                    except Exception as e:
                        print(f"Error parsing JD {job_id}: {e}")
                # ---------------------------------------

                return result
            except Exception as e:
                print(f"Error evaluating {job_id}: {e}")
                traceback.print_exc()
                return {"error": str(e), "job_id": job_id}

        # Run concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=settings.BATCH_EVAL_WORKERS) as executor:
            futures = {executor.submit(process_singe_job, row): row for row in jobs_to_process}
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    processed_count += 1
                    
                    if result and "error" not in result:
                        save_evaluation(result)
                    else:
                        failed_count += 1
                        if result and "error" in result:
                            last_error = result["error"]
                except Exception as e:
                    failed_count += 1
                    last_error = str(e)
                    print(f"Critical error in worker: {e}")
                
                # Update task progress
                save_task_status(task_id, "running", {
                    "completed": processed_count, 
                    "total": total_jobs, 
                    "failed": failed_count,
                    "last_error": last_error
                })
        
        # Mark complete
        status = "completed" if failed_count < total_jobs else "failed"
        final_error = last_error if status == "failed" else None
        
        save_task_status(task_id, status, {
            "completed": processed_count, 
            "total": total_jobs, 
            "failed": failed_count,
            "last_error": last_error
        }, error=final_error)

    except Exception as e:
        print(f"Fatal batch error: {e}")
        save_task_status(task_id, "failed", {"error": str(e)}, error=str(e))


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
def evaluate_job(job_id: str, background_tasks: BackgroundTasks, force: bool = False):
    """Evaluate a single job (synchronous)."""
    # Check if already evaluated
    if is_job_evaluated(job_id) and not force:
        return {"message": "Job already evaluated", "job_id": job_id}
    
    # Get job from Supabase (Primary Source now)
    job = get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found in Supabase")
    
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
        
        # --- Smart Conditional Parsing Logic ---
        from agents.jd_parser import run_jd_parser_task
        action = result.get("recommended_action")
        # User Policy: Only parse 'tailor' jobs. 'Apply' jobs are good enough as-is.
        if action == "tailor":
            background_tasks.add_task(
                run_jd_parser_task, 
                job_id, 
                job.get("description_text", "")
            )
        # ---------------------------------------
        
        return {
            "message": f"Evaluation complete: {result.get('Verdict')} (Score: {result.get('job_match_score')})",
            "job_id": job_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")



