"""
Parse routes - Parse JD for evaluated jobs.
"""
import json
from fastapi import APIRouter, HTTPException

from agents.supabase_client import get_supabase_client

from backend.settings import settings
from api.schemas import ParseResult, MessageResponse
from agents.database import (
    get_db_connection,
    is_job_evaluated,
    is_job_parsed,
    save_jd_parsed,
    get_evaluation,
)
from agents.jd_parser import JDParserAgent

router = APIRouter()



def get_job_by_id(job_id: str) -> dict | None:
    client = get_supabase_client()
    result = client.table("jobs").select("*").eq("id", job_id).execute()
    
    if not result.data:
        return None
        
    return result.data[0]


@router.get("/{job_id}", response_model=ParseResult)
def get_parsed_jd(job_id: str):
    """Get parsed JD signals for a job."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jd_parsed WHERE job_id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Parsed JD for job {job_id} not found")
    
    result = dict(row)
    
    # Parse JSON fields
    for field in ["must_haves", "nice_to_haves", "location_constraints", "ats_keywords", "normalized_skills"]:
        if result.get(field):
            try:
                result[field] = json.loads(result[field])
            except:
                pass
    
    return result


@router.post("/{job_id}", response_model=MessageResponse)
def parse_jd(job_id: str, force: bool = False):
    """Parse JD for a job (must be evaluated first)."""
    # Check if evaluated
    if not is_job_evaluated(job_id):
        raise HTTPException(status_code=400, detail=f"Job {job_id} not evaluated yet")
    
    # Check verdict
    evaluation = get_evaluation(job_id)
    action = evaluation.get("recommended_action", "")
    if action == "skip" and not force:
        return {"message": "Job marked as 'skip'. Use force=true to parse anyway.", "job_id": job_id}
    
    # Check if already parsed
    if is_job_parsed(job_id) and not force:
        return {"message": "JD already parsed", "job_id": job_id}
    
    # Get job from Supabase
    job = get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found in Supabase")
    
    # Run parser
    try:
        agent = JDParserAgent()
        result = agent.run(
            job_id=job_id,
            description_text=job.get("description_text", ""),
        )
        save_jd_parsed(result)
        
        return {
            "message": f"JD parsed: {len(result.get('must_haves', []))} must-haves, {len(result.get('ats_keywords', []))} keywords",
            "job_id": job_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parse failed: {str(e)}")
