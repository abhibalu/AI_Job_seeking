import json
import logging
from pathlib import Path
from agents.base import BaseAgent
from agents.database import get_evaluation, get_jd_parsed

logger = logging.getLogger(__name__)

class ResumeTailorAgent(BaseAgent):
    """
    Agent for tailoring a resume to a specific Job Description.
    Strategy: "Conservative Editor" (Preserves structure, edits ~40% of content).
    """

    def __init__(self, model: str = None):
        super().__init__(model, temperature=0.3)

    def get_system_prompt(self) -> str:
        prompt_path = Path("agent_prompts/resume_tailor.md")
        if prompt_path.exists():
            with open(prompt_path) as f:
                return f.read()
        return "You are an expert Resume Tailor." # Fallback

    def build_user_prompt(self, base_resume: dict, edit_plan: dict, approved_skills: str, critique: str = None, **kwargs) -> str:
        prompt = f"""
### BASE RESUME (JSON):
{json.dumps(base_resume, indent=2)}

### EDIT PLAN (Structured):
{json.dumps(edit_plan, indent=2)}

### APPROVED SKILLS (Source of Truth):
{approved_skills}

### INSTRUCTION:
Apply the edit plan to the base resume.
1. Only modify locations specified in the edit plan.
2. Copy all other content exactly verbatim.
3. Preserve bullet counts, IDs, and section structure.

### EXAMPLE:

Base Resume (excerpt):
{{
  "experience": [
    {{
      "id": "acme",
      "company": "Acme Corp",
      "bullets": [
        {{"id": "acme_1", "text": "Built internal tooling for the ops team using Python."}},
        {{"id": "acme_2", "text": "Managed deployments to AWS using Jenkins pipelines."}}
      ]
    }}
  ]
}}

Edit Plan (excerpt):
{{
  "edits": [
    {{
      "location": "experience.acme.bullets.acme_1",
      "action": "rephrase",
      "target_text": "Developed Python automation tools for operations, reducing manual work by 30%.",
      "reason": "Add impact metric aligned with JD focus on automation"
    }}
  ],
  "preserve": ["acme_2"]
}}

Expected Output (excerpt):
{{
  "experience": [
    {{
      "id": "acme",
      "company": "Acme Corp",
      "bullets": [
        {{"id": "acme_1", "text": "Developed Python automation tools for the ops team, cutting manual deployment steps by 30%."}},
        {{"id": "acme_2", "text": "Managed deployments to AWS using Jenkins pipelines."}}
      ]
    }}
  ]
}}

Note: acme_2 is copied exactly verbatim. acme_1 preserves the core action and metric from target_text with minor voice adjustment.
"""

        if critique:
            prompt += f"""
### CRITIQUE TO ADDRESS (URGENT):
The reviewer found the following issues with your previous draft:
{critique}

Revision workflow:
1. Identify the specific bullets named in the critique above.
2. Revise only those bullets to fix the reported issues.
3. All other sections and bullets must remain exactly as in your previous draft — do not touch them.
"""

        prompt += "\nReturn VALID JSON only."
        return prompt

    def run_tailoring(self, job_id: str, base_resume: dict, approved_skills: str) -> dict:
        """
        Legacy direct-call path: fetches context from DB, generates a plan, and executes.
        Prefer using the subgraph (build_tailoring_subgraph) for the full pipeline.
        """
        from agents.change_planner import ChangePlannerAgent

        # 1. Fetch Context
        evaluation = get_evaluation(job_id)
        if not evaluation:
            raise ValueError(f"Job not evaluated yet: {job_id}")

        jd_parsed = get_jd_parsed(job_id)
        if not jd_parsed:
            logger.warning("JD Parser signals missing — tailoring may lack precision", extra={"job_id": job_id})
            jd_parsed = {}

        jd_context = {
            "role": evaluation.get("title_role"),
            "company": evaluation.get("company_name"),
            "summary": evaluation.get("summary"),
            "must_haves": jd_parsed.get("must_haves", []),
            "ats_keywords": jd_parsed.get("ats_keywords", []),
            "strategic_gaps": evaluation.get("gaps", {}),
            "improvement_suggestions": evaluation.get("improvement_suggestions", [])
        }

        # 2. Generate edit plan
        planner = ChangePlannerAgent()
        edit_plan = planner.run(
            base_resume=base_resume,
            jd_context=jd_context,
            approved_skills=approved_skills,
        )

        # 3. Execute the plan
        return self.run(base_resume=base_resume, edit_plan=edit_plan, approved_skills=approved_skills)

