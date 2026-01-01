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

from agents.database import get_master_resume as get_db_master_resume, save_resume

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
