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
        return "You are a Resume Change Planner. Return a structured JSON edit plan."

    def build_user_prompt(self, base_resume: dict, jd_context: dict, approved_skills: str) -> str:
        return f"""
        ### BASE RESUME (JSON):
        {json.dumps(base_resume, indent=2)}

        ### JD CONTEXT (Structured):
        {json.dumps(jd_context, indent=2)}

        ### APPROVED SKILLS (Source of Truth):
        {approved_skills}

        ### INSTRUCTION:
        Analyze the gaps and improvement suggestions in the JD Context.
        Cross-reference with Approved Skills to verify truthfulness.
        Produce a structured edit plan with specific locations, actions, and reasons.

        Return VALID JSON only.
        """
