import os
import json
import argparse
import http.client
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- CONFIGURATION ---
# Add your URLs here
URLS = [
    "https://ie.linkedin.com/jobs/search?keywords=Data%20Engineer&location=Ireland&geoId=104738515&f_TPR=r604800&position=1&pageNum=0"
]

APIFY_TOKEN = os.getenv("APIFY_TOKEN")
ACTOR_ID = "hKByXkMQaC5Qt9UMN"
# ---------------------

def main():
    parser = argparse.ArgumentParser(description="Scrape jobs using Apify (Sync HTTP).")
    parser.add_argument("--output", help="Output JSON filename", default=None)
    args = parser.parse_args()

    if not APIFY_TOKEN:
        print("Error: APIFY_TOKEN not found in environment variables.")
        return

    if not URLS:
        print("Error: No URLs defined in the script. Please add URLs to the URLS list.")
        return

    print(f"Starting Apify scrape for {len(URLS)} URLs using raw HTTP...")

    # Prepare the payload
    run_input = {
        "urls": URLS,
        "scrapeCompany": True,
        "count": 100,
    }
    payload = json.dumps(run_input)

    # Prepare headers
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {APIFY_TOKEN}'
    }

    try:
        # Establish connection
        conn = http.client.HTTPSConnection("api.apify.com")
        
        # Endpoint: /v2/acts/{actorId}/run-sync-get-dataset-items
        endpoint = f"/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items"
        
        print(f"Sending POST request to {endpoint}...")
        conn.request("POST", endpoint, payload, headers)
        
        # Get response
        res = conn.getresponse()
        data = res.read()
        
        if res.status != 201: # 201 Created is typical for run-sync, but 200 might be returned for get-dataset-items? Docs say 201 for run.
             # Actually run-sync-get-dataset-items returns 201 Created on success usually.
             print(f"Request failed with status {res.status}: {res.reason}")
             print(f"Response: {data.decode('utf-8')}")
             return

        decoded_data = data.decode("utf-8")
        results = json.loads(decoded_data)
        
        # The response from run-sync-get-dataset-items is commonly the list of items itself 
        # or an object containing the items depending on configuration, 
        # but usually it's the items if using defaults. 
        # However, checking the user provided snippet: `data = res.read(); print(data.decode("utf-8"))`
        # implies they expect the raw JSON. 
        # If it's a list, great. If it's a dict with 'data', we might need to adjust.
        # But standard Apify run-sync-get-dataset-items returns the array of items.
        
        if isinstance(results, list):
             print(f"Scraped {len(results)} jobs")
        else:
             print("Received response (not a list), saving as is.")

    except Exception as e:
        print(f"Error executing HTTP request: {e}")
        return
    finally:
        if 'conn' in locals():
            conn.close()

    # Determine output filename
    if args.output:
        output_filename = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"jobs_{timestamp}.json"

    # Save to JSON
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=4)
        print(f"Results saved to {output_filename}")
    except IOError as e:
        print(f"Error saving results to file: {e}")

if __name__ == "__main__":
    main()
