import json
import os
import shutil
from typing import Annotated
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
import pdfplumber
from datetime import datetime

from agents.resume_parser import ResumeParserAgent

router = APIRouter()

MASTER_RESUME_PATH = "/Users/abhijithm/Documents/Code/TailorAI/test/master_resume.json"
UPLOAD_DIR = "/Users/abhijithm/Documents/Code/TailorAI/uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)

from agents.database import (
    get_master_resume as get_db_master_resume, 
    save_resume,
    save_tailored_resume,
    get_tailored_resumes,
    update_tailored_resume_status
)
from agents.resume_tailor import ResumeTailorAgent

APPROVED_SKILLS_PATH = "agent_prompts/approved_skills.md"

@router.get("/master")
def get_master_resume():
    """Get the current master resume JSON."""
    resume = get_db_master_resume()
    if resume:
        return resume
        
    # Fallback to file for backward compatibility during migration
    if os.path.exists(MASTER_RESUME_PATH):
        try:
            with open(MASTER_RESUME_PATH, "r") as f:
                return json.load(f)
        except:
            pass
            
    raise HTTPException(status_code=404, detail="Master resume not found. Please upload a resume first.")

from api.schemas import ResumeData

@router.post("/master")
def update_master_resume(resume: ResumeData):
    """Update (save) the master resume with new content."""
    try:
        # Convert Pydantic model to dict
        content = resume.model_dump()
        
        # Save as new master version
        save_resume(content, name="Master Resume", is_master=True)
        
        # Also update file backup for redundancy
        if os.path.exists(MASTER_RESUME_PATH):
             with open(MASTER_RESUME_PATH, "w") as f:
                json.dump(content, f, indent=2)
                
        return {"status": "success", "message": "Resume updated successfully"}
    except Exception as e:
        print(f"Error updating resume: {e}")
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.concurrency import run_in_threadpool

async def process_resume_background(full_text: str):
    """Background task to parse resume and save to DB."""
    try:
        agent = ResumeParserAgent()
        result = await run_in_threadpool(agent.run, resume_text=full_text)
        
        if "error" not in result:
             # Save final results
             save_resume(result, name="Master Resume", is_master=True)
             
             # Also update file backup
             with open(MASTER_RESUME_PATH, "w") as f:
                json.dump(result, f, indent=2)
        else:
            print(f"Background parsing failed: {result.get('error')}")
            # Save error status so UI can show it
            save_resume({"status": "error", "error": result.get("error")}, is_master=True)
            
    except Exception as e:
        print(f"Background parsing exception: {e}")
        save_resume({"status": "error", "error": str(e)}, is_master=True)

@router.post("/upload")
async def upload_resume(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Upload a PDF resume, save processing status, and trigger background parsing."""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    try:
        # Save uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Extract text using pdfplumber
        full_text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n\n"
        
        if not full_text:
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")

        # Save immediate "processing" state to DB
        processing_status = {"status": "processing", "uploaded_at": datetime.now().isoformat()}
        save_resume(processing_status, name="Master Resume", is_master=True)

        # Trigger background parsing
        background_tasks.add_task(process_resume_background, full_text)
        
        return processing_status

    except Exception as e:
        print(f"Error starting resume process: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tailor/{job_id}")
async def tailor_resume(job_id: str):
    """
    Generate a tailored resume for a specific job.
    """
    try:
        # 1. Get Base Resume
        base_resume = get_db_master_resume()
        if not base_resume:
             # Fallback
             if os.path.exists(MASTER_RESUME_PATH):
                 with open(MASTER_RESUME_PATH, "r") as f:
                     base_resume = json.load(f)
        
        if not base_resume:
            raise HTTPException(status_code=400, detail="No base resume found.")

        # 2. Get Approved Skills
        approved_skills = ""
        if os.path.exists(APPROVED_SKILLS_PATH):
            with open(APPROVED_SKILLS_PATH, "r") as f:
                approved_skills = f.read()
        else:
            print("Warning: Approved skills file not found.")

        # 3. Run Agent
        agent = ResumeTailorAgent()
        # Note: Run synchronously for now as it's a critical User-initiated action, 
        # but could be backgrounded if slow (>20s). 
        # Given "Conservative Editor" (40% rule), it should be fast-ish.
        # But to be safe on timeouts, let's allow it to block or use run_in_threadpool.
        
        tailored_content = await run_in_threadpool(
            agent.run_tailoring, 
            job_id=job_id, 
            base_resume=base_resume, 
            approved_skills=approved_skills
        )
        
        # 4. Save Result
        # Determine version number
        existing = get_tailored_resumes(job_id)
        version = len(existing) + 1
        
        record_id = save_tailored_resume(job_id, version, tailored_content, status="pending")
        
        return {
            "id": record_id,
            "version": version,
            "status": "pending",
            "content": tailored_content
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        
        # Check for rate limit / quota errors
        error_str = str(e).lower()
        if "429" in str(e) or "rate" in error_str or "quota" in error_str or "too many requests" in error_str:
            raise HTTPException(
                status_code=429, 
                detail="Rate limit exceeded. The AI model is temporarily unavailable. Please wait 1-2 minutes and try again."
            )
        
        raise HTTPException(status_code=500, detail=f"Tailoring failed: {str(e)}")


@router.get("/tailored/{job_id}")
def get_tailored_versions(job_id: str):
    """Get all tailored versions for a job."""
    return get_tailored_resumes(job_id)


@router.post("/tailored/{record_id}/status")
def update_status(record_id: str, status: str):
    """Update status (approved/rejected)."""
    if status not in ["approved", "rejected", "pending"]:
         raise HTTPException(status_code=400, detail="Invalid status")
         
    update_tailored_resume_status(record_id, status)
    return {"status": "success"}
