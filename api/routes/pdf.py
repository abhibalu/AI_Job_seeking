import json
import os
import tempfile
import typst
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel
from typing import List, Optional

from api.schemas import ResumeData 

router = APIRouter()

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../templates")

class Helper:
    # Just a helper for the route
    pass

@router.post("/generate")
def generate_pdf(data: ResumeData, template: str = "modern"):
    """
    Generate a PDF resume using Typst.
    """
    
    # Validate template exists
    template_path = os.path.join(TEMPLATES_DIR, f"{template}.typ")
    if not os.path.exists(template_path):
        # Fallback to modern if not found
        template_path = os.path.join(TEMPLATES_DIR, "modern.typ")
        
    try:
        # Create a temporary directory for compilation context
        with tempfile.TemporaryDirectory() as temp_dir:
            
            # 1. Write data.json
            data_dict = data.dict()
            json_path = os.path.join(temp_dir, "data.json")
            with open(json_path, "w") as f:
                json.dump(data_dict, f)
                
            # 2. Copy the template file to temp dir (to resolve local imports if any)
            # OR better: structure the entrypoint to import from absolute path? 
            # Typst might be strict about paths. Safer to copy template content.
            
            with open(template_path, "r") as f:
                template_content = f.read()
                
            # 3. Create entrypoint.typ
            # We explicitly call the 'resume' function defined in the template
            entrypoint_content = f"""
import "{template}.typ": resume
#let data = json("data.json")
#show: resume(data)
"""
            # We need to make sure the template file is available in the temp dir as '{template}.typ'
            # So we write the content we read back to a file in temp_dir
            with open(os.path.join(temp_dir, f"{template}.typ"), "w") as f:
                f.write(template_content)
                
            entrypoint_path = os.path.join(temp_dir, "main.typ")
            with open(entrypoint_path, "w") as f:
                f.write(entrypoint_content)
                
            # 4. Compile
            output_pdf_path = os.path.join(temp_dir, "resume.pdf")
            typst.compile(entrypoint_path, output=output_pdf_path)
            
            # 5. Read PDF bytes
            with open(output_pdf_path, "rb") as f:
                pdf_bytes = f.read()
                
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=resume_{template}.pdf"}
            )

    except Exception as e:
        print(f"PDF Generation Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
