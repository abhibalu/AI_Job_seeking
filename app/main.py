from __future__ import annotations
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Any, Dict, Optional, List
from pathlib import Path
import json
import subprocess
import tempfile
import datetime as dt

ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = ROOT / "resume.json"
VARIANTS_DIR = ROOT / "variants"
OUT_DIR = ROOT / "out"
APPROVALS_PATH = ROOT / "approvals.json"

app = FastAPI(title="Resume API")

VARIANTS_DIR.mkdir(exist_ok=True)
OUT_DIR.mkdir(exist_ok=True)

# Templates
TEMPLATES = Jinja2Templates(directory=str(ROOT / "app" / "templates"))


def read_json(p: Path) -> Dict[str, Any]:
    """Read and parse a JSON file."""
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_json_safe(p: Path, default: Any) -> Any:
    """Read JSON file, returning default if file does not exist or parsing fails."""
    if not p.exists():
        return default
    try:
        return read_json(p)
    except Exception:
        return default


def write_json(p: Path, data: Dict[str, Any]):
    """Write data as formatted JSON to file."""
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)




class CreateVariantRequest(BaseModel):
    variant_name: str
    tailored_resume: Dict[str, Any]
    company_name: str


# --- Simple approval store (file-based for now) ---
class ApprovalStatus(BaseModel):
    variant: str
    status: str  # draft|approved|rejected
    updated_at: str


def get_approvals() -> Dict[str, ApprovalStatus]:
    """Load all approval statuses from approvals.json."""
    raw = read_json_safe(APPROVALS_PATH, {})
    out: Dict[str, ApprovalStatus] = {}
    for k, v in raw.items():
        try:
            out[k] = ApprovalStatus(**v)
        except Exception:
            out[k] = ApprovalStatus(variant=k, status=str(getattr(v, "status", "draft")), updated_at=dt.datetime.utcnow().isoformat())
    return out


def set_approval(variant: str, status: str):
    """Update approval status for a variant (draft|approved|rejected)."""
    data = read_json_safe(APPROVALS_PATH, {})
    data[variant] = {
        "variant": variant,
        "status": status,
        "updated_at": dt.datetime.utcnow().isoformat(),
    }
    with APPROVALS_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@app.get("/resume")
def get_resume():
    """Get the base/original resume JSON."""
    return read_json(BASE_PATH)


@app.get("/resume/{section}")
@app.get("/resume/{section}/{item_id}")
def get_section(section: str, item_id: Optional[str] = None):
    """Get a section or a specific item by id from the base resume."""
    doc = get_resume()
    if section not in doc:
        raise HTTPException(404, f"Section '{section}' not found")
    sec = doc[section]
    if item_id is None:
        return sec
    if not isinstance(sec, list):
        raise HTTPException(400, f"Section '{section}' is not a list")
    for item in sec:
        if isinstance(item, dict) and str(item.get("id")) == str(item_id):
            return item
    raise HTTPException(404, f"Item '{item_id}' not found in section '{section}'")


@app.patch("/resume/{section}")
def patch_section(section: str, payload: Dict[str, Any]):
    """Update a section in the base resume.json."""
    base = read_json(BASE_PATH)
    base[section] = payload
    write_json(BASE_PATH, base)
    return {"ok": True}


@app.patch("/resume/{section}/{item_id}")
def patch_item(section: str, item_id: str, payload: Dict[str, Any]):
    """Update or insert a specific item by id in a section of the base resume.json."""
    base = read_json(BASE_PATH)
    sec = base.get(section, [])
    if not isinstance(sec, list):
        raise HTTPException(400, f"Section '{section}' is not a list")
    found = False
    for i, item in enumerate(sec):
        if isinstance(item, dict) and str(item.get("id")) == str(item_id):
            sec[i] = payload
            found = True
            break
    if not found:
        payload = dict(payload)
        payload.setdefault("id", item_id)
        sec.append(payload)
    base[section] = sec
    write_json(BASE_PATH, base)
    return {"ok": True}


@app.post("/variants")
def create_variant(req: CreateVariantRequest):
    """Create a new tailored resume variant (full JSON)."""
    variant_path = VARIANTS_DIR / f"{req.variant_name}.json"
    # Store full tailored resume + metadata
    data = {
        "company_name": req.company_name,
        "resume": req.tailored_resume,
        "created_at": dt.datetime.utcnow().isoformat(),
    }
    write_json(variant_path, data)
    return {"ok": True, "variant_name": req.variant_name, "path": str(variant_path)}


@app.get("/variants/{variant_name}")
def get_variant(variant_name: str):
    """Get a tailored variant by name."""
    variant_path = VARIANTS_DIR / f"{variant_name}.json"
    if not variant_path.exists():
        raise HTTPException(404, f"Variant '{variant_name}' not found")
    return read_json(variant_path)


@app.get("/variants/{variant_name}/resume")
def get_variant_resume(variant_name: str):
    """Get the tailored resume JSON from a variant."""
    variant_data = get_variant(variant_name)
    return variant_data.get("resume", {})


@app.get("/variants/{variant_name}/pdf")
def get_variant_pdf(variant_name: str):
    """Download the generated PDF for a variant (for n8n)."""
    variant_data = get_variant(variant_name)
    company = variant_data.get("company_name", "unknown")
    pdf_path = OUT_DIR / variant_name / f"Abhijith_sivadas_moothedath_{company}.pdf"
    if not pdf_path.exists():
        raise HTTPException(404, "PDF not generated yet. Call /export first.")
    return FileResponse(path=str(pdf_path), filename=pdf_path.name)




@app.post("/export")
def export_resume(variant_name: str, fmt: str = "pdf", theme: Optional[str] = None, review: bool = False):
    """Export a variant resume as HTML or PDF with custom naming.

    Params:
    - variant_name: name of stored variant (required)
    - fmt: 'html' or 'pdf' (default 'pdf')
    - theme: optional; 'elegant' to use jsonresume-theme-elegant, 'local' (default) for theme-local, or any theme name/path.
      If the chosen theme fails and it's 'local' (or unset), we automatically fallback to 'elegant'.
    - review: if True (HTML only), enables highlighting of AI-edited bullets for review; False = clean final output
    """
    variant_data = get_variant(variant_name)
    resume_json = variant_data.get("resume")
    company = variant_data.get("company_name", "unknown")

    # For review mode (HTML only), inject a flag; for final PDF/HTML, strip meta
    output_json = json.loads(json.dumps(resume_json))  # deep copy
    if review and fmt == "html":
        # Keep meta for highlighting, add review flag
        output_json["_review_mode"] = True
        # Also fetch base resume to show original text
        base = read_json(BASE_PATH)
        output_json["_base_resume"] = base
    else:
        # Clean final output: remove meta
        output_json.pop("meta", None)
        output_json.pop("_review_mode", None)
        output_json.pop("_base_resume", None)

    # Write to temp file for resume-cli
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
        json.dump(output_json, tf, ensure_ascii=False, indent=2)
        tmp_path = tf.name

    OUT_DIR.mkdir(exist_ok=True)
    variant_dir = OUT_DIR / variant_name
    variant_dir.mkdir(parents=True, exist_ok=True)

    # Custom filename: Abhijith_sivadas_moothedath_{company_name}.{fmt}
    filename = f"Abhijith_sivadas_moothedath_{company}.{fmt}"
    out_file = variant_dir / filename

    if fmt not in ("html", "pdf"):
        raise HTTPException(400, "unsupported fmt; use html or pdf")

    # Resolve theme argument
    chosen = theme or "local"
    def theme_value(val: str) -> str:
        if val == "elegant":
            return "elegant"
        if val == "local":
            return "local"  # installed as jsonresume-theme-local in node_modules
        return val  # allow custom theme name/path

    def run_export(theme_arg: str):
        cmd = [
            "resume", "export", str(out_file),
            "--theme", theme_arg,
            "--resume", tmp_path,
        ]
        return subprocess.run(cmd, capture_output=True, text=True)

    # First attempt
    res = run_export(theme_value(chosen))

    # Fallback to elegant if local failed
    if res.returncode != 0 and chosen in (None, "local"):
        fallback = run_export("elegant")
        if fallback.returncode != 0:
            raise HTTPException(500, f"export failed. local stderr: {res.stderr or res.stdout} | elegant stderr: {fallback.stderr or fallback.stdout}")
    elif res.returncode != 0:
        raise HTTPException(500, f"export failed. stderr: {res.stderr or res.stdout}")

    return FileResponse(path=str(out_file), filename=filename)


# ---- Minimal UI ----
@app.get("/ui", response_class=HTMLResponse)
def ui_index(request: Request):
    """Render main UI page listing all variants."""
    variants: List[str] = []
    if VARIANTS_DIR.exists():
        variants = [p.stem for p in VARIANTS_DIR.glob("*.json")]
    statuses = get_approvals()
    return TEMPLATES.TemplateResponse("index.html", {
        "request": request,
        "variants": sorted(variants),
        "statuses": statuses,
    })


@app.get("/ui/variant/{variant}", response_class=HTMLResponse)
def ui_variant(request: Request, variant: str):
    """Render detail page for a single variant with preview iframe and actions."""
    status = get_approvals().get(variant)
    return TEMPLATES.TemplateResponse("variant.html", {
        "request": request,
        "variant": variant,
        "status": status.status if status else "draft",
    })


@app.post("/ui/approve/{variant}")
def ui_approve(variant: str):
    """Mark a variant as approved."""
    set_approval(variant, "approved")
    return RedirectResponse(url=f"/ui/variant/{variant}", status_code=303)


@app.post("/ui/reject/{variant}")
def ui_reject(variant: str):
    """Mark a variant as rejected."""
    set_approval(variant, "rejected")
    return RedirectResponse(url=f"/ui/variant/{variant}", status_code=303)


@app.post("/ui/export/{variant_name}/{fmt}")
def ui_export(variant_name: str, fmt: str, review: bool = False):
    """Trigger export of variant and redirect browser to the output file."""
    if fmt not in ("html", "pdf"):
        raise HTTPException(400, "fmt must be html or pdf")
    # Trigger export (review mode for HTML preview, clean for PDF)
    export_resume(variant_name=variant_name, fmt=fmt, review=review)
    # Compute output path and redirect
    variant_data = get_variant(variant_name)
    company = variant_data.get("company_name", "unknown")
    filename = f"Abhijith_sivadas_moothedath_{company}.{fmt}"
    return RedirectResponse(url=f"/out/{variant_name}/{filename}", status_code=303)




# Lightweight API for n8n
@app.get("/approved")
def list_approved():
    """List all variants with approved status (for n8n polling)."""
    statuses = get_approvals()
    return [v for v, st in statuses.items() if st.status == "approved"]


@app.get("/status/{variant}")
def get_status(variant: str):
    """Get approval status and timestamp for a variant."""
    st = get_approvals().get(variant)
    return {"variant": variant, "status": (st.status if st else "draft"), "updated_at": (st.updated_at if st else None)}

@app.get("/")
def root():
    """Health check endpoint."""
    return {"ok": True}


# Mount static files LAST to avoid blocking routes
app.mount("/out", StaticFiles(directory=str(OUT_DIR)), name="out")
