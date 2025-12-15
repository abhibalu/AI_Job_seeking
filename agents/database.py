"""
SQLite database for storing agent evaluation results.
"""
import sqlite3
from pathlib import Path

from backend.settings import settings


def get_db_path() -> Path:
    """Get the database path, creating parent directories if needed."""
    db_path = Path(settings.EVAL_DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


def get_db_connection() -> sqlite3.Connection:
    """Get a database connection."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize the database schema."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Job evaluations table (Agent 1)
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
    
    # JD parsed signals table (Agent 2)
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
    
    # Tasks table for async operations
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
    
    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_eval_verdict ON job_evaluations(verdict)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_eval_score ON job_evaluations(job_match_score)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_eval_action ON job_evaluations(recommended_action)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_status ON tasks(status)")
    
    conn.commit()
    conn.close()
    
    print(f"Database initialized at: {get_db_path()}")


def is_job_evaluated(job_id: str) -> bool:
    """Check if a job has already been evaluated."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM job_evaluations WHERE job_id = ?", (job_id,))
    result = cursor.fetchone() is not None
    conn.close()
    return result


def is_job_parsed(job_id: str) -> bool:
    """Check if a job's JD has been parsed."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM jd_parsed WHERE job_id = ?", (job_id,))
    result = cursor.fetchone() is not None
    conn.close()
    return result


def get_evaluation(job_id: str) -> dict | None:
    """Get evaluation for a job."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM job_evaluations WHERE job_id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def save_evaluation(result: dict):
    """Save job evaluation to database."""
    import json
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO job_evaluations (
            job_id, company_name, title_role, job_url,
            verdict, job_match_score, summary, required_exp, recommended_action,
            gaps, improvement_suggestions, interview_tips,
            jd_keywords, matched_keywords, missing_keywords,
            model_used, raw_response
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(result.get("job_id", "")),
        result.get("company_name", ""),
        result.get("title_role", ""),
        result.get("job_url", ""),
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
    ))
    
    conn.commit()
    conn.close()


def save_jd_parsed(result: dict):
    """Save JD parsed signals to database."""
    import json
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO jd_parsed (
            job_id, must_haves, nice_to_haves, domain, seniority,
            location_constraints, ats_keywords, normalized_skills,
            model_used, raw_response
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(result.get("job_id", "")),
        json.dumps(result.get("must_haves", [])),
        json.dumps(result.get("nice_to_haves", [])),
        result.get("domain", ""),
        result.get("seniority", ""),
        json.dumps(result.get("location_constraints", [])),
        json.dumps(result.get("ats_keywords", [])),
        json.dumps(result.get("normalized_skills", {})),
        result.get("_model_used", ""),
        json.dumps(result),
    ))
    
    conn.commit()
    conn.close()


def save_task_status(task_id: str, status: str, progress: dict | None = None, error: str | None = None):
    """Save or update task status."""
    import json
    from datetime import datetime
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if task exists
    cursor.execute("SELECT 1 FROM tasks WHERE task_id = ?", (task_id,))
    exists = cursor.fetchone() is not None
    
    if exists:
        # Update existing task
        if status == "completed" or status == "failed":
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
        # Insert new task
        cursor.execute("""
            INSERT INTO tasks (task_id, status, progress, error)
            VALUES (?, ?, ?, ?)
        """, (task_id, status, json.dumps(progress) if progress else None, error))
    
    conn.commit()
    conn.close()
