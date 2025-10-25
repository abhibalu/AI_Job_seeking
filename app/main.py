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
OVERLAYS_DIR = ROOT / "overlays"
OUT_DIR = ROOT / "out"
APPROVALS_PATH = ROOT / "approvals.json"

app = FastAPI(title="Resume API")

# Mount output dir to serve generated previews/downloads
app.mount("/out", StaticFiles(directory=str(OUT_DIR)), name="out")

OVERLAYS_DIR.mkdir(exist_ok=True)
OUT_DIR.mkdir(exist_ok=True)

# Templates
TEMPLATES = Jinja2Templates(directory=str(ROOT / "app" / "templates"))


def read_json(p: Path) -> Dict[str, Any]:
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_json_safe(p: Path, default: Any) -> Any:
    if not p.exists():
        return default
    try:
        return read_json(p)
    except Exception:
        return default


def write_json(p: Path, data: Dict[str, Any]):
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_obj(x: Any) -> bool:
    return isinstance(x, dict)


def is_list(x: Any) -> bool:
    return isinstance(x, list)


def index_by_id(arr: list[dict]) -> dict[str, dict]:
    return {str(item.get("id")): item for item in arr if isinstance(item, dict) and "id" in item}


def deep_merge(base: Any, overlay: Any) -> Any:
    # Objects: deep-merge
    if is_obj(base) and is_obj(overlay):
        out = dict(base)
        for k, v in overlay.items():
            if k in out:
                out[k] = deep_merge(out[k], v)
            else:
                out[k] = v
        return out
    # Arrays: merge-by-id if possible, else replace
    if is_list(base) and is_list(overlay):
        if all(isinstance(x, dict) and "id" in x for x in base) or all(isinstance(x, dict) and "id" in x for x in overlay):
            base_idx = index_by_id([x for x in base if isinstance(x, dict)]) if is_list(base) else {}
            # start with base (preserve order)
            merged_list: list[dict] = [json.loads(json.dumps(it)) if isinstance(it, dict) else it for it in base]
            o_idx = index_by_id([x for x in overlay if isinstance(x, dict)])
            # apply overlay items by id
            for oid, oitem in o_idx.items():
                if oid in base_idx:
                    # find index in merged_list to replace with merged object
                    for i, it in enumerate(merged_list):
                        if isinstance(it, dict) and str(it.get("id")) == oid:
                            merged_list[i] = deep_merge(it, oitem)
                            break
                else:
                    merged_list.append(oitem)
            return merged_list
        # default: replace array
        return overlay
    # scalars: override
    return overlay


class TailorRequest(BaseModel):
    variant: str
    overlay: Optional[Dict[str, Any]] = None
    jd: Optional[str] = None  # for future use


# --- Simple approval store (file-based for now) ---
class ApprovalStatus(BaseModel):
    variant: str
    status: str  # draft|approved|rejected
    updated_at: str


def get_approvals() -> Dict[str, ApprovalStatus]:
    raw = read_json_safe(APPROVALS_PATH, {})
    out: Dict[str, ApprovalStatus] = {}
    for k, v in raw.items():
        try:
            out[k] = ApprovalStatus(**v)
        except Exception:
            out[k] = ApprovalStatus(variant=k, status=str(getattr(v, "status", "draft")), updated_at=dt.datetime.utcnow().isoformat())
    return out


def set_approval(variant: str, status: str):
    data = read_json_safe(APPROVALS_PATH, {})
    data[variant] = {
        "variant": variant,
        "status": status,
        "updated_at": dt.datetime.utcnow().isoformat(),
    }
    with APPROVALS_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@app.get("/resume")
def get_resume(variant: Optional[str] = None):
    base = read_json(BASE_PATH)
    if not variant:
        return base
    ov_path = OVERLAYS_DIR / f"{variant}.json"
    if not ov_path.exists():
        return base
    overlay = read_json(ov_path)
    return deep_merge(base, overlay)


@app.get("/resume/{section}")
@app.get("/resume/{section}/{item_id}")
def get_section(section: str, item_id: Optional[str] = None, variant: Optional[str] = None):
    doc = get_resume(variant)
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
    base = read_json(BASE_PATH)
    if section not in base:
        base[section] = payload
    else:
        base[section] = deep_merge(base[section], payload)
    write_json(BASE_PATH, base)
    return {"ok": True}


@app.patch("/resume/{section}/{item_id}")
def patch_item(section: str, item_id: str, payload: Dict[str, Any]):
    base = read_json(BASE_PATH)
    sec = base.get(section)
    if not isinstance(sec, list):
        raise HTTPException(400, f"Section '{section}' is not a list")
    found = False
    for i, item in enumerate(sec):
        if isinstance(item, dict) and str(item.get("id")) == str(item_id):
            sec[i] = deep_merge(item, payload)
            found = True
            break
    if not found:
        payload = dict(payload)
        payload.setdefault("id", item_id)
        sec.append(payload)
    base[section] = sec
    write_json(BASE_PATH, base)
    return {"ok": True}


@app.post("/variants/{variant}")
def create_variant(variant: str):
    p = OVERLAYS_DIR / f"{variant}.json"
    if p.exists():
        return {"ok": True, "path": str(p)}
    write_json(p, {})
    return {"ok": True, "path": str(p)}


@app.get("/variants/{variant}/resume")
def get_variant_resume(variant: str):
    return get_resume(variant)


@app.patch("/variants/{variant}/{section}")
def patch_variant_section(variant: str, section: str, payload: Dict[str, Any]):
    p = OVERLAYS_DIR / f"{variant}.json"
    overlay = read_json(p) if p.exists() else {}
    cur = overlay.get(section)
    if cur is None:
        overlay[section] = payload
    else:
        overlay[section] = deep_merge(cur, payload)
    write_json(p, overlay)
    return {"ok": True}


@app.patch("/variants/{variant}/{section}/{item_id}")
def patch_variant_item(variant: str, section: str, item_id: str, payload: Dict[str, Any]):
    p = OVERLAYS_DIR / f"{variant}.json"
    overlay = read_json(p) if p.exists() else {}
    sec = overlay.get(section)
    if sec is None:
        sec = []
    if not isinstance(sec, list):
        raise HTTPException(400, f"Section '{section}' is not a list in overlay")
    found = False
    for i, item in enumerate(sec):
        if isinstance(item, dict) and str(item.get("id")) == str(item_id):
            sec[i] = deep_merge(item, payload)
            found = True
            break
    if not found:
        payload = dict(payload)
        payload.setdefault("id", item_id)
        sec.append(payload)
    overlay[section] = sec
    write_json(p, overlay)
    return {"ok": True}


@app.post("/tailor")
def tailor(req: TailorRequest):
    if not req.variant:
        raise HTTPException(400, "variant is required")
    if not req.overlay:
        raise HTTPException(400, "overlay is required (precomputed by AI)")
    p = OVERLAYS_DIR / f"{req.variant}.json"
    cur = read_json(p) if p.exists() else {}
    write_json(p, deep_merge(cur, req.overlay))
    return {"ok": True}


@app.post("/export")
def export_resume(variant: Optional[str] = None, fmt: str = "pdf"):
    merged = get_resume(variant)
    # validate by writing to temp file
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
        json.dump(merged, tf, ensure_ascii=False, indent=2)
        tmp_path = tf.name
    OUT_DIR.mkdir(exist_ok=True)
    variant_dir = OUT_DIR / (variant or "default")
    variant_dir.mkdir(parents=True, exist_ok=True)
    out_file = variant_dir / f"resume.{fmt}"

    if fmt == "html" or fmt == "pdf":
        cmd = [
            "resume", "export", str(out_file),
            "--theme", str(ROOT / "theme-local"),
            "--resume", tmp_path,
        ]
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            raise HTTPException(500, f"export failed: {e}")
    else:
        raise HTTPException(400, "unsupported fmt; use html or pdf")

    return FileResponse(path=str(out_file), filename=out_file.name)


# ---- Minimal UI ----
@app.get("/ui", response_class=HTMLResponse)
def ui_index(request: Request):
    # variants are overlay files + default
    variants: List[str] = ["default"]
    if OVERLAYS_DIR.exists():
        variants += [p.stem for p in OVERLAYS_DIR.glob("*.json")]
    statuses = get_approvals()
    return TEMPLATES.TemplateResponse("index.html", {
        "request": request,
        "variants": sorted(set(variants)),
        "statuses": statuses,
    })


@app.get("/ui/variant/{variant}", response_class=HTMLResponse)
def ui_variant(request: Request, variant: str):
    status = get_approvals().get(variant)
    return TEMPLATES.TemplateResponse("variant.html", {
        "request": request,
        "variant": variant,
        "status": status.status if status else "draft",
    })


@app.post("/ui/approve/{variant}")
def ui_approve(variant: str):
    set_approval(variant, "approved")
    return RedirectResponse(url=f"/ui/variant/{variant}", status_code=303)


@app.post("/ui/reject/{variant}")
def ui_reject(variant: str):
    set_approval(variant, "rejected")
    return RedirectResponse(url=f"/ui/variant/{variant}", status_code=303)


@app.post("/ui/export/{variant}/{fmt}")
def ui_export(variant: str, fmt: str):
    if fmt not in ("html", "pdf"):
        raise HTTPException(400, "fmt must be html or pdf")
    # Trigger export and redirect to file
    resp = export_resume(variant=variant, fmt=fmt)
    # resp is FileResponse; compute path under /out and redirect for browser to open directly
    return RedirectResponse(url=f"/out/{variant}/resume.{fmt}", status_code=303)


@app.post("/ui/create_variant")
def ui_create_variant(name: str):
    create_variant(name)
    return RedirectResponse(url=f"/ui/variant/{name}", status_code=303)


# Lightweight API for n8n
@app.get("/approved")
def list_approved():
    statuses = get_approvals()
    return [v for v, st in statuses.items() if st.status == "approved"]


@app.get("/status/{variant}")
def get_status(variant: str):
    st = get_approvals().get(variant)
    return {"variant": variant, "status": (st.status if st else "draft"), "updated_at": (st.updated_at if st else None)}

@app.get("/")
def root():
    return {"ok": True}
