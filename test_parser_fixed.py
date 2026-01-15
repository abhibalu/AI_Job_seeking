import os
import httpx
import json

# Hardcoded valid settings
API_KEY = os.environ.get("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "meta-llama/llama-3.1-8b-instruct:free"

def run():
    print(f"Testing direct HTTP request to {BASE_URL}")
    if not API_KEY:
        print("Skipping: No API Key in env")
        # Try to read from file if possible, but I can't here easily without imports.
        # I'll rely on the fact that I'm running in the user's environment which HAS the key?
        # No, 'run_command' allows me to inherit env? 
        # I need to source .env
        return

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://tailorai.test",
    }
    
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "Hello!"}],
    }
    
    try:
        response = httpx.post(BASE_URL, headers=headers, json=payload, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    run()
