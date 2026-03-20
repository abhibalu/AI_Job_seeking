"""
Pydantic schemas for API request/response models.
"""
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import List, Literal, Optional


# Job schemas
class JobBase(BaseModel):
    id: str
    title: str | None = None
    company_name: str | None = None
    location: str | None = None
    posted_at: str | None = None
    applicants_count: int | None = None
    company_website: str | None = None
    job_url: str | None = None
    updated_at: str | None = None
    salary_info: str | None = None
    tailoring_status: Literal['not_started', 'processing', 'ready', 'cancelled', 'needs_review'] | None = None


class JobDetail(JobBase):
    description_text: str | None = None
    description_html: str | None = None
    seniority_level: str | None = None
    employment_type: str | None = None
    # link field removed as it's now job_url in JobBase

    
    # New Fields from Supabase
    status: str | None = None
    job_function: str | list | dict | None = None
    industries: str | list | dict | None = None
    salary_info: str | None = None
    benefits: list | dict | None = None
    
    # Company Details
    company_linkedin_url: str | None = None
    company_logo: str | None = None
    company_description: str | None = None
    company_slogan: str | None = None
    company_employees_count: int | None = None
    company_city: str | None = None
    company_country: str | None = None
    
    # Poster
    job_poster_name: str | None = None
    job_poster_profile_url: str | None = None
    
    # URLs
    apply_url: str | None = None
    input_url: str | None = None

    # OotoCV: cover letter (AI-generated, user-editable)
    cover_letter: str | None = None


class JobStats(BaseModel):
    total_jobs: int
    unique_companies: int
    top_companies: list[dict]


class DeleteRequest(BaseModel):
    ids: list[str]

# Evaluation schemas
class EvaluationResult(BaseModel):
    job_id: str
    job_url: str | None = None
    company_name: str | None = None
    company_website: str | None = None
    title_role: str | None = None
    verdict: str | None = None
    job_match_score: int | None = None
    summary: str | None = None
    required_exp: str | None = None
    recommended_action: str | None = None
    wit_line: str | None = None
    recruiter_email: str | None = None
    gaps: dict | None = None
    improvement_suggestions: dict | None = None
    interview_tips: dict | None = None
    jd_keywords: list[str] | None = None
    matched_keywords: list[str] | None = None
    missing_keywords: list[str] | None = None
    evaluated_at: datetime | None = None


class EvaluationStats(BaseModel):
    total_evaluated: int
    average_score: float
    by_action: dict[str, int]
    by_verdict: dict[str, int]


# Parse schemas
class ParseResult(BaseModel):
    job_id: str
    must_haves: list[str] | None = None
    nice_to_haves: list[str] | None = None
    domain: str | None = None
    seniority: str | None = None
    ats_keywords: list[str] | None = None
    normalized_skills: dict | None = None
    parsed_at: datetime | None = None


# Batch schemas
class BatchRequest(BaseModel):
    max_jobs: int = 10
    only_unevaluated: bool = True
    company_filter: str | None = None


class TaskStatus(BaseModel):
    task_id: str
    status: str  # queued, running, completed, failed
    progress: dict | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


# Generic responses
class MessageResponse(BaseModel):
    message: str
    job_id: str | None = None
    task_id: str | None = None


# Resume Data Schemas (For Typst generation)
class Experience(BaseModel):
    id: str
    company: str
    role: str
    period: str
    location: Optional[str] = ""
    achievements: List[str] = []

class Education(BaseModel):
    id: str
    institution: str
    degree: str
    period: str
    location: Optional[str] = ""
    score: Optional[str] = None

class GDocImportRequest(BaseModel):
    document_id: str  # The Google Doc ID from the URL


# JSON Resume validation schemas (for LLM output validation)
class JSONResumeBasics(BaseModel):
    name: str
    label: str = ""
    email: str = ""
    phone: str = ""
    summary: str = ""
    location: dict | str = {}
    profiles: list[dict] = []

    model_config = ConfigDict(extra="allow")


class JSONResumeWork(BaseModel):
    name: str
    position: str
    startDate: str = ""
    endDate: str = "Present"
    summary: str = ""
    highlights: list[str] = []

    model_config = ConfigDict(extra="allow")


class JSONResumeEducation(BaseModel):
    institution: str
    studyType: str = ""
    area: str = ""
    startDate: str = ""
    endDate: str = ""
    score: str = ""

    model_config = ConfigDict(extra="allow")


class JSONResumeSkill(BaseModel):
    name: str
    keywords: list[str] = []

    model_config = ConfigDict(extra="allow")


class JSONResumeSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    basics: JSONResumeBasics
    work: list[JSONResumeWork] = []
    education: list[JSONResumeEducation] = []
    skills: list[JSONResumeSkill] = []


class ResumeData(BaseModel):
    fullName: str
    title: Optional[str] = ""
    phone: str
    email: str
    location: str
    websites: List[str] = []
    summary: Optional[str] = ""
    experience: List[Experience] = []
    education: List[Education] = []
    skills: List[str] = []


# OotoCV: per-change review schema (ADR-0010)
class ResumeChange(BaseModel):
    id: str
    resume_id: str
    job_id: str
    location: str
    action_type: Literal['rephrase', 'add', 'remove']
    original_text: str | None = None   # immutable pre-AI text; None for 'add' actions
    tailored_text: str | None = None   # AI output
    accepted_text: str | None = None   # final value; None = not yet reviewed
    review_action: Literal['accept', 'reject', 'keep_original'] | None = None
    reason: str | None = None
    confidence: float | None = None
    approved_source: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ResumeChangeActionRequest(BaseModel):
    action: Literal['accept', 'reject', 'keep_original']


class ResumeChangeBulkActionRequest(BaseModel):
    action: Literal['accept', 'reject', 'keep_original']
    scope: Literal['remaining', 'all'] = 'remaining'


# OotoCV: system config schema (cron_tz, auto_send_threshold)
class SystemConfigItem(BaseModel):
    key: str
    value: str


class ServiceTogglesResponse(BaseModel):
    openrouter: bool
    apify: bool
    google_docs: bool


class ServiceTogglesUpdate(BaseModel):
    openrouter: bool | None = None
    apify: bool | None = None
    google_docs: bool | None = None


class CronConfigRequest(BaseModel):
    cron_time: str          # HH:MM
    cron_tz: str            # IANA timezone (e.g. "Europe/Dublin")


# OotoCV: GDoc export result schema (Layer 4)
class ExportSkippedField(BaseModel):
    section: str
    reason: str


class ExportResultSummary(BaseModel):
    total: int
    applied: int
    skipped: int


class ExportResultResponse(BaseModel):
    status: Literal['success', 'partial', 'failed', 'no_changes']
    url: str
    path: Literal['copy_and_fill', 'plain_text']
    summary: ExportResultSummary | None = None
    skipped_fields: list[ExportSkippedField] | None = None
