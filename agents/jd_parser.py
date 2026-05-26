"""
JD Parser Agent - Extracts structured signals from job descriptions.

Returns must-haves, skills, keywords, and normalized skill mappings.
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

from .base import BaseAgent


class JDParserAgent(BaseAgent):
    """Agent that parses and extracts signals from job descriptions."""
    
    def __init__(self, model: str | None = None):
        super().__init__(model=model, temperature=0.2)
        self._load_approved_skills()
    
    def _load_approved_skills(self):
        """Load approved skills for normalization."""
        skills_path = Path("agent_prompts/approved_skills.md")
        if skills_path.exists():
            with open(skills_path) as f:
                self.approved_skills = f.read()
        else:
            logger.warning("approved_skills.md not found at %s — skill normalization will produce empty canonical matches", skills_path)
            self.approved_skills = ""
    
    def get_system_prompt(self) -> str:
        return """You are a conservative JD-to-signals extractor.
Return ONLY a single valid JSON object — no markdown fences, no commentary, no text outside the JSON.
Be precise and avoid guessing. If unsure, set fields to [] or "unspecified".
Normalize tools/skills using the provided SKILL_BUCKET map.
Do not invent requirements not present in the JD.
Do not extract signals from boilerplate sections (equal opportunity statements, legal disclaimers, company benefits)."""
    
    def build_user_prompt(self, job_id: str, description_text: str) -> str:
        return f"""JOB DESCRIPTION (raw text):
{description_text}

SKILL_BUCKET (canonical map):
{self.approved_skills}

job_id: {job_id}

EXTRACTION STEPS:
1. Identify explicit requirements ("must have", "required", "X+ years") → must_haves. Use verbatim phrases from the JD.
2. Identify preferred/optional qualifications ("nice to have", "preferred", "bonus") → nice_to_haves. Do not duplicate items already in must_haves.
3. Determine seniority ONLY if the JD explicitly states a level (e.g., "Senior", "Lead", "Junior"). Otherwise "unspecified".
4. Determine domain ONLY if the JD clearly indicates an industry or vertical. Otherwise "unspecified".
5. Select 5–12 ATS keywords: exact salient phrases from the JD that an applicant tracking system would match on. Exclude generic terms ("team player", "communication skills").
6. Normalize skills against SKILL_BUCKET:
   a. For each technical term in the JD, check if it appears as a canonical name in SKILL_BUCKET → add to canonical.
   b. If the JD term is a known synonym or alias of a SKILL_BUCKET entry (e.g., "Azure Data Factory" → "ADF"), add to synonym_hits with the mapping.
   c. If the term is not in SKILL_BUCKET at all, add to unknown_terms.

Return JSON ONLY with this shape:

{{
  "job_id": "{job_id}",
  "must_haves": ["verbatim phrases from the JD that are explicitly required"],
  "nice_to_haves": ["verbatim phrases explicitly listed as preferred/nice-to-have"],
  "domain": "fintech | retail | healthcare | edtech | adtech | saas | consulting | other | unspecified",
  "seniority": "junior | mid | senior | lead | unspecified",
  "location_constraints": ["e.g., on-site Dublin", "EU work permit", "unspecified"],
  "ats_keywords": ["5–12 exact JD terms likely used by ATS"],
  "normalized_skills": {{
    "canonical": ["canonical names from SKILL_BUCKET"],
    "synonym_hits": [
      {{"term": "Azure Data Factory", "maps_to": "ADF"}},
      {{"term": "Postgres", "maps_to": "PostgreSQL"}}
    ],
    "unknown_terms": ["technical terms not found in SKILL_BUCKET"]
  }}
}}

ONE-SHOT EXAMPLE:

Input JD fragment:
"We're looking for a Senior Data Engineer with 5+ years of experience in Python and SQL. Experience with dbt and Airflow is required. Familiarity with Snowflake or BigQuery is a plus. This role is based in Dublin, Ireland (hybrid)."

Expected output:
{{
  "job_id": "example-123",
  "must_haves": ["Senior Data Engineer", "5+ years of experience in Python and SQL", "Experience with dbt and Airflow"],
  "nice_to_haves": ["Familiarity with Snowflake or BigQuery"],
  "domain": "unspecified",
  "seniority": "senior",
  "location_constraints": ["hybrid Dublin, Ireland"],
  "ats_keywords": ["Data Engineer", "Python", "SQL", "dbt", "Airflow", "Snowflake", "BigQuery", "hybrid"],
  "normalized_skills": {{
    "canonical": ["Python", "SQL", "dbt", "Apache Airflow", "Snowflake", "BigQuery"],
    "synonym_hits": [
      {{"term": "Airflow", "maps_to": "Apache Airflow"}}
    ],
    "unknown_terms": []
  }}
}}

Now extract from the JD above. Return the JSON only."""


def run_jd_parser_task(job_id: str, description_text: str):
    """
    Background task to run JD parsing and save results.
    """
    try:
        from .database import save_jd_parsed, is_job_parsed
        
        # specific check to avoid re-parsing if already done (though API might have checked too)
        if is_job_parsed(job_id):
            logger.info("Job %s already parsed. Skipping.", job_id, extra={"job_id": job_id})
            return

        logger.info("Starting background JD parsing for %s", job_id, extra={"job_id": job_id})
        agent = JDParserAgent()
        result = agent.run(job_id=job_id, description_text=description_text)

        # Save to DB
        save_jd_parsed(result)
        logger.info("Successfully parsed and saved JD for %s", job_id, extra={"job_id": job_id})

    except Exception as e:
        logger.exception("Error in background JD parsing for %s", job_id, extra={"job_id": job_id})

