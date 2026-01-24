
import os
import sys
import logging
# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langfuse import Langfuse
from backend.settings import settings

# Configure debug logging
logging.basicConfig(level=logging.DEBUG)

# Force env vars
os.environ["LANGFUSE_PUBLIC_KEY"] = settings.LANGFUSE_PUBLIC_KEY
os.environ["LANGFUSE_SECRET_KEY"] = settings.LANGFUSE_SECRET_KEY
os.environ["LANGFUSE_HOST"] = "http://127.0.0.1:3010"

print("Testing Langfuse Connectivity...")
print(f"Host: {os.environ['LANGFUSE_HOST']}")
print(f"Public Key: {os.environ['LANGFUSE_PUBLIC_KEY']}")

try:
    langfuse = Langfuse()
    
    print("Creating trace...")
    trace = langfuse.trace(
        name="connectivity-debug-trace",
        user_id="debug-user"
    )
    
    print("Creating span...")
    span = trace.span(name="debug-span")
    span.end()
    
    print("Updating trace...")
    trace.update(output="Success")
    
    print("Flushing...")
    langfuse.flush()
    print("Done. Check dashboard.")
    
except Exception as e:
    print(f"❌ Error: {e}")
