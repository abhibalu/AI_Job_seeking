import json
from pathlib import Path
from agents.base import BaseAgent
import logging

logger = logging.getLogger(__name__)


class ChangePlannerAgent(BaseAgent):
    """
    Plans specific resume edits based on JD gaps and approved skills.
    Produces a structured edit plan — does NOT modify the resume.
    """

    def __init__(self, model: str = None):
        super().__init__(model, temperature=0.2)

    def get_system_prompt(self) -> str:
        prompt_path = Path("agent_prompts/change_planner.md")
        if prompt_path.exists():
            with open(prompt_path) as f:
                return f.read()
        logger.warning("change_planner.md not found at %s — using minimal fallback prompt", prompt_path)
        return "You are a Resume Change Planner. Return a structured JSON edit plan."

    def build_user_prompt(self, base_resume: dict, jd_context: dict, approved_skills: str) -> str:
        return f"""### BASE RESUME (JSON):
{json.dumps(base_resume, indent=2)}

### JD CONTEXT (Structured):
{json.dumps(jd_context, indent=2)}

### APPROVED SKILLS (Source of Truth):
{approved_skills}

### ONE-SHOT EXAMPLE

JD Context fragment:
{{"must_haves": ["3+ years Python", "Experience with Redshift"], "ats_keywords": ["Redshift", "Python", "ELT", "data pipeline"], "strategic_gaps": {{"technical": ["Redshift"]}}, "improvement_suggestions": {{"resume_edits": [{{"area": "work highlights", "suggestion": "Frame BigQuery experience as transferable to Redshift", "approved_reference": "Data Engineering: BigQuery, SQL; Notable Projects: Teradata-to-BigQuery migration"}}]}}}}

Expected edit plan:
{{
  "edits": [
    {{
      "location": "work[0].highlights[2]",
      "action": "rephrase",
      "current_text": "Migrated legacy Teradata warehouse to BigQuery, building ELT pipelines with 4-hour refresh cycles",
      "target_text": "Migrated legacy data warehouse to BigQuery (columnar MPP, comparable to Redshift), building ELT pipelines with 4-hour refresh cycles",
      "reason": "JD requires Redshift; BigQuery is closest approved columnar warehouse — draw explicit parallel",
      "approved_source": "Notable Projects: Teradata-to-BigQuery Warehouse Modernization — parallel ELT pipelines"
    }},
    {{
      "location": "skills",
      "action": "add",
      "items": ["ELT"],
      "reason": "ATS keyword 'ELT' is present in approved skills but missing from skills section",
      "approved_source": "Data Engineering: ELT Pipelines"
    }}
  ],
  "preserve": [
    "work[0].highlights[0-1]",
    "work[0].highlights[3-5]",
    "work[1].*",
    "education.*"
  ],
  "summary": "1 bullet rephrase (Redshift parallel), 1 skill addition (ELT). Change ratio: 1/6 bullets = 17%."
}}

### INSTRUCTION:
Analyze the gaps and improvement suggestions in the JD Context.
Cross-reference with Approved Skills to verify truthfulness.
Produce a structured edit plan with specific locations, actions, and reasons.

Return VALID JSON only."""
