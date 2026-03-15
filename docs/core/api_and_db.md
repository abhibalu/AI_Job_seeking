# TailorAI Technical Resources

This document serves as a centralized reference for the current Backend Database Schema (Supabase) and active API Endpoints used throughout the application.

## 1. Database Schema (Supabase)
TailorAI uses Supabase PostgreSQL for persistent state. Below are the key tables managed via `agents/database.py`.

### 1.1 `jobs`
Stores basic metadata about a job description evaluated by the user.
- `id` (PK, String): Unique Job ID assigned by the frontend.
- `company_name` (String): Company Name.
- `title` (String): Role Title.
- `job_url` (String): Original posting URL.

### 1.2 `job_evaluations`
Stores the output of the `JobEvaluatorAgent`.
- `job_id` (PK, FK to jobs): The associated job.
- `verdict` / `job_match_score` / `recommended_action`: High-level evaluation metrics.
- `gaps` / `improvement_suggestions` / `interview_tips` (JSON Text): Structured feedback arrays.
- `jd_keywords` / `matched_keywords` / `missing_keywords` (JSON Text): Keyword overlap analysis.
- `raw_response` (JSON Text): Full raw output from the LLM.

### 1.3 `jd_parsed`
Stores the output of the `JDParserAgent`.
- `job_id` (PK, FK to jobs): The associated job.
- `must_haves` / `nice_to_haves` / `ats_keywords` (JSON Text): Extracted ATS signals.
- `location_constraints` / `domain` / `seniority`: Job metadata semantics.

### 1.4 `resumes`
Unified table storing both the *Master* Base Resume and specifically *Tailored* versions.
- `id` (PK, UUID String): Unique identifier for the resume instance.
- `status` (String): Indicated state (`master`, `pending`, `approved`, `rejected`).
- `job_id` (FK to jobs, Nullable): Only populated if this is a Tailored resume meant for a specific job.
- `version` (Integer, Nullable): Iteration number for tailored resumes (corresponds to LangGraph revision count).
- `content` (JSON Text): The actual Resume payload stored in the standardized *JSON Resume* schema format.

---

## 2. API Endpoints (`api/routes/resumes.py`)
These are the primary routes managing the resume lifecycle, exposed via FastAPI.

### 2.1 Master Resume Routes
- **`GET /api/resumes/master`**
  - Fetches the latest resume where `status='master'` from the `resumes` table.
  - Automatically translates it from *JSON Resume* format to the specific Frontend UI format.
- **`POST /api/resumes/master`**
  - Accepts Frontend UI JSON format, translates it back to JSON Resume schema, and inserts a new row with `status='master'`.
- **`POST /api/resumes/upload`**
  - Accepts a PDF file, extracts raw text via `pdfplumber`, saves a temporary `status='processing'` state, and triggers `ResumeParserAgent` in the background.

### 2.2 Tailoring Routes
- **`POST /api/resumes/tailor/{job_id}`**
  - The core LangGraph endpoint.
  - Fetches the latest Master Resume, parses JD context (`get_evaluation`, `get_jd_parsed`), and invokes `tailoring_subgraph.py`.
  - Blocks until the subgraph completes, then returns the newly generated tailored resume JSON.
- **`GET /api/resumes/tailored/{job_id}`**
  - Fetches all iterations of tailored resumes specific to a `job_id`.
- **`POST /api/resumes/tailored/{record_id}/status`**
  - Updates the `status` column (e.g., changing from `pending` to `approved` or `rejected`).

### 2.3 Export Routes
- **`POST /api/resumes/export-gdoc/{job_id}`**
  - Fetches the latest tailored resume for the `job_id`.
  - Calls `services/google_docs.py` to authenticate and either create or overwrite a matching Google Doc.
  - Returns the live URL to the Google Doc.
