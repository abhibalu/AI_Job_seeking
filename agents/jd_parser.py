"""
JD Parser Agent - Extracts structured signals from job descriptions.

Returns must-haves, skills, keywords, and normalized skill mappings.
"""
from pathlib import Path

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
            self.approved_skills = ""
    
    def get_system_prompt(self) -> str:
        return """You are a conservative JD-to-signals extractor.
Return ONLY a single valid JSON object with fields exactly as specified.
Be precise and avoid guessing. If unsure, set fields to [] or "unspecified".
Normalize tools/skills using the provided SKILL_BUCKET map; include both the original term and its canonical mapping.
Do not invent requirements not present in the JD."""
    
    def build_user_prompt(self, job_id: str, description_text: str) -> str:
        return f"""JOB DESCRIPTION (raw text):
{description_text}

SKILL_BUCKET (canonical map):
{self.approved_skills}

job_id: {job_id}

Return JSON ONLY with this shape:

{{
  "job_id": "{job_id}",
  "must_haves": ["exact phrases explicitly required in JD"],
  "nice_to_haves": ["explicitly listed as preferred/nice"],
  "domain": "e.g., fintech | retail | healthcare | unspecified",
  "seniority": "junior | mid | senior | lead | unspecified",
  "location_constraints": ["e.g., on-site Dublin", "EU work permit", "unspecified"],
  "ats_keywords": ["5–12 exact JD terms likely used by ATS"],
  "normalized_skills": {{
    "canonical": ["canonical names from approved_skills"],
    "synonym_hits": [
      {{"term":"Azure Data Factory","maps_to":"ADF"}},
      {{"term":"ADLS","maps_to":"ADLS Gen2"}}
    ],
    "unknown_terms": ["terms not found in approved_skills"]
  }}
}}

Rules:
- Extract only what the JD states. If ambiguous, choose "unspecified" or [].
- For seniority: infer only if JD states (e.g., "Senior", "Lead").
- For domain: infer only if clearly indicated (industry, product, or data domain).
- ats_keywords should be the most salient exact phrases from the JD, not generic words.
- Use SKILL_BUCKET to populate normalized_skills.canonical; include synonym_hits for mapped terms.

Return the JSON now."""


def run_jd_parser_task(job_id: str, description_text: str):
    """
    Background task to run JD parsing and save results.
    """
    try:
        from .database import save_jd_parsed, is_job_parsed
        
        # specific check to avoid re-parsing if already done (though API might have checked too)
        if is_job_parsed(job_id):
            print(f"Job {job_id} already parsed. Skipping.")
            return

        print(f"Starting background JD parsing for {job_id}...")
        agent = JDParserAgent()
        result = agent.run(job_id=job_id, description_text=description_text)
        
        # Save to DB
        save_jd_parsed(result)
        print(f"Successfully parsed and saved JD for {job_id}")
        
    except Exception as e:
        print(f"Error in background JD parsing for {job_id}: {e}")

