"""
Base Agent class for OpenRouter LLM interactions.
"""
import json
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx

from backend.settings import settings


class BaseAgent(ABC):
    """Base class for all LLM agents."""
    
    def __init__(
        self,
        model: str | None = None,
        system_prompt: str = "",
        temperature: float = 0.7,
    ):
        self.model = model or settings.OPENROUTER_MODEL
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.api_key = settings.OPENROUTER_API_KEY
        self.base_url = settings.OPENROUTER_BASE_URL
        
    def _call_llm(self, user_prompt: str) -> str:
        """Make a raw LLM call and return the response text."""
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not set in environment")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/TailorAI",
            "X-Title": "TailorAI Job Evaluator",
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
        }
        
        with httpx.Client(timeout=120.0) as client:
            # Handle both cases: base URL with or without /chat/completions
            base_url = self.base_url.rstrip("/")
            url = base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"
            response = client.post(
                url,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            
        data = response.json()
        return data["choices"][0]["message"]["content"]
    
    def _parse_json_response(self, response_text: str) -> dict:
        """Parse JSON from LLM response, handling markdown code blocks."""
        text = response_text.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        text = text.strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            # Try to find JSON object in the response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(text[start:end])
            raise ValueError(f"Failed to parse JSON response: {e}")
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        pass
    
    @abstractmethod
    def build_user_prompt(self, **kwargs) -> str:
        """Build the user prompt from input data."""
        pass
    
    def run(self, **kwargs) -> dict:
        """Execute the agent and return parsed results."""
        self.system_prompt = self.get_system_prompt()
        user_prompt = self.build_user_prompt(**kwargs)
        
        response_text = self._call_llm(user_prompt)
        result = self._parse_json_response(response_text)
        
        # Add metadata
        result["_model_used"] = self.model
        result["_agent"] = self.__class__.__name__
        
        # Rate limiting
        time.sleep(settings.EVAL_DELAY_SECONDS)
        
        return result
