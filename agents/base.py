import json
import time
import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx
import os
from backend.settings import settings

logger = logging.getLogger(__name__)

# Configure Langfuse Env Vars for the SDK to pick up automatically
# MUST be set before importing langfuse.decorators
os.environ["LANGFUSE_PUBLIC_KEY"] = settings.LANGFUSE_PUBLIC_KEY
os.environ["LANGFUSE_SECRET_KEY"] = settings.LANGFUSE_SECRET_KEY
os.environ["LANGFUSE_HOST"] = settings.LANGFUSE_BASE_URL

from langfuse.decorators import observe, langfuse_context

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
        
        # Initialize OpenAI client (wrapped by Langfuse)
        # We use the standard openai client but imported from langfuse.openai to get auto-instrumentation
        try:
            from langfuse.openai import openai
            
            self.client = openai.OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                default_headers={
                    "HTTP-Referer": "https://github.com/TailorAI",
                    "X-Title": "TailorAI Job Evaluator",
                }
            )
        except ImportError:
            logger.warning("Langfuse OpenAI wrapper not found, falling back to standard openai")
            import openai
            self.client = openai.OpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                default_headers={
                    "HTTP-Referer": "https://github.com/TailorAI",
                    "X-Title": "TailorAI Job Evaluator",
                }
            )

    @observe(as_type="generation")
    def _call_llm(self, user_prompt: str) -> str:
        """Make a LLM call using OpenAI SDK and return the response text."""
        if not self.api_key:
            logger.critical("OPENROUTER_API_KEY not set in environment")
            raise ValueError("OPENROUTER_API_KEY not set in environment")
            
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        # Primary then Backup model strategy
        models_to_try = [self.model]
        if settings.OPENROUTER_MODEL_BACKUP and settings.OPENROUTER_MODEL_BACKUP != self.model:
            models_to_try.append(settings.OPENROUTER_MODEL_BACKUP)
            
        last_exception = None
        
        for current_model in models_to_try:
            # Retry logic for this model (e.g. 429 Rate Limits)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    if current_model != self.model:
                        logger.warning(f"Retrying with BACKUP model: {current_model}")

                    # SDK Call
                    completion = self.client.chat.completions.create(
                        model=current_model,
                        messages=messages,
                        temperature=self.temperature,
                        extra_body={
                            "usage": { "include": True } # Critical for OpenRouter cost tracking
                        },
                        name=f"{self.__class__.__name__}-generation"
                    )
                    
                    content = completion.choices[0].message.content
                    
                    # Manual usage/cost tracking for OpenRouter via Langfuse
                    try:
                        if hasattr(completion, 'usage') and completion.usage:
                            # Extract usage stats
                            usage = completion.usage
                            
                            # Prepare metadata update
                            metadata_update = {
                                "model": current_model,
                                "usage_prompt_tokens": getattr(usage, "prompt_tokens", 0),
                                "usage_completion_tokens": getattr(usage, "completion_tokens", 0),
                                "usage_total_tokens": getattr(usage, "total_tokens", 0),
                            }
                            
                            # Try to extract cost if present (OpenRouter specific)
                            # OpenRouter often sends cost in the extra fields or we might need to rely on model pricing
                            # But sometimes it's in completion.usage (if using specific client) or extra_fields
                            
                            # Check for direct 'cost' attribute or within dict if it's a dict
                            cost = getattr(usage, "cost", None)
                            
                            # If using standard openai client, usage is an object. 
                            # OpenRouter might inject cost into it, but accessing it might fail if strict typing.
                            # Let's try converting to dict if possible
                            if hasattr(usage, "model_dump"):
                                usage_dict = usage.model_dump()
                                if "cost" in usage_dict:
                                    cost = usage_dict["cost"]
                            
                            if cost is not None:
                                metadata_update["cost"] = cost
                                metadata_update["openrouter_cost"] = cost
                                
                            # Update Langfuse observation
                            langfuse_context.update_current_observation(
                                metadata=metadata_update,
                                model=current_model,
                                usage={
                                    "input": getattr(usage, "prompt_tokens", 0),
                                    "output": getattr(usage, "completion_tokens", 0),
                                    "total": getattr(usage, "total_tokens", 0),
                                    "unit": "TOKENS"
                                }
                            )
                            
                            if cost:
                                logger.info(f"OpenRouter Cost captured: ${cost}")
                                
                    except Exception as e:
                        logger.warning(f"Failed to extract/update Langfuse usage: {e}")

                    # Log with output preview
                    output_preview = content[:500] + "..." if len(content) > 500 else content
                    logger.info(f"LLM call completed via SDK", extra={
                        "model": current_model,
                        "output_preview": output_preview,
                    })
                    
                    return content
                    
                except Exception as e:
                    # Check for rate limit in exception message or type
                    is_rate_limit = "429" in str(e) or "Rate limit" in str(e)
                    
                    if is_rate_limit:
                         wait_time = 5 * (attempt + 1)
                         logger.warning(f"Rate limited (429) on {current_model}. Waiting {wait_time}s...")
                         time.sleep(wait_time)
                         if attempt == max_retries - 1:
                             last_exception = e
                         continue
                    
                    # If not rate limit, or exhausted retries
                    logger.error(f"Model {current_model} failed attempt {attempt+1}: {e}")
                    last_exception = e
                    if not is_rate_limit:
                        break # Break retry loop for non-transient errors (usually)
            
            # If we get here and didn't return, we try the next model
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
