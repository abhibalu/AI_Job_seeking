"""
Database module for storing agent evaluation results.

Supports both SQLite (local) and Supabase (cloud) backends.
Toggle with USE_SUPABASE environment variable.
"""
import json
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.settings import settings

logger = logging.getLogger(__name__)


# ============================================
# BACKEND SELECTION
# ============================================

def _use_supabase() -> bool:
    """Check if Supabase should be used."""
    return settings.USE_SUPABASE and settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY


# ============================================
# SQLITE FUNCTIONS (Original)
# ============================================

def get_db_path() -> Path:
    """Get the database path, creating parent directories if needed."""
    db_path = Path(settings.EVAL_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def get_db_connection() -> sqlite3.Connection:
    """Get a SQLite database connection."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize the SQLite database schema."""
    if _use_supabase():
        logger.info("Using Supabase - SQLite init skipped")
        return
    
    logger.info(f"Using SQLite at {get_db_path()}")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Job evaluations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_evaluations (
            job_id TEXT PRIMARY KEY,
            company_name TEXT,
            title_role TEXT,
            job_url TEXT,
            
            verdict TEXT,
            job_match_score INTEGER,
            summary TEXT,
            required_exp TEXT,
            recommended_action TEXT,
            
            gaps TEXT,
            improvement_suggestions TEXT,
            interview_tips TEXT,
            jd_keywords TEXT,
            matched_keywords TEXT,
            missing_keywords TEXT,
            
            model_used TEXT,
            evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            raw_response TEXT
        )
    """)
    
    # JD parsed signals table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jd_parsed (
            job_id TEXT PRIMARY KEY,
            must_haves TEXT,
            nice_to_haves TEXT,
            domain TEXT,
            seniority TEXT,
            location_constraints TEXT,
            ats_keywords TEXT,
            normalized_skills TEXT,
            
            model_used TEXT,
            parsed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            raw_response TEXT,
            
            FOREIGN KEY (job_id) REFERENCES job_evaluations(job_id)
        )
    """)
    
    # Tasks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            status TEXT,
            progress TEXT,
            error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP
        )
    """)

    # Resumes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id TEXT PRIMARY KEY,
            name TEXT,
            content TEXT,
            is_master BOOLEAN,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tailored Resumes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tailored_resumes (
            id TEXT PRIMARY KEY,
            job_id TEXT,
            version INTEGER,
            content TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES job_evaluations(job_id)
        )
    """)
    
    # Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_eval_verdict ON job_evaluations(verdict)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_eval_score ON job_evaluations(job_match_score)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_eval_action ON job_evaluations(recommended_action)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_status ON tasks(status)")
    
    conn.commit()
    conn.close()
    
    print(f"SQLite database initialized at: {get_db_path()}")


# ============================================
# SUPABASE FUNCTIONS
# ============================================

def _get_supabase():
    """Get Supabase client (lazy import to avoid circular deps)."""
    from agents.supabase_client import get_supabase_client
    return get_supabase_client()


def _ensure_job_exists(job_id: str, company_name: str = "", title: str = "", job_url: str = ""):
    """Ensure a job record exists in the jobs table (for foreign key)."""
    client = _get_supabase()
    
    # Check if job exists
    result = client.table("jobs").select("id").eq("id", job_id).execute()
    
    if not result.data:
        # Insert minimal job record
        client.table("jobs").insert({
            "id": job_id,
            "company_name": company_name,
            "title": title,
            "job_url": job_url,
        }).execute()


# ============================================
# EVALUATION FUNCTIONS
# ============================================

def is_job_evaluated(job_id: str) -> bool:
    """Check if a job has already been evaluated."""
    if _use_supabase():
        client = _get_supabase()
        result = client.table("job_evaluations").select("job_id").eq("job_id", job_id).execute()
        return len(result.data) > 0
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM job_evaluations WHERE job_id = ?", (job_id,))
    result = cursor.fetchone() is not None
    conn.close()
    return result


def get_evaluation(job_id: str) -> dict | None:
    """Get evaluation for a job."""
    if _use_supabase():
        client = _get_supabase()
        result = client.table("job_evaluations").select("*").eq("job_id", job_id).execute()
        if result.data:
            return result.data[0]
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM job_evaluations WHERE job_id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def list_evaluations(skip: int = 0, limit: int = 20, action: str | None = None) -> list[dict]:
    """List evaluations with pagination and filtering."""
    if _use_supabase():
        client = _get_supabase()
        query = client.table("job_evaluations").select("*")
        
        if action:
            query = query.eq("recommended_action", action)
            
        # Supabase range is inclusive
        result = query.order("evaluated_at", desc=True).range(skip, skip + limit - 1).execute()
        return result.data
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM job_evaluations"
    params = []
    
    if action:
        query += " WHERE recommended_action = ?"
        params.append(action)
    
    query += " ORDER BY evaluated_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, skip])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_evaluation_statistics() -> dict:
    """Get evaluation statistics."""
    if _use_supabase():
        client = _get_supabase()
        
        try:
            # Total count (efficient HEAD request)
            total_res = client.table("job_evaluations").select("*", count="exact", head=True).execute()
            total = total_res.count or 0
            
            # Fetch all needed data in ONE query to minimize round-trips
            res = client.table("job_evaluations").select("job_match_score, recommended_action, verdict").execute()
            data = res.data or []
            
            # Average Score
            score_list = [r["job_match_score"] for r in data if r["job_match_score"] is not None]
            avg_score = sum(score_list) / len(score_list) if score_list else 0
            
            # Group by Action
            by_action = {}
            for r in data:
                act = r.get("recommended_action") or "unknown"
                by_action[act] = by_action.get(act, 0) + 1
                
            # Group by Verdict
            by_verdict = {}
            for r in data:
                v = r.get("verdict") or "unknown"
                by_verdict[v] = by_verdict.get(v, 0) + 1
                
        except Exception as e:
            logger.error(f"Failed to fetch stats from Supabase: {e}", exc_info=True)
            # Return empty stats on failure rather than crashing API
            return {
                "total_evaluated": 0,
                "average_score": 0,
                "by_action": {},
                "by_verdict": {},
            }
            
        return {
            "total_evaluated": total,
            "average_score": round(avg_score, 1),
            "by_action": by_action,
            "by_verdict": by_verdict,
        }

    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM job_evaluations")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT AVG(job_match_score) FROM job_evaluations")
    avg_score = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT recommended_action, COUNT(*) FROM job_evaluations GROUP BY recommended_action")
    by_action = dict(cursor.fetchall())
    
    cursor.execute("SELECT verdict, COUNT(*) FROM job_evaluations GROUP BY verdict")
    by_verdict = dict(cursor.fetchall())
    
    conn.close()
    
    return {
        "total_evaluated": total,
        "average_score": round(avg_score, 1),
        "by_action": by_action,
        "by_verdict": by_verdict,
    }


def save_evaluation(result: dict):
    """Save job evaluation to database."""
    job_id = str(result.get("job_id", ""))
    company_name = result.get("company_name", "")
    title_role = result.get("title_role", "")
    job_url = result.get("job_url", "")
    
    if _use_supabase():
        client = _get_supabase()
        
        # Ensure job exists for FK
        _ensure_job_exists(job_id, company_name, title_role, job_url)
        
        data = {
            "job_id": job_id,
            "company_name": company_name,
            "title_role": title_role,
            "job_url": job_url,
            "verdict": result.get("Verdict", result.get("verdict", "")),
            "job_match_score": result.get("job_match_score", 0),
            "summary": result.get("summary", ""),
            "required_exp": result.get("required_exp", ""),
            "recommended_action": result.get("recommended_action", ""),
            "gaps": result.get("gaps", {}),
            "improvement_suggestions": result.get("improvement_suggestions", {}),
            "interview_tips": result.get("interview_tips", {}),
            "jd_keywords": result.get("jd_keywords", []),
            "matched_keywords": result.get("matched_keywords", []),
            "missing_keywords": result.get("missing_keywords", []),
            "model_used": result.get("_model_used", ""),
            "raw_response": result,
            "evaluated_at": datetime.now().isoformat(),
        }
        
        # Upsert (insert or update on conflict)
        client.table("job_evaluations").upsert(
            data,
            on_conflict="job_id"
        ).execute()
        return
    
    # SQLite fallback
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO job_evaluations (
            job_id, company_name, title_role, job_url,
            verdict, job_match_score, summary, required_exp, recommended_action,
            gaps, improvement_suggestions, interview_tips,
            jd_keywords, matched_keywords, missing_keywords,
            model_used, raw_response, evaluated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        job_id,
        company_name,
        title_role,
        job_url,
        result.get("Verdict", result.get("verdict", "")),
        result.get("job_match_score", 0),
        result.get("summary", ""),
        result.get("required_exp", ""),
        result.get("recommended_action", ""),
        json.dumps(result.get("gaps", {})),
        json.dumps(result.get("improvement_suggestions", {})),
        json.dumps(result.get("interview_tips", {})),
        json.dumps(result.get("jd_keywords", [])),
        json.dumps(result.get("matched_keywords", [])),
        json.dumps(result.get("missing_keywords", [])),
        result.get("_model_used", ""),
        json.dumps(result),
        datetime.now()
    ))
    
    conn.commit()
    conn.close()


# ============================================
# JD PARSED FUNCTIONS
# ============================================

def is_job_parsed(job_id: str) -> bool:
    """Check if a job's JD has been parsed."""
    if _use_supabase():
        client = _get_supabase()
        result = client.table("jd_parsed").select("job_id").eq("job_id", job_id).execute()
        return len(result.data) > 0
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM jd_parsed WHERE job_id = ?", (job_id,))
    result = cursor.fetchone() is not None
    conn.close()
    return result


def save_jd_parsed(result: dict):
    """Save JD parsed signals to database."""
    job_id = str(result.get("job_id", ""))
    
    if _use_supabase():
        client = _get_supabase()
        
        # Ensure job exists for FK
        _ensure_job_exists(job_id)
        
        data = {
            "job_id": job_id,
            "must_haves": result.get("must_haves", []),
            "nice_to_haves": result.get("nice_to_haves", []),
            "domain": result.get("domain", ""),
            "seniority": result.get("seniority") if result.get("seniority") in ('junior', 'mid', 'senior', 'lead', 'unspecified') else None,
            "location_constraints": result.get("location_constraints", []),
            "ats_keywords": result.get("ats_keywords", []),
            "normalized_skills": result.get("normalized_skills", {}),
            "model_used": result.get("_model_used", ""),
            "raw_response": result,
            "parsed_at": datetime.now().isoformat(),
        }
        
        # Upsert
        client.table("jd_parsed").upsert(
            data,
            on_conflict="job_id"
        ).execute()
        return
    
    # SQLite fallback
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO jd_parsed (
            job_id, must_haves, nice_to_haves, domain, seniority,
            location_constraints, ats_keywords, normalized_skills,
            model_used, raw_response, parsed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        job_id,
        json.dumps(result.get("must_haves", [])),
        json.dumps(result.get("nice_to_haves", [])),
        result.get("domain", ""),
        result.get("seniority", ""),
        json.dumps(result.get("location_constraints", [])),
        json.dumps(result.get("ats_keywords", [])),
        json.dumps(result.get("normalized_skills", {})),
        result.get("_model_used", ""),
        json.dumps(result),
        datetime.now()
    ))
    
    conn.commit()
    conn.close()


# ============================================
# TASK FUNCTIONS
# ============================================

def list_tasks(limit: int = 20) -> list[dict]:
    """List recent tasks."""
    if _use_supabase():
        client = _get_supabase()
        result = client.table("tasks").select("*").order("created_at", desc=True).limit(limit).execute()
        return result.data
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def save_task_status(task_id: str, status: str, progress: dict | None = None, error: str | None = None):
    """Save or update task status."""
    if _use_supabase():
        client = _get_supabase()
        
        # Check if task exists
        result = client.table("tasks").select("task_id").eq("task_id", task_id).execute()
        
        data = {
            "task_id": task_id,
            "status": status,
            "progress": progress or {},
            "error": error,
        }
        
        if status in ("completed", "failed"):
            data["completed_at"] = datetime.now().isoformat()
        
        if result.data:
            # Update
            client.table("tasks").update(data).eq("task_id", task_id).execute()
        else:
            # Insert
            client.table("tasks").insert(data).execute()
        return
    
    # SQLite fallback
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT 1 FROM tasks WHERE task_id = ?", (task_id,))
    exists = cursor.fetchone() is not None
    
    if exists:
        if status in ("completed", "failed"):
            cursor.execute("""
                UPDATE tasks 
                SET status = ?, progress = ?, error = ?, completed_at = ?
                WHERE task_id = ?
            """, (status, json.dumps(progress) if progress else None, error, datetime.now(), task_id))
        else:
            cursor.execute("""
                UPDATE tasks 
                SET status = ?, progress = ?, error = ?
                WHERE task_id = ?
            """, (status, json.dumps(progress) if progress else None, error, task_id))
    else:
        cursor.execute("""
            INSERT INTO tasks (task_id, status, progress, error)
            VALUES (?, ?, ?, ?)
        """, (task_id, status, json.dumps(progress) if progress else None, error))
    
    conn.commit()
    conn.close()


def get_task_status(task_id: str) -> dict | None:
    """Get task status by ID."""
    if _use_supabase():
        client = _get_supabase()
        result = client.table("tasks").select("*").eq("task_id", task_id).execute()
        if result.data:
            return result.data[0]
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        result = dict(row)
        if result.get("progress"):
            try:
                result["progress"] = json.loads(result["progress"])
            except:
                pass
        return result
    return None


# ============================================
# RESUME FUNCTIONS
# ============================================

def save_resume(content: dict, name: str = "Master Resume", is_master: bool = False):
    """Save parsed resume to database."""
    if _use_supabase():
        client = _get_supabase()
        
        data = {
            "name": name,
            "content": content,
            "is_master": is_master,
            "updated_at": datetime.now().isoformat(),
        }
        
        client.table("resumes").insert(data).execute()
        return

    # SQLite fallback
    conn = get_db_connection()
    cursor = conn.cursor()
    import uuid
    
    cursor.execute("""
        INSERT INTO resumes (id, name, content, is_master, updated_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        str(uuid.uuid4()),
        name,
        json.dumps(content),
        is_master,
        datetime.now()
    ))
    
    conn.commit()
    conn.close()


def get_master_resume() -> dict | None:
    """Get the latest master resume."""
    if _use_supabase():
        client = _get_supabase()
        # Get latest is_master=true
        result = client.table("resumes").select("content").eq("is_master", True).order("created_at", desc=True).limit(1).execute()
        if result.data:
            return result.data[0]["content"]
        return None
        
    # SQLite fallback
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT content FROM resumes 
        WHERE is_master = 1 
        ORDER BY created_at DESC 
        LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()
    
    if row and row[0]:
        try:
            return json.loads(row[0])
        except:
            return None
    return None


# ============================================
# TAILORED RESUME FUNCTIONS
# ============================================

def save_tailored_resume(job_id: str, version: int, content: dict, status: str = "pending") -> str:
    """Save a tailored resume."""
    import uuid
    record_id = str(uuid.uuid4())
    
    if _use_supabase():
        client = _get_supabase()
        
        data = {
            "id": record_id,
            "job_id": job_id,
            "version": version,
            "content": content,
            "status": status,
            "created_at": datetime.now().isoformat(),
        }
        
        client.table("tailored_resumes").insert(data).execute()
        return record_id

    # SQLite fallback
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO tailored_resumes (id, job_id, version, content, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        record_id,
        job_id,
        version,
        json.dumps(content),
        status,
        datetime.now()
    ))
    
    conn.commit()
    conn.close()
    return record_id


def get_tailored_resumes(job_id: str) -> list[dict]:
    """Get all tailored versions for a job."""
    if _use_supabase():
        client = _get_supabase()
        # Explicitly selecting expected columns to avoid issues
        result = client.table("tailored_resumes").select("*").eq("job_id", job_id).order("version", desc=True).execute()
        return result.data

    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM tailored_resumes 
        WHERE job_id = ? 
        ORDER BY version DESC
    """, (job_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for row in rows:
        d = dict(row)
        try:
            d["content"] = json.loads(d["content"])
        except:
            pass
        results.append(d)
    return results


def update_tailored_resume_status(record_id: str, status: str):
    """Update status (approved/rejected)."""
    if _use_supabase():
        client = _get_supabase()
        client.table("tailored_resumes").update({"status": status}).eq("id", record_id).execute()
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tailored_resumes SET status = ? WHERE id = ?", (status, record_id))
    conn.commit()
    conn.close()


def get_jd_parsed(job_id: str) -> dict | None:
    """Get parsed signals for a job."""
    if _use_supabase():
        client = _get_supabase()
        result = client.table("jd_parsed").select("*").eq("job_id", job_id).execute()
        if result.data:
            return result.data[0]
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jd_parsed WHERE job_id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        result = dict(row)
        # Parse JSON fields
        for f in ["must_haves", "nice_to_haves", "ats_keywords", "normalized_skills"]:
             if result.get(f):
                 try:
                     result[f] = json.loads(result[f])
                 except:
                     pass
        return result
    return None
