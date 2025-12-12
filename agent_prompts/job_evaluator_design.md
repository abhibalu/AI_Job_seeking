# Job Evaluator Agent - Design Document

## Overview

A Python-based AI agent that evaluates job descriptions against a base resume, providing match scores, gap analysis, and actionable recommendations using OpenRouter LLM API.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           JOB EVALUATOR AGENT                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌───────────────┐     ┌───────────────┐     ┌───────────────────┐    │
│   │ Gold Delta    │────▶│ Job Evaluator │────▶│ SQLite            │    │
│   │ (1 job/call)  │     │ (OpenRouter)  │     │ job_evaluations   │    │
│   └───────────────┘     └───────────────┘     └───────────────────┘    │
│                                │                                        │
│                    ┌───────────┴───────────┐                           │
│                    ▼                       ▼                           │
│           ┌───────────────┐       ┌───────────────┐                    │
│           │ base_resume   │       │ approved_     │                    │
│           │ .json         │       │ skills.md     │                    │
│           └───────────────┘       └───────────────┘                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Processing | 1 job per request | Avoid context overflow on smaller models |
| Storage | SQLite (local) | Zero setup, migrate to PostgreSQL later |
| Model | OpenRouter free/cheap | Flexible model switching via config |
| Pre-filtering | None | Let LLM decide; titles vary across orgs |
| Prompt | Detailed/structured | Prevents hallucination with smaller models |

---

## Input Files

| File | Purpose |
|------|---------|
| `base_resume.json` | Candidate's master resume (JSON Resume format) |
| `approved_skills.md` | Additional verified skills/projects for resume edits |

---

## SQLite Schema

```sql
CREATE TABLE job_evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT UNIQUE NOT NULL,
    
    -- Job info
    company_name TEXT,
    title_role TEXT,
    job_url TEXT,
    
    -- Evaluation results
    verdict TEXT,  -- Strong/Moderate/Weak Match
    job_match_score INTEGER,  -- 0-100
    summary TEXT,
    required_exp TEXT,
    recommended_action TEXT,  -- apply/tailor/skip
    
    -- Detailed analysis (JSON strings)
    gaps TEXT,  -- JSON
    improvement_suggestions TEXT,  -- JSON
    interview_tips TEXT,  -- JSON
    jd_keywords TEXT,  -- JSON
    matched_keywords TEXT,  -- JSON
    missing_keywords TEXT,  -- JSON
    
    -- Metadata
    model_used TEXT,
    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    raw_response TEXT  -- Full JSON for debugging
);

CREATE INDEX idx_job_id ON job_evaluations(job_id);
CREATE INDEX idx_verdict ON job_evaluations(verdict);
CREATE INDEX idx_score ON job_evaluations(job_match_score);
```

---

## Processing Flow

```
1. Initialize SQLite database (create if not exists)
2. Load base_resume.json + approved_skills.md
3. Query Gold Delta for unevaluated jobs
4. For each job:
   a. Check if already evaluated (skip if yes)
   b. Build prompt with resume + JD + approved skills
   c. Call OpenRouter API (free/cheap model)
   d. Parse JSON response
   e. Insert into SQLite
   f. Wait 1 second (rate limiting)
5. Report summary (evaluated, skipped, failed)
```

---

## Configuration (settings.py)

```python
# OpenRouter
OPENROUTER_API_KEY: str
OPENROUTER_MODEL: str = "openai/gpt-4o-mini"  # or free models
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

# Evaluation settings
EVAL_DELAY_SECONDS: float = 1.0
EVAL_MAX_JOBS_PER_RUN: int = 50

# Database
EVAL_DB_PATH: str = "data/job_evaluations.db"
```

---

## File Structure

```
TailorAI/
├── agent_prompts/
│   ├── job_evaluator.md          # System prompt
│   ├── approved_skills.md        # Verified skills list
│   ├── base_resume.json          # Master resume
│   └── job_evaluator_design.md   # This document
├── agents/
│   ├── __init__.py
│   └── job_evaluator.py          # Main agent code
├── data/
│   └── job_evaluations.db        # SQLite database
└── ...
```

---

## Ready for Implementation

**Next steps:**
1. ✅ Design approved (this document)
2. Create `agents/job_evaluator.py`
3. Add OpenRouter config to `settings.py`
4. Test with 1-2 jobs
5. Run batch evaluation
