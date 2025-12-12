"""
Job Evaluator Agent - Compares resume with job description.

Returns match score, verdict, gaps, and recommendations.
"""
import json
from pathlib import Path

from .base import BaseAgent


class JobEvaluatorAgent(BaseAgent):
    """Agent that evaluates job-resume fit."""
    
    def __init__(self, model: str | None = None):
        super().__init__(model=model, temperature=0.3)
        self._load_resume()
        self._load_approved_skills()
    
    def _load_resume(self):
        """Load base resume from JSON file."""
        resume_path = Path("agent_prompts/base_resume.json")
        if resume_path.exists():
            with open(resume_path) as f:
                self.resume = json.load(f)
        else:
            raise FileNotFoundError(f"Resume not found: {resume_path}")
    
    def _load_approved_skills(self):
        """Load approved skills from markdown file."""
        skills_path = Path("agent_prompts/approved_skills.md")
        if skills_path.exists():
            with open(skills_path) as f:
                self.approved_skills = f.read()
        else:
            self.approved_skills = ""
    
    def get_system_prompt(self) -> str:
        return """You are an AI Job Match Evaluator Agent.

Your task: Compare the candidate's resume with a given job description and return **exactly one valid JSON object** that includes:
- Company and role information
- Job description summary
- Alignment verdict and numeric score
- Detailed gaps categorized by type (for interview prep)
- Actionable improvement suggestions grounded in approved skills/projects
- Interview preparation tips based on JD emphasis
- Recruiter contact and metadata

You may reason privately but **must not output your thoughts**.

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

## EXPERIENCE FIT RULE

If the JD requires more than 5 years of experience, set:
- recommended_action: "skip"
- Reduce job_match_score by at least 20 points

The candidate has only 3-5 years of professional experience.

## recommended_action LOGIC

- "skip": required_exp > 6 years OR job_match_score < 50
- "tailor": job_match_score 50-79 AND required_exp <= 5 years
- "apply": job_match_score >= 80 AND required_exp <= 5 years

## STRICT OUTPUT RULES

- Return ONLY the JSON object
- No markdown, no code fences, no explanations
- Use valid JSON with double quotes
- Keep values single-line"""
    
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
