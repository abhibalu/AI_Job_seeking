import json
import logging
import os
import shutil
from typing import Annotated
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
import pdfplumber
from datetime import datetime

logger = logging.getLogger(__name__)

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
from agents.tailoring_subgraph import build_tailoring_subgraph
from agents.database import get_evaluation, get_jd_parsed

APPROVED_SKILLS_PATH = "agent_prompts/approved_skills.md"

def _to_frontend_format(json_resume: dict) -> dict:
    """Transform JSON Resume format to frontend format for the Editor.
    
    JSON Resume uses: basics, work, highlights
    Frontend uses: fullName, experience, achievements
    """
    # If already in frontend format, return as-is
    if "fullName" in json_resume and "experience" in json_resume:
        return json_resume
    
    basics = json_resume.get("basics", {})
    location = basics.get("location", {})
    location_str = location.get("city", "") if isinstance(location, dict) else str(location)
    
    return {
        "fullName": basics.get("name", ""),
        "title": basics.get("label", ""),
        "email": basics.get("email", ""),
        "phone": basics.get("phone", ""),
        "location": location_str,
        "summary": basics.get("summary", ""),
        "websites": [p.get("url", "") for p in basics.get("profiles", [])],
        "experience": [
            {
                "id": work.get("id", str(i)),
                "company": work.get("name", ""),
                "role": work.get("position", ""),
                "period": f"{work.get('startDate', '')} - {work.get('endDate', 'Present')}",
                "location": work.get("location", ""),
                "achievements": work.get("highlights", [])
            }
            for i, work in enumerate(json_resume.get("work", []))
        ],
        "education": [
            {
                "id": edu.get("id", str(i)),
                "institution": edu.get("institution", ""),
                "degree": edu.get("studyType", edu.get("degree", "")),
                "period": edu.get("endDate", edu.get("period", "")),
                "location": edu.get("location", ""),
                "score": edu.get("score", "")
            }
            for i, edu in enumerate(json_resume.get("education", []))
        ],
        "skills": json_resume.get("skills", [])
    }

@router.get("/master")
def get_master_resume():
    """Get the current master resume JSON in frontend format."""
    resume = get_db_master_resume()
    if resume:
        return _to_frontend_format(resume)
        
    # Fallback to file for backward compatibility during migration
    if os.path.exists(MASTER_RESUME_PATH):
        try:
            with open(MASTER_RESUME_PATH, "r") as f:
                return _to_frontend_format(json.load(f))
        except:
            pass
            
    raise HTTPException(status_code=404, detail="Master resume not found. Please upload a resume first.")

from api.schemas import ResumeData

def _to_json_resume_format(data: dict) -> dict:
    """Transform frontend resume format to JSON Resume format.
    
    Frontend uses: fullName, experience, achievements
    JSON Resume uses: basics, work, highlights
    
    If already in JSON Resume format, returns as-is.
    """
    # Check if already in JSON Resume format
    if "basics" in data and "work" in data:
        return data
        
    return {
        "$schema": "https://raw.githubusercontent.com/jsonresume/resume-schema/v1.0.0/schema.json",
        "basics": {
            "name": data.get("fullName", ""),
            "label": data.get("title", ""),
            "email": data.get("email", ""),
            "phone": data.get("phone", ""),
            "location": {"city": data.get("location", "")},
            "summary": data.get("summary", ""),
            "profiles": [{"url": url} for url in data.get("websites", [])]
        },
        "work": [
            {
                "id": exp.get("id", ""),
                "name": exp.get("company", ""),
                "position": exp.get("role", ""),
                "location": exp.get("location", ""),
                "startDate": exp.get("period", "").split(" - ")[0] if " - " in exp.get("period", "") else exp.get("period", ""),
                "endDate": exp.get("period", "").split(" - ")[1] if " - " in exp.get("period", "") else "Present",
                "highlights": exp.get("achievements", [])
            }
            for exp in data.get("experience", [])
        ],
        "education": [
            {
                "id": edu.get("id", ""),
                "institution": edu.get("institution", ""),
                "studyType": edu.get("degree", ""),
                "area": "",
                "endDate": edu.get("period", ""),
                "location": edu.get("location", ""),
                "score": edu.get("score", "")
            }
            for edu in data.get("education", [])
        ],
        "skills": data.get("skills", []),
        "meta": {"theme": "elegant"}
    }

@router.post("/master")
def update_master_resume(resume: ResumeData):
    """Update (save) the master resume with new content.
    
    Converts frontend format to JSON Resume format before saving.
    """
    try:
        # Convert Pydantic model to dict
        frontend_data = resume.model_dump()
        
        # Transform to JSON Resume format for storage
        json_resume_content = _to_json_resume_format(frontend_data)
        
        # Save as new master version
        save_resume(json_resume_content, name="Master Resume", is_master=True)
        
        # Also update file backup for redundancy
        if os.path.exists(MASTER_RESUME_PATH):
             with open(MASTER_RESUME_PATH, "w") as f:
                json.dump(json_resume_content, f, indent=2)
                
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
        
        # Normalize to JSON Resume format (handles both frontend and JSON Resume formats)
        base_resume = _to_json_resume_format(base_resume)
        
        if not base_resume:
            raise HTTPException(status_code=400, detail="No base resume found.")

        # 2. Get Approved Skills
        approved_skills = ""
        if os.path.exists(APPROVED_SKILLS_PATH):
            with open(APPROVED_SKILLS_PATH, "r") as f:
                approved_skills = f.read()
        else:
            print("Warning: Approved skills file not found.")

        # 3. Construct JD Context
        eval_res = get_evaluation(job_id) or {}
        jd_parsed = get_jd_parsed(job_id) or {}

        jd_context = {
            "role": eval_res.get("title_role", "Unknown"),
            "company": eval_res.get("company_name", "Unknown"),
            "summary": eval_res.get("summary", ""),
            "must_haves": jd_parsed.get("must_haves", []),
            "ats_keywords": jd_parsed.get("keywords_to_include", []),
            "strategic_gaps": eval_res.get("gaps", {}),
            "improvement_suggestions": eval_res.get("improvement_suggestions", []),
        }

        # 4. Construct Initial State for Sub-Graph
        initial_state = {
            "job_id": job_id,
            "base_resume": base_resume,
            "jd_context": jd_context,
            "approved_skills": approved_skills,
            "revision_count": 0,
            "critique": [],
        }

        # 5. Compile and Invoke Sub-Graph
        subgraph = build_tailoring_subgraph().compile()
        
        # Run the subgraph synchronously
        final_state = await run_in_threadpool(
            subgraph.invoke,
            initial_state
        )

        if final_state.get("errors"):
            raise HTTPException(status_code=500, detail="; ".join(final_state["errors"]))
            
        record_id = final_state.get("final_resume_id")
        if not record_id:
            raise HTTPException(status_code=500, detail="Tailoring subgraph returned no final_resume_id")

        # 6. Return Result
        # We need to fetch the newly saved tailored resume from DB to return it,
        # or we could return draft_resume from final_state. Let's return draft_resume.
        tailored_content = final_state.get("draft_resume", {})
        version = final_state.get("revision_count", 0) # This is roughly the version

        return {
            "id": record_id,
            "version": version,
            "status": "pending",
            "content": _to_frontend_format(tailored_content)
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
    versions = get_tailored_resumes(job_id)
    # Convert content to frontend format for each version
    for version in versions:
        if version.get("content"):
            version["content"] = _to_frontend_format(version["content"])
    return versions


@router.post("/tailored/{record_id}/status")
def update_status(record_id: str, status: str):
    """Update status (approved/rejected)."""
    if status not in ["approved", "rejected", "pending"]:
         raise HTTPException(status_code=400, detail="Invalid status")
         
    update_tailored_resume_status(record_id, status)
    return {"status": "success"}

@router.post("/export-gdoc/{job_id}")
async def export_to_google_docs(job_id: str):
    """Export the latest tailored resume for a job to a Google Doc."""
    try:
        from services.google_docs import create_tailored_resume_doc
        
        # 1. Fetch latest tailored resume for this job
        versions = get_tailored_resumes(job_id)
        if not versions:
            raise HTTPException(status_code=404, detail="No tailored resume found to export")
            
        latest_version = versions[0]
        resume_data = _to_frontend_format(latest_version.get("content", {}))
        
        # 2. Get Job Details for the Doc Title
        eval_res = get_evaluation(job_id) or {}
        job_title = eval_res.get("title_role", "Unknown Role")
        company = eval_res.get("company_name", "Unknown Company")
        
        # 3. Get Drive Folder ID from settings
        from backend.settings import settings
        folder_id = settings.GOOGLE_DRIVE_FOLDER_ID or None
        
        # 4. Generate Google Doc
        doc_url = await run_in_threadpool(
            create_tailored_resume_doc,
            job_title=job_title,
            company=company,
            resume_data=resume_data,
            folder_id=folder_id
        )
        
        return {"status": "success", "url": doc_url}
        
    except Exception as e:
        logger.error(f"Failed to export Google Doc: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
