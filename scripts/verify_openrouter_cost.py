
import os
import sys
import time

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langfuse.decorators import observe
from langfuse.openai import openai
from backend.settings import settings

# Configure environment for Langfuse - MUST be set before importing langfuse
os.environ["LANGFUSE_PUBLIC_KEY"] = settings.LANGFUSE_PUBLIC_KEY
os.environ["LANGFUSE_SECRET_KEY"] = settings.LANGFUSE_SECRET_KEY
os.environ["LANGFUSE_HOST"] = settings.LANGFUSE_BASE_URL.replace("localhost", "127.0.0.1")

@observe(name="openrouter-cost-verification")
def verify_cost_tracking():
    """Verify OpenRouter cost integration with Langfuse.
    
    This function tests that:
    1. OpenRouter API calls are traced
    2. Token usage is captured
    3. Cost data from OpenRouter is properly logged
    """
    print("Locked and loaded. Testing OpenRouter cost integration...")
    
    client = openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.OPENROUTER_API_KEY,
        default_headers={
             "HTTP-Referer": "https://github.com/TailorAI",
             "X-Title": "TailorAI Cost Verification",
        }
    )

    model = "google/gemini-2.0-flash-exp:free"
    if settings.OPENROUTER_MODEL:
        model = settings.OPENROUTER_MODEL

    print(f"Using model: {model}")

    try:
        # Make the API call with usage tracking enabled
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "What is 2+2? Answer in one word."}
            ],
            extra_body={
                "usage": {"include": True}  # Critical for OpenRouter cost tracking
            },
            name="cost-verification-generation",
            metadata={
                "source": "cost-verification-script",
                "provider": "openrouter"
            }
        )
        
        print("\n--- Response ---")
        print(completion.choices[0].message.content)
        
        print("\n--- Usage Data (from OpenRouter SDK) ---")
        openrouter_cost = None
        if completion.usage:
            print(f"  Input tokens: {completion.usage.prompt_tokens}")
            print(f"  Output tokens: {completion.usage.completion_tokens}")
            print(f"  Total tokens: {completion.usage.total_tokens}")
            
            # OpenRouter includes cost in the usage object
            if hasattr(completion.usage, 'cost') and completion.usage.cost:
                openrouter_cost = completion.usage.cost
                print(f"  Cost (from OpenRouter): ${openrouter_cost:.6f}")
        
        # Pass the OpenRouter cost to Langfuse
        if openrouter_cost:
            from langfuse.decorators import langfuse_context
            langfuse_context.update_current_observation(
                metadata={
                    "openrouter_cost": openrouter_cost,
                    "openrouter_cost_usd": f"${openrouter_cost:.6f}"
                }
            )
            print(f"  → Cost logged to Langfuse metadata!")
        
        print("\n✅ Call successful. Check Langfuse dashboard for trace data.")
        print("   Token usage and cost should be visible in the dashboard.")
        
        return completion.choices[0].message.content
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise

def main():
    verify_cost_tracking()
    
    # Flush traces to ensure they're sent
    print("\nFlushing Langfuse traces...")
    from langfuse import Langfuse
    lf = Langfuse(host=settings.LANGFUSE_BASE_URL.replace("localhost", "127.0.0.1"))
    lf.flush()
    print("Done!")

if __name__ == "__main__":
    main()
