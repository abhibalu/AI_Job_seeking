"""
Job Evaluator Agent - Compares resume with job description.

Returns match score, verdict, gaps, and recommendations.
"""
import json
import logging
from pathlib import Path

from .base import BaseAgent
from agents.database import get_master_resume
from backend.settings import settings

logger = logging.getLogger(__name__)


class JobEvaluatorAgent(BaseAgent):
    """Agent that evaluates job-resume fit."""
    
    def __init__(self, model: str | None = None):
        super().__init__(model=model, temperature=0.3)
        self._load_resume()
        self._load_approved_skills()
    
    def _load_resume(self):
        """Load base resume from DB (preferred) or JSON file."""
        # 1. Try DB
        try:
            db_resume = get_master_resume()
            if db_resume:
                self.resume = self._normalize_resume(db_resume)
                return
        except Exception as e:
            logger.warning(f"Failed to load resume from DB: {e}")

        # 2. Fallback to file
        resume_path = Path("agent_prompts/base_resume.json")
        if resume_path.exists():
            with open(resume_path) as f:
                self.resume = self._normalize_resume(json.load(f))
        else:
            raise FileNotFoundError(f"Resume not found in DB or at {resume_path}")
    
    def _normalize_resume(self, resume: dict) -> dict:
        """Normalize resume to JSON Resume format.
        
        Handles both:
        - Frontend format: fullName, experience, etc.
        - JSON Resume format: basics, work, etc.
        """
        # If already in JSON Resume format, return as-is
        if "basics" in resume and "work" in resume:
            return resume
        
        # Transform frontend format to JSON Resume format
        normalized = {}
        
        # Map basics
        normalized["basics"] = {
            "name": resume.get("fullName", ""),
            "label": resume.get("title", ""),
            "email": resume.get("email", ""),
            "phone": resume.get("phone", ""),
            "location": {"city": resume.get("location", "")},
            "summary": resume.get("summary", ""),
            "profiles": [{"url": url} for url in resume.get("websites", [])]
        }
        
        # Map work experience
        normalized["work"] = []
        for exp in resume.get("experience", []):
            normalized["work"].append({
                "id": exp.get("id", ""),
                "name": exp.get("company", ""),
                "position": exp.get("role", ""),
                "location": exp.get("location", ""),
                "startDate": exp.get("period", "").split(" - ")[0] if " - " in exp.get("period", "") else exp.get("period", ""),
                "endDate": exp.get("period", "").split(" - ")[1] if " - " in exp.get("period", "") else "",
                "highlights": exp.get("achievements", [])
            })
        
        # Map education
        normalized["education"] = []
        for edu in resume.get("education", []):
            normalized["education"].append({
                "id": edu.get("id", ""),
                "institution": edu.get("institution", ""),
                "studyType": edu.get("degree", ""),
                "area": "",
                "endDate": edu.get("period", ""),
                "location": edu.get("location", ""),
                "score": edu.get("score", "")
            })
        
        # Map skills (already strings in frontend format)
        normalized["skills"] = resume.get("skills", [])
        
        logger.info(f"Normalized resume from frontend format. Work entries: {len(normalized['work'])}")
        return normalized
    
    def _load_approved_skills(self):
        """Load approved skills from markdown file."""
        skills_path = Path("agent_prompts/approved_skills.md")
        if skills_path.exists():
            with open(skills_path) as f:
                self.approved_skills = f.read()
        else:
            self.approved_skills = ""
    
    def get_system_prompt(self) -> str:
        prompt_intro = f"""You are an AI Job Match Evaluator Agent.

Your task: Compare the candidate's resume with a given job description and return **exactly one valid JSON object**.

## CANDIDATE EXPERIENCE
- The candidate has **{settings.CANDIDATE_EXPERIENCE_YEARS}** of total experience.
- Assume this experience is relevant unless the job is in a completely different domain requiring zero overlap with the candidate's skills.

## EXPERIENCE FIT RULE
- Compare **{settings.CANDIDATE_EXPERIENCE_YEARS}** to the JD's requirement.
- If **{settings.CANDIDATE_EXPERIENCE_YEARS} < JD Required Years**, set recommended_action: "skip" and penalize the score significantly."""

        prompt_schema = """

## OUTPUT FORMAT (JSON ONLY)

Return one JSON object with exactly these keys:

{
  "job_id": "string",
  "company_name": "string",
  "title_role": "string",
  "recruiter_email": "string or Unknown",
  "JD": "50–100 word summary of the job description",
  "Verdict": "Strong Match | Moderate Match | Weak Match",
  "job_match_score": 10 | 20 | 30 | 40 | 50 | 60 | 70 | 80 | 90 | 100,
  "summary": "2–3 sentences summarizing how the resume aligns with the JD",
  "required_exp": "string (e.g., '5+ years', 'at least 3 years', 'Unknown')",
  
  "gaps": {
    "technical": ["specific tech stack gaps"],
    "domain": ["domain/industry knowledge gaps"],
    "soft_skills": ["leadership, communication, or soft skill gaps"]
  },
  
  "improvement_suggestions": {
    "resume_edits": [
      {
        "area": "work.metro.highlights[4]",
        "suggestion": "Specific actionable edit",
        "approved_reference": "Reference to approved skills/projects doc"
      }
    ],
    "interview_prep": ["Study suggestion 1", "Study suggestion 2"]
  },
  
  "interview_tips": {
    "high_priority_topics": [
      {
        "topic": "Topic name",
        "why": "Why it's important",
        "prep": "Specific prep actions"
      }
    ],
    "your_strengths_to_highlight": ["Strength 1", "Strength 2"],
    "questions_to_ask": ["Smart question 1", "Smart question 2"]
  },
  
  "recommended_action": "apply | tailor | skip",
  "jd_keywords": ["keyword1", "keyword2"],
  "matched_keywords": ["keyword1"],
  "missing_keywords": ["keyword2"],
  
  "posted_date": "YYYY-MM-DD or Unknown",
  "application_deadline": "YYYY-MM-DD or Unknown",
  "job_url": "string or Unknown"
}

## SCORING RULES

1. Start from 50 points
2. Add +10 for each strong overlap (title match, tech stack overlap, etc.)
3. Subtract -10 for each major gap (missing must-have, experience mismatch)
4. Clamp score between 10 and 100

Verdict mapping:
- Strong Match: >= 80
- Moderate Match: 50-70
- Weak Match: <= 40

## recommended_action LOGIC

- "skip": Relevant Exp < Required Exp OR job_match_score < 50
- "tailor": job_match_score 50-79 AND Relevant Exp >= Required Exp
- "apply": job_match_score >= 80 AND Relevant Exp >= Required Exp

## STRICT OUTPUT RULES

- Return ONLY the JSON object
- No markdown, no code fences, no explanations
- Use valid JSON with double quotes
- Keep values single-line"""

        return prompt_intro + prompt_schema
    
    def build_user_prompt(self, job_id: str, description_text: str, 
                          company_name: str = "Unknown", 
                          title: str = "Unknown",
                          job_url: str = "Unknown") -> str:
        resume_str = json.dumps({
            "basics": self.resume.get("basics", {}),
            "work": self.resume.get("work", []),
            "education": self.resume.get("education", []),
            "skills": self.resume.get("skills", []),
        }, indent=2)
        
        return f"""## INPUTS

**Resume**:
```json
{resume_str}
```

**Approved Skills and Projects**:
```
{self.approved_skills}
```

**Job ID**: {job_id}
**Company**: {company_name}
**Title/Role**: {title}
**Job URL**: {job_url}

**Job Description**:
{description_text}

Return the evaluation JSON now."""
