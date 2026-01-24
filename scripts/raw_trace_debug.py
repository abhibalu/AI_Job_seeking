
from datetime import datetime
import os
import sys
import requests
import json
import base64
import uuid

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.settings import settings

pk = settings.LANGFUSE_PUBLIC_KEY
sk = settings.LANGFUSE_SECRET_KEY
host = "http://127.0.0.1:3010"
auth = base64.b64encode(f"{pk}:{sk}".encode()).decode()

url = f"{host}/api/public/ingestion"
trace_id = str(uuid.uuid4())

print(f"Sending trace {trace_id} to {url}")
print(f"Public Key: {pk}")

payload = {
    "batch": [
        {
            "id": str(uuid.uuid4()),
            "type": "trace-create",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "body": {
                "id": trace_id,
                "name": "raw-http-debug-trace",
                "userId": "raw-debug-user"
            }
        }
    ],
    "metadata": {
        "sdk_integration": "custom",
        "sdk_name": "python-requests",
        "sdk_version": "0.0.0",
        "public_key": pk
    }
}

try:
    response = requests.post(
        url,
        json=payload,
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json"
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Body: {response.text}")
except Exception as e:
    print(f"Error: {e}")
