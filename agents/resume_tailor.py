import json
from pathlib import Path
from agents.base import BaseAgent
from agents.database import get_evaluation, is_job_parsed, get_jd_parsed
from backend.settings import settings

class ResumeTailorAgent(BaseAgent):
    """
    Agent for tailoring a resume to a specific Job Description.
    Strategy: "Conservative Editor" (Preserves structure, edits ~40% of content).
    """

    def __init__(self, model: str = None):
        super().__init__(model)

    def get_system_prompt(self) -> str:
        prompt_path = Path("agent_prompts/resume_tailor.md")
        if prompt_path.exists():
            with open(prompt_path) as f:
                return f.read()
        return "You are an expert Resume Tailor." # Fallback

    def build_user_prompt(self, base_resume: dict, jd_context: dict, approved_skills: str) -> str:
        return f"""
        ### BASE RESUME (JSON):
        {json.dumps(base_resume, indent=2)}
        
        ### JD CONTEXT (Structured):
        {json.dumps(jd_context, indent=2)}
        
        ### APPROVED SKILLS (Source of Truth):
        {approved_skills}
        
        ### INSTRUCTION:
        Apply the "Conservative Editor" strategy.
        1. Maintain Bullet Counts.
        2. Integrate 'ats_keywords' from JD Context where truthful.
        3. Fill 'strategic_gaps' using 'APPROVED SKILLS' only.
        
        Return VALID JSON only.
        """

    def run_tailoring(self, job_id: str, base_resume: dict, approved_skills: str) -> dict:
        """
        Run the resume tailoring process.
        Returns the tailored resume JSON.
        """
        
        # 1. Fetch Context
        evaluation = get_evaluation(job_id)
        if not evaluation:
            raise ValueError(f"Job not evaluated yet: {job_id}")
            
        jd_parsed = get_jd_parsed(job_id)
        if not jd_parsed:
             print(f"Warning: JD Parser signals missing for {job_id}. Tailoring might lack precision.")
             jd_parsed = {}

        # 2. Construct Prompt Inputs
        # Safely handle raw_response which might be a string or dict
        raw_response = evaluation.get("raw_response", {})
        if isinstance(raw_response, str):
            try:
                raw_response = json.loads(raw_response)
            except:
                raw_response = {}
        
        # We don't really rely on full JD text anymore as we use structured signals
        # But if we did, we'd get it here properly now.
        
        jd_context = {
            "role": evaluation.get("title_role"),
            "company": evaluation.get("company_name"),
            "summary": evaluation.get("summary"),
            "must_haves": jd_parsed.get("must_haves", []),
            "ats_keywords": jd_parsed.get("ats_keywords", []),
            "strategic_gaps": evaluation.get("gaps", {}),
            "improvement_suggestions": evaluation.get("improvement_suggestions", [])
        }

        # 3. Use BaseAgent.run() which handles token limits, keys, etc.
        # Pass the kwargs expected by build_user_prompt
        # Note: BaseAgent.run calls build_user_prompt(**kwargs)
        
        # Override BaseAgent.run to inject specific json_mode=True if needed?
        # BaseAgent.run calls _call_llm which uses just the prompt.
        # BaseAgent doesn't natively support json_mode param in _call_llm signature in the provided file.
        # But OpenRouter supports it via model parameters or just prompt engineering.
        # The prompt says "Return VALID JSON".
        # We can pass `response_format` in _call_llm if we updated BaseAgent, but right now we rely on prompt.
        
        return self.run(base_resume=base_resume, jd_context=jd_context, approved_skills=approved_skills)

