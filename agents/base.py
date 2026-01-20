"""
Base Agent class for OpenRouter LLM interactions.
"""
import json
import time
import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx
import os
from langfuse.decorators import observe

from backend.settings import settings

logger = logging.getLogger(__name__)

# Configure Langfuse Env Vars for the SDK to pick up automatically
os.environ["LANGFUSE_PUBLIC_KEY"] = settings.LANGFUSE_PUBLIC_KEY
os.environ["LANGFUSE_SECRET_KEY"] = settings.LANGFUSE_SECRET_KEY
os.environ["LANGFUSE_HOST"] = settings.LANGFUSE_HOST

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
        
    @observe()
    def _call_llm(self, user_prompt: str) -> str:
        """Make a raw LLM call and return the response text. Retries with backup model on failure."""
        if not self.api_key:
            logger.critical("OPENROUTER_API_KEY not set in environment")
            raise ValueError("OPENROUTER_API_KEY not set in environment")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/TailorAI",
            "X-Title": "TailorAI Job Evaluator",
        }
        
        # Primary then Backup model strategy
        models_to_try = [self.model]
        if settings.OPENROUTER_MODEL_BACKUP and settings.OPENROUTER_MODEL_BACKUP != self.model:
            models_to_try.append(settings.OPENROUTER_MODEL_BACKUP)
            
        last_exception = None
        
        for current_model in models_to_try:
            payload = {
                "model": current_model,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": self.temperature,
            }
            
            # Retry logic for this model (e.g. 429 Rate Limits)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    if current_model != self.model:
                        logger.warning(f"Retrying with BACKUP model: {current_model}")

                    with httpx.Client(timeout=120.0) as client:
                        base_url = self.base_url.rstrip("/")
                        url = base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"
                        response = client.post(
                            url,
                            headers=headers,
                            json=payload,
                        )
                        
                        # Handle 429 specifically
                        if response.status_code == 429:
                            wait_time = 5 * (attempt + 1) # Linear backoff: 5s, 10s, 15s
                            logger.warning(f"Rate limited (429) on {current_model}. Waiting {wait_time}s...")
                            time.sleep(wait_time)
                            if attempt == max_retries - 1:
                                response.raise_for_status() # Raise on final attempt
                            continue # Retry same model
                            
                        response.raise_for_status()
                        
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                    
                except Exception as e:
                    # If it's the last retry, log and break to try next model
                    if attempt == max_retries - 1:
                        logger.error(f"Model {current_model} failed after {max_retries} attempts: {e}")
                        last_exception = e
                    # For non-429 errors (like network/timeout), maybe retry too? 
                    # For now we rely on the loop above for 429.
                    # If it was a 429, we already continued in the loop. 
                    # If it was other error, break to next model.
                    if "429" not in str(e):
                         break
            
            # If we are here, this model failed completely. Try next model.
            continue
                
        # If we get here, all models failed
        if last_exception:
            raise last_exception
        raise RuntimeError("LLM call failed with no exception captured")
    
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
    
    @observe()
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
