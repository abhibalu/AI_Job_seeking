"""
Pydantic schemas for API request/response models.
"""
from datetime import datetime
from pydantic import BaseModel


# Job schemas
class JobBase(BaseModel):
    id: str
    title: str | None = None
    company_name: str | None = None
    location: str | None = None
    posted_at: str | None = None
    applicants_count: int | None = None


class JobDetail(JobBase):
    description_text: str | None = None
    seniority_level: str | None = None
    employment_type: str | None = None
    link: str | None = None
    company_website: str | None = None


class JobStats(BaseModel):
    total_jobs: int
    unique_companies: int
    top_companies: list[dict]


# Evaluation schemas
class EvaluationResult(BaseModel):
    job_id: str
    company_name: str | None = None
    title_role: str | None = None
    verdict: str | None = None
    job_match_score: int | None = None
    summary: str | None = None
    required_exp: str | None = None
    recommended_action: str | None = None
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
