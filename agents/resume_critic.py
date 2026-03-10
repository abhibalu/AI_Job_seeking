import json
from pathlib import Path
from agents.base import BaseAgent
import logging

logger = logging.getLogger(__name__)

class ResumeCriticAgent(BaseAgent):
    """
    Acts as a Hiring Manager reviewing a draft resume.
    Returns a list of actionable critiques.
    """

    def __init__(self, model: str = None):
        super().__init__(model)

    def get_system_prompt(self) -> str:
        prompt_path = Path("agent_prompts/resume_critic.md")
        if prompt_path.exists():
            with open(prompt_path) as f:
                return f.read()
        return "You are a strict Resume Critic. Return a JSON list of strings containing critiques."

    def build_user_prompt(self, draft_resume: dict, jd_context: dict, approved_skills: str) -> str:
        return f"""
        ### DRAFT RESUME TO REVIEW (JSON):
        {json.dumps(draft_resume, indent=2)}
        
        ### JOB DESCRIPTION CONTEXT:
        {json.dumps(jd_context, indent=2)}
        
        ### CANDIDATE'S ACTUAL APPROVED SKILLS (Source of Truth):
        {approved_skills}
        
        Review the draft. Return a JSON array of strings containing your critique. 
        If the draft is perfect, return `[]`.
        """
        
    def _parse_json_response(self, text: str) -> list:
        """
        Override because the critic returns a list of strings, not a dict.
        """
        # Try to find JSON array in the text
        if "[" in text and "]" in text:
            start_idx = text.find("[")
            end_idx = text.rfind("]") + 1
            json_str = text[start_idx:end_idx]
            try:
                parsed = json.loads(json_str)
                if isinstance(parsed, list):
                    return parsed
            except Exception as e:
                logger.error(f"[ResumeCritic] Failed to parse JSON list from LLM: {e}\nText: {text}")
        
        # Fallback to returning the raw text as a single critique item
        return [text.strip()]

    def run(self, **kwargs) -> list:
        """Execute the critic agent and return a list of critiques."""
        self.system_prompt = self.get_system_prompt()
        user_prompt = self.build_user_prompt(**kwargs)
        
        response_text = self._call_llm(user_prompt)
        critique_list = self._parse_json_response(response_text)
        
        return critique_list
