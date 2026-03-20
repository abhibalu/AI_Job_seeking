"""
Job Evaluator Agent - Compares resume with job description.

Returns match score, verdict, gaps, and recommendations.
"""
import json
import logging
from pathlib import Path

from .base import BaseAgent
from agents.database import get_master_resume

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
            logger.warning("Failed to load resume from DB: %s", e, exc_info=True)

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
        prompt_intro = """You are a rigorous technical hiring consultant specialising in data engineering roles across EU and US markets. You have evaluated thousands of applications and understand that an inflated match score has a direct human cost — a candidate submits to a role they will be screened out of in round one, wasting their application and signalling poor self-awareness to the recruiter.

Your professional standard is precision over encouragement. When fit is borderline, score conservatively. A well-calibrated skip is more valuable to the candidate than a false tailor.

Your task: Compare the candidate's resume with a given job description and return exactly one valid JSON object.

## EXPERIENCE FIT RULE
- Derive the candidate's total experience from the resume work history.
- If candidate experience < JD required years, set recommended_action: "skip" and penalize the score significantly."""

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
  "wit_line": "3–5 word punchy quip about this role (e.g. 'Exactly your stack', 'Worth the stretch', 'Pass on this one')",
  "jd_keywords": ["keyword1", "keyword2"],
  "matched_keywords": ["keyword1"],
  "missing_keywords": ["keyword2"],
  
  "posted_date": "YYYY-MM-DD or Unknown",
  "application_deadline": "YYYY-MM-DD or Unknown",
  "job_url": "string or Unknown"
}

## SCORING

Score on a scale of 10–100 (multiples of 10). Calibrate against the reference examples in the user message — those anchors define what a 30 (two variants: experience skip vs stack skip), a 45, a 60, and an 85 look like. Do not calculate mechanically; assess holistically relative to those reference points.

Verdict mapping:
- Strong Match: ≥ 80
- Moderate Match: 50–79
- Weak Match: ≤ 49

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
        
        anchors = """
## SCORING REFERENCE EXAMPLES

Use these anchors to calibrate your score. They define the scale — do not deviate from these reference points.

### Anchor 1 — Strong Match (score: 85, recommended_action: "apply")
Role: Data Engineer, 3–5yr required, GCP stack (BigQuery, dbt, Airflow, Python, Cloud Composer), FinTech SaaS domain.
Candidate: 4yr experience, all core stack present, FinTech domain overlap, right seniority.
```json
{"job_id":"anchor-1","company_name":"FinTech Co","title_role":"Data Engineer","recruiter_email":"Unknown","JD":"Data Engineer role at FinTech SaaS company requiring 3–5yr experience with GCP stack: BigQuery, dbt, Airflow, Python, Cloud Composer. Build and maintain data pipelines for financial reporting.","Verdict":"Strong Match","job_match_score":85,"summary":"Candidate meets the experience threshold and matches the full GCP stack. FinTech domain overlap strengthens fit. No significant gaps.","required_exp":"3–5 years","gaps":{"technical":[],"domain":[],"soft_skills":[]},"improvement_suggestions":{"resume_edits":[],"interview_prep":["Brush up on Cloud Composer orchestration patterns","Review BigQuery cost optimisation"]},"interview_tips":{"high_priority_topics":[{"topic":"dbt modelling","why":"Core to role","prep":"Review incremental models and testing strategies"}],"your_strengths_to_highlight":["Full GCP stack coverage","FinTech domain experience"],"questions_to_ask":["What does the data team structure look like?","How mature is the dbt project?"]},"recommended_action":"apply","wit_line":"Exactly your stack","jd_keywords":["BigQuery","dbt","Airflow","Python","Cloud Composer"],"matched_keywords":["BigQuery","dbt","Airflow","Python","Cloud Composer"],"missing_keywords":[],"posted_date":"Unknown","application_deadline":"Unknown","job_url":"Unknown"}
```

### Anchor 2 — Moderate Match (score: 60, recommended_action: "tailor")
Role: Data Engineer, 4yr required, AWS-heavy (Redshift, Glue, Step Functions, dbt, Python), E-commerce domain.
Candidate: 5yr experience, strong dbt + Python + Airflow — but no AWS-native services.
```json
{"job_id":"anchor-2","company_name":"E-Commerce Ltd","title_role":"Data Engineer","recruiter_email":"Unknown","JD":"Data Engineer at E-commerce company requiring 4yr experience with AWS stack: Redshift, Glue, Step Functions, dbt, Python. Design and maintain ELT pipelines for retail analytics.","Verdict":"Moderate Match","job_match_score":60,"summary":"Candidate exceeds the experience threshold and has strong transferable skills in dbt and Python. However, they lack AWS-native services (Redshift, Glue, Step Functions) which are core to this role.","required_exp":"4 years","gaps":{"technical":["Redshift","AWS Glue","Step Functions"],"domain":["E-commerce retail analytics"],"soft_skills":[]},"improvement_suggestions":{"resume_edits":[{"area":"work highlights","suggestion":"Frame Airflow experience as transferable to Step Functions orchestration","approved_reference":"Approved doc: Cloud & Storage lists AWS; Notable Projects includes Teradata-to-BigQuery Warehouse Modernization with parallel ELT pipelines in Airflow"}],"interview_prep":["Study Redshift vs Snowflake differences","Review AWS Glue ETL patterns"]},"interview_tips":{"high_priority_topics":[{"topic":"AWS data stack","why":"Core platform gap","prep":"Complete AWS Data Analytics specialty overview"}],"your_strengths_to_highlight":["dbt expertise","Python data pipeline experience"],"questions_to_ask":["Is there an expectation to ramp up on AWS quickly?","How much greenfield vs maintenance work?"]},"recommended_action":"tailor","wit_line":"Worth the stretch","jd_keywords":["Redshift","Glue","Step Functions","dbt","Python"],"matched_keywords":["dbt","Python"],"missing_keywords":["Redshift","Glue","Step Functions"],"posted_date":"Unknown","application_deadline":"Unknown","job_url":"Unknown"}
```

### Anchor 3 — Experience Skip (score: 30, recommended_action: "skip")
Role: Senior Data Engineer, 7yr required, GCP stack (BigQuery, dbt, Airflow). Candidate has the full stack but only 3yr experience — experience threshold failure in isolation.
```json
{"job_id":"anchor-3","company_name":"Scale-Up Corp","title_role":"Senior Data Engineer","recruiter_email":"Unknown","JD":"Senior Data Engineer requiring 7+ years of experience with GCP stack: BigQuery, dbt, Airflow. Lead data infrastructure design and mentor junior engineers.","Verdict":"Weak Match","job_match_score":30,"summary":"Candidate matches the technical stack but has only 3 years of experience against a 7-year requirement. The seniority gap is too large to bridge with tailoring.","required_exp":"7+ years","gaps":{"technical":[],"domain":[],"soft_skills":["Senior leadership","Mentoring experience"]},"improvement_suggestions":{"resume_edits":[],"interview_prep":[]},"interview_tips":{"high_priority_topics":[],"your_strengths_to_highlight":["GCP stack coverage"],"questions_to_ask":[]},"recommended_action":"skip","wit_line":"Not yet","jd_keywords":["BigQuery","dbt","Airflow","senior","7 years"],"matched_keywords":["BigQuery","dbt","Airflow"],"missing_keywords":["7 years experience","senior leadership"],"posted_date":"Unknown","application_deadline":"Unknown","job_url":"Unknown"}
```

### Anchor 4 — Stack Skip (score: 30, recommended_action: "skip")
Role: ML Platform Engineer, 5yr required, Kafka + Spark + Flink + Kubernetes + MLflow, real-time ML inference domain. Candidate meets experience years but stack is completely wrong.
```json
{"job_id":"anchor-4","company_name":"ML Infra Inc","title_role":"ML Platform Engineer","recruiter_email":"Unknown","JD":"ML Platform Engineer requiring 5yr experience with Kafka, Spark, Flink, Kubernetes, and MLflow. Build and operate real-time ML inference infrastructure.","Verdict":"Weak Match","job_match_score":30,"summary":"Candidate has sufficient years of experience but the entire technical stack is mismatched. No overlap with streaming systems, Kubernetes, or MLflow required for this role.","required_exp":"5 years","gaps":{"technical":["Kafka","Spark","Flink","Kubernetes","MLflow"],"domain":["Real-time ML inference","ML platform engineering"],"soft_skills":[]},"improvement_suggestions":{"resume_edits":[],"interview_prep":[]},"interview_tips":{"high_priority_topics":[],"your_strengths_to_highlight":[],"questions_to_ask":[]},"recommended_action":"skip","wit_line":"Pass on this one","jd_keywords":["Kafka","Spark","Flink","Kubernetes","MLflow"],"matched_keywords":[],"missing_keywords":["Kafka","Spark","Flink","Kubernetes","MLflow"],"posted_date":"Unknown","application_deadline":"Unknown","job_url":"Unknown"}
```

### Anchor 5 — Borderline Weak (score: 45, recommended_action: "skip")
Role: Analytics Engineer, 3yr required, Snowflake + dbt + Looker + SQL Server, BI reporting domain.
Candidate: 5yr experience and dbt overlap — but the role is fundamentally BI-heavy, platform is Snowflake/SQL Server not GCP, and Looker/reporting is the core deliverable not pipeline engineering.
```json
{"job_id":"anchor-5","company_name":"RetailBI Corp","title_role":"Analytics Engineer","recruiter_email":"Unknown","JD":"Analytics Engineer requiring 3yr experience with Snowflake, dbt, Looker, and SQL Server. Own BI dashboards and reporting models for commercial teams. Strong Looker LookML and stakeholder-facing data presentation required.","Verdict":"Weak Match","job_match_score":45,"summary":"Candidate meets experience threshold and shares dbt overlap, but the role is BI and reporting-led rather than pipeline engineering. No Snowflake, Looker, or SQL Server experience. Function mismatch — candidate builds data infrastructure, this role delivers dashboards.","required_exp":"3 years","gaps":{"technical":["Snowflake","Looker / LookML","SQL Server"],"domain":["BI reporting","Stakeholder-facing data presentation"],"soft_skills":[]},"improvement_suggestions":{"resume_edits":[{"area":"work highlights","suggestion":"Surface any dbt exposure to Gold/reporting layer as closest proxy to analytics engineering work","approved_reference":"Approved doc: Data Engineering lists dbt and Medallion Architecture; Analytics lists Semantic Layer Concepts and dbt Testing"}],"interview_prep":["Study Looker LookML basics","Review Snowflake vs BigQuery architectural differences"]},"interview_tips":{"high_priority_topics":[{"topic":"Looker + LookML","why":"Core deliverable of the role, no existing experience","prep":"Significant ramp-up required — limited transferability from dbt alone"}],"your_strengths_to_highlight":["dbt modelling experience","Data quality and testing discipline"],"questions_to_ask":["How much of the role is LookML vs dbt modelling?","Is there a data engineering counterpart on the team?"]},"recommended_action":"skip","wit_line":"Wrong end of the stack","jd_keywords":["Snowflake","dbt","Looker","LookML","SQL Server"],"matched_keywords":["dbt"],"missing_keywords":["Snowflake","Looker","LookML","SQL Server"],"posted_date":"Unknown","application_deadline":"Unknown","job_url":"Unknown"}
```

Return the evaluation JSON now."""

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
""" + anchors
