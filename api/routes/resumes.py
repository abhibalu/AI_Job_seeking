import json
import logging
import os
import shutil
import uuid
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
    get_tailored_resume,
    get_tailored_resumes,
    update_tailored_resume_status,
    update_cover_letter,
    get_resume_changes,
    apply_change_action,
    apply_bulk_change_action,
)
from agents.resume_tailor import ResumeTailorAgent
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
        "skills": [
            f"{s['name']}: {', '.join(s.get('keywords', []))}" if isinstance(s, dict) and s.get('keywords')
            else (s.get('name', str(s)) if isinstance(s, dict) else str(s))
            for s in json_resume.get("skills", [])
        ],
        "projects": [
            {
                "id": proj.get("id", str(i)),
                "name": proj.get("name", ""),
                "description": proj.get("description", ""),
                "highlights": proj.get("highlights", []),
                "url": proj.get("url", "")
            }
            for i, proj in enumerate(json_resume.get("projects", []))
        ]
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
        
        if "error" in result:
            logger.error(f"Background parsing failed: {result.get('error')}")
            save_resume({"status": "error", "error": result.get("error")}, is_master=True)
        elif result.get("_validation_failed"):
            logger.error(f"Resume parsed but failed schema validation: {result.get('_validation_error')}")
            save_resume({"status": "error", "error": f"Resume parsed but failed schema validation: {result.get('_validation_error', 'Unknown')}"}, is_master=True)
        else:
            # Save final results
            save_resume(result, name="Master Resume", is_master=True)

            # Also update file backup
            with open(MASTER_RESUME_PATH, "w") as f:
                json.dump(result, f, indent=2)
            
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


from api.schemas import GDocImportRequest

@router.post("/import-gdoc")
async def import_from_google_doc(request: GDocImportRequest, background_tasks: BackgroundTasks):
    """Import resume from a Google Doc, parse via LLM, save as master."""
    from services.google_docs import read_google_doc

    try:
        doc_text = read_google_doc(request.document_id)
        if not doc_text.strip():
            raise HTTPException(400, "Google Doc is empty")

        # Save immediate "processing" state
        processing_status = {"status": "processing", "uploaded_at": datetime.now().isoformat()}
        save_resume(processing_status, name="Master Resume", is_master=True)

        # Reuse existing background parsing flow
        background_tasks.add_task(process_resume_background, doc_text)
        return {"status": "processing", "message": "Parsing Google Doc content..."}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to import Google Doc: {e}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


def run_tailoring_worker(task_id: str, job_id: str, initial_state: dict):
    """Background worker that runs tailoring pipeline with per-stage progress and cancellation."""
    from agents.database import save_task_status, get_task_status
    from agents.tailoring_subgraph import (
        node_plan, node_draft, node_validate, node_critique, node_save,
        route_validate, route_critique,
    )

    def is_cancelled():
        task = get_task_status(task_id)
        return task and task.get("status") == "cancelled"

    state = dict(initial_state)
    # Ensure required fields
    state.setdefault("errors", [])
    state.setdefault("status", "queued")
    state.setdefault("draft_resume", {})
    state.setdefault("final_resume_id", "")

    try:
        # --- Stage 1: Planning ---
        save_task_status(task_id, "running", {"completed": 0, "total": 4, "stage": "planning"})
        if is_cancelled(): return

        result = node_plan(state)
        state.update(result)
        if state.get("errors"):
            save_task_status(task_id, "failed", {"completed": 0, "total": 4, "stage": "planning"}, error="; ".join(state["errors"]))
            return

        # --- Stage 2: Drafting + Validation (may loop) ---
        save_task_status(task_id, "running", {"completed": 1, "total": 4, "stage": "drafting"})
        if is_cancelled(): return

        result = node_draft(state)
        state.update(result)
        if state.get("errors"):
            save_task_status(task_id, "failed", {"completed": 1, "total": 4, "stage": "drafting"}, error="; ".join(state["errors"]))
            return

        # Validate
        result = node_validate(state)
        state.update(result)

        # Route after validation — may loop back to draft
        route = route_validate(state)
        while route == "revise":
            if is_cancelled(): return
            result = node_draft(state)
            state.update(result)
            if state.get("errors"):
                save_task_status(task_id, "failed", {"completed": 1, "total": 4, "stage": "drafting"}, error="; ".join(state["errors"]))
                return
            result = node_validate(state)
            state.update(result)
            route = route_validate(state)

        if route == "error":
            save_task_status(task_id, "failed", {"completed": 1, "total": 4, "stage": "drafting"}, error="; ".join(state.get("errors", ["Unknown error"])))
            return

        # --- Stage 3: Critiquing (may loop back to draft) ---
        save_task_status(task_id, "running", {"completed": 2, "total": 4, "stage": "critiquing"})
        if is_cancelled(): return

        result = node_critique(state)
        state.update(result)
        if state.get("errors"):
            save_task_status(task_id, "failed", {"completed": 2, "total": 4, "stage": "critiquing"}, error="; ".join(state["errors"]))
            return

        # Route after critique — may loop back
        route = route_critique(state)
        while route == "revise":
            if is_cancelled(): return
            save_task_status(task_id, "running", {"completed": 2, "total": 4, "stage": "revising"})
            result = node_draft(state)
            state.update(result)
            if state.get("errors"):
                save_task_status(task_id, "failed", {"completed": 2, "total": 4, "stage": "revising"}, error="; ".join(state["errors"]))
                return
            result = node_validate(state)
            state.update(result)
            result = node_critique(state)
            state.update(result)
            if state.get("errors"):
                save_task_status(task_id, "failed", {"completed": 2, "total": 4, "stage": "critiquing"}, error="; ".join(state["errors"]))
                return
            route = route_critique(state)

        if route == "error":
            save_task_status(task_id, "failed", {"completed": 2, "total": 4, "stage": "critiquing"}, error="; ".join(state.get("errors", ["Unknown error"])))
            return

        # --- Stage 4: Saving ---
        save_task_status(task_id, "running", {"completed": 3, "total": 4, "stage": "saving"})
        if is_cancelled(): return

        result = node_save(state)
        state.update(result)
        if state.get("errors"):
            save_task_status(task_id, "failed", {"completed": 3, "total": 4, "stage": "saving"}, error="; ".join(state["errors"]))
            return

        record_id = state.get("final_resume_id", "")
        save_task_status(task_id, "completed", {"completed": 4, "total": 4, "stage": "done", "resume_id": record_id})

    except Exception as e:
        import traceback
        traceback.print_exc()
        save_task_status(task_id, "failed", {"completed": 0, "total": 4, "stage": "error"}, error=str(e))


@router.post("/tailor/{job_id}")
async def tailor_resume(job_id: str, background_tasks: BackgroundTasks):
    """Trigger tailoring as a background task. Returns task_id for SSE tracking."""
    from agents.database import save_task_status

    try:
        # 1. Get Base Resume (fast DB read)
        base_resume = get_db_master_resume()
        if not base_resume:
            if os.path.exists(MASTER_RESUME_PATH):
                with open(MASTER_RESUME_PATH, "r") as f:
                    base_resume = json.load(f)
        if not base_resume:
            raise HTTPException(status_code=400, detail="No base resume found.")

        base_resume = _to_json_resume_format(base_resume)
        if not base_resume:
            raise HTTPException(status_code=400, detail="No base resume found.")

        # 2. Get Approved Skills
        approved_skills = ""
        if os.path.exists(APPROVED_SKILLS_PATH):
            with open(APPROVED_SKILLS_PATH, "r") as f:
                approved_skills = f.read()

        # 3. Construct JD Context
        eval_res = get_evaluation(job_id) or {}
        jd_parsed = get_jd_parsed(job_id) or {}
        jd_context = {
            "role": eval_res.get("title_role", "Unknown"),
            "company": eval_res.get("company_name", "Unknown"),
            "summary": eval_res.get("summary", ""),
            "must_haves": jd_parsed.get("must_haves", []),
            "ats_keywords": jd_parsed.get("ats_keywords", []),
            "strategic_gaps": eval_res.get("gaps", {}),
            "improvement_suggestions": eval_res.get("improvement_suggestions", []),
        }

        # 4. Initial state
        initial_state = {
            "job_id": job_id,
            "base_resume": base_resume,
            "jd_context": jd_context,
            "approved_skills": approved_skills,
            "edit_plan": {},
            "revision_count": 0,
            "critique": [],
        }

        # 5. Create task and fire background worker
        task_id = str(uuid.uuid4())
        save_task_status(task_id, "queued", {"completed": 0, "total": 4, "stage": "queued"})

        background_tasks.add_task(run_tailoring_worker, task_id, job_id, initial_state)

        return {"task_id": task_id, "message": "Tailoring started"}

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to start tailoring: {str(e)}")


@router.get("/tailored/record/{record_id}")
def get_tailored_resume_by_id(record_id: str):
    """Get a single tailored resume by its record ID."""
    resume = get_tailored_resume(record_id)
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    if resume.get("content"):
        resume["content"] = _to_frontend_format(resume["content"])
    return resume


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

from api.schemas import ResumeChangeActionRequest, ResumeChangeBulkActionRequest


@router.get("/{resume_id}/changes")
def list_resume_changes(resume_id: str):
    """Get all per-change review records for a tailored resume (ADR-0010).
    Sorted by confidence asc — lowest confidence (most uncertain) first.
    """
    changes = get_resume_changes(resume_id)
    return changes


@router.patch("/{resume_id}/changes/bulk")
def bulk_change_action(resume_id: str, body: ResumeChangeBulkActionRequest):
    """Accept / Reject / Keep original across multiple changes at once (ADR-0010).

    scope='remaining' (default): only unreviewed changes.
    scope='all': all changes for the resume.
    """
    updated = apply_bulk_change_action(resume_id, body.action, body.scope)
    return {"updated": updated}


@router.patch("/{resume_id}/changes/{change_id}")
def change_action(resume_id: str, change_id: str, body: ResumeChangeActionRequest):
    """Apply Accept / Reject / Keep original to a single change (ADR-0010).

    'keep_original': sets accepted_text = original_text immediately.
    No regeneration loop is triggered — the original text is the final value.
    """
    apply_change_action(change_id, body.action)
    return {"ok": True}


@router.patch("/{resume_id}/cover_letter")
def save_cover_letter(resume_id: str, body: dict):
    """Save user-edited cover letter for a tailored resume (ADR-0011).
    Called on blur from the CL textarea in TailoringReview.
    """
    cover_letter = body.get("cover_letter", "")
    update_cover_letter(resume_id, cover_letter)
    return {"ok": True}


def _build_replacement_map(base: dict, tailored: dict) -> dict[str, str]:
    """Return a {old_text: new_text} map of strings that differ between base and tailored resumes.

    Both dicts must be in frontend format (fullName, experience, skills, summary…).
    Only non-empty, changed strings are included.
    """
    replacements: dict[str, str] = {}

    def _add(old: str, new: str) -> None:
        old, new = (old or "").strip(), (new or "").strip()
        if old and new and old != new:
            replacements[old] = new

    # Summary
    _add(base.get("summary", ""), tailored.get("summary", ""))

    # Experience bullets (matched by position)
    base_exp = base.get("experience", [])
    tail_exp = tailored.get("experience", [])
    for b_job, t_job in zip(base_exp, tail_exp):
        for b_bullet, t_bullet in zip(b_job.get("achievements", []), t_job.get("achievements", [])):
            _add(b_bullet, t_bullet)

    # Skills (frontend format stores each skill as a plain string)
    for b_skill, t_skill in zip(base.get("skills", []), tailored.get("skills", [])):
        _add(str(b_skill), str(t_skill))

    return replacements


@router.post("/export-gdoc/{job_id}")
async def export_to_google_docs(job_id: str):
    """Export the latest tailored resume for a job to a Google Doc."""
    try:
        from services.google_docs import create_tailored_resume_doc

        # 1. Fetch latest tailored resume for this job (exclude master)
        versions = [v for v in get_tailored_resumes(job_id) if v.get("status") != "master"]
        if not versions:
            raise HTTPException(status_code=404, detail="No tailored resume found to export")

        latest_version = versions[0]
        content = latest_version.get("content") or {}
        resume_data = _to_frontend_format(content)

        # 2. Get Job Details for the Doc Title
        eval_res = get_evaluation(job_id) or {}
        job_title = eval_res.get("title_role", "Unknown Role")
        company = eval_res.get("company_name", "Unknown Company")

        # 3. Get settings
        from backend.settings import settings
        folder_id = settings.GOOGLE_DRIVE_FOLDER_ID or None
        base_doc_id = settings.GOOGLE_BASE_RESUME_DOC_ID or None

        # 4. Build replacement map when copy-and-fill path is active
        # TODO: replacements disabled for progressive testing — verify copy lands first
        replacements: dict[str, str] = {}

        # 5. Generate Google Doc
        doc_url = await run_in_threadpool(
            create_tailored_resume_doc,
            job_title=job_title,
            company=company,
            resume_data=resume_data,
            folder_id=folder_id,
            base_doc_id=base_doc_id,
            replacements=replacements,
        )

        return {"status": "success", "url": doc_url}

    except Exception as e:
        logger.error(f"Failed to export Google Doc: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
