import os
import requests
import json
import time
from backend.settings import settings

# --- Setup Environment Variables ---
os.environ["LANGFUSE_PUBLIC_KEY"] = settings.LANGFUSE_PUBLIC_KEY
os.environ["LANGFUSE_SECRET_KEY"] = settings.LANGFUSE_SECRET_KEY
os.environ["LANGFUSE_HOST"] = settings.LANGFUSE_HOST

print(f"Testing with Host: {settings.LANGFUSE_HOST}")
print(f"Public Key: {settings.LANGFUSE_PUBLIC_KEY[:5]}...")
print(f"OpenRouter Model: {settings.OPENROUTER_MODEL}")

from langfuse import Langfuse

# Initialize Langfuse
langfuse = Langfuse()

def call_openrouter(prompt):
    """Makes a real call to OpenRouter."""
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
         # "HTTP-Referer": "http://localhost:3000", # Optional
    }
    
    # Use the backup model if the main one is empty or unreliable logic isn't here
    model = settings.OPENROUTER_MODEL or "x-ai/grok-4.1-fast" # fallback
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    
    print(f"Calling OpenRouter with model: {model}...")
    start_time = time.time()
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload
    )
    end_time = time.time()
    
    response.raise_for_status()
    data = response.json()
    
    return data, model, start_time, end_time

try:
    print("Starting trace...")
    
    # 1. Create the root trace
    trace = langfuse.trace(name="manual-llm-execution")
    
    # 2. Create a span for the "Pre-processing" work
    span = trace.span(name="preprocessing")
    span.update(output="Preparing prompt...")
    prompt = "Explain quantum computing in one sentence."
    span.end()
    
    # 3. Create a GENERATION for the actual LLM call
    generation = trace.generation(
        name="openrouter-call",
        model=settings.OPENROUTER_MODEL or "unknown",
        input=[{"role": "user", "content": prompt}],
        metadata={"provider": "openrouter"}
    )
    
    try:
        # Perform the actual network call
        data, used_model, start, end = call_openrouter(prompt)
        
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        
        # 4. Update the generation with specific LLM metrics
        generation.update(
            model=used_model, 
            output=content,
            usage={
                "input": usage.get("prompt_tokens"),
                "output": usage.get("completion_tokens"),
                "total": usage.get("total_tokens")
            },
            end_time=time.time() 
        )
        print(f"\nLLM Response: {content}\n")
        
    except Exception as e:
        generation.update(level="ERROR", status_message=str(e))
        raise e
    finally:
        generation.end()
    
    # 5. Post-processing span
    span = trace.span(name="postprocessing")
    span.update(input=content, output="Done")
    span.end()
    
    print("Trace created. Flushing...")
    langfuse.flush()
    print("✅ Flush complete. Check UI at http://localhost:3010")

except Exception as e:
    import traceback
    traceback.print_exc()
