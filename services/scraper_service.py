import json
import http.client
from typing import Optional, Dict, Any, List
from backend.settings import settings
from services.job_mapper import map_job_record
from agents.supabase_client import get_supabase_client
from lakehouse.silver import parse_raw_json

class ScraperService:
    ACTOR_ID = "hKByXkMQaC5Qt9UMN"
    API_HOST = "api.apify.com"

    @classmethod
    def scrape_and_import(cls, url: str) -> Dict[str, Any]:
        """
        Scrape a single LinkedIn job URL (or search URL) using Apify.
        Maps and upserts all found jobs to Supabase.
        Returns a summary of the operation.
        """
        print(f"Scraping URL: {url}")
        
        # 1. Scrape via Apify
        raw_data = cls._run_apify_sync(url)
        if not raw_data:
            raise Exception("Failed to scrape data from Apify.")
            
        print(f"Scrape successful. Found {len(raw_data)} items.")
        
        # 2. Iterate and Import
        imported_ids = []
        first_job_details = None
        
        client = get_supabase_client()
        
        for job_item in raw_data:
            try:
                # Basic validation
                if not job_item.get("id"):
                    continue

                # Parse & Map
                job_json_str = json.dumps(job_item)
                silver_record = parse_raw_json(job_json_str)
                app_record = map_job_record(silver_record, is_active=True)
                job_id = app_record["id"]
                
                if not job_id:
                    continue

                # Upsert to Supabase
                client.table("jobs").upsert(app_record, on_conflict="id").execute()
                imported_ids.append(job_id)
                
                if not first_job_details:
                    first_job_details = {
                        "id": job_id,
                        "title": app_record.get("title"),
                        "company": app_record.get("company_name")
                    }
                    
            except Exception as e:
                print(f"Failed to import a job item: {e}")
                continue

        if not imported_ids:
             raise Exception("No valid jobs imported from scrape result.")

        return {
            "count": len(imported_ids),
            "first_job": first_job_details, # For UI to show immediate feedback or select
            "ids": imported_ids,
            "id": first_job_details["id"] if first_job_details else None, # Backwards compatibility for frontend
            "status": "imported"
        }

    @classmethod
    def _run_apify_sync(cls, url: str) -> List[Dict]:
        """Run Apify actor synchronously."""
        # Mock Mode for Verification
        if "mock" in url:
            print("DEBUG: Running in MOCK MODE")
            return [{
                "id": "1234567890",
                "trackingId": "track123",
                "title": "Mock Data Engineer",
                "descriptionText": "This is a mock job description for verification.",
                "descriptionHtml": "<p>This is a mock job description.</p>",
                "seniorityLevel": "Mid-Senior level",
                "employmentType": "Full-time",
                "jobFunction": "Engineering",
                "industries": "Technology",
                "companyName": "Mock Company Inc.",
                "companyLinkedinUrl": "https://www.linkedin.com/company/mock-company",
                "companyLogo": "https://via.placeholder.com/100",
                "location": "San Francisco, CA",
                "postedAt": "2025-01-01T12:00:00.000Z",
                "applicantsCount": 10,
                "link": url,
                "applyUrl": url,
                "inputUrl": url,
                "status": "active"
            }]

        if not settings.APIFY_TOKEN:
            raise Exception("APIFY_TOKEN not configured.")

        payload = json.dumps({
            "urls": [url],
            "scrapeCompany": True,
            "count": 100,
        })
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {settings.APIFY_TOKEN}'
        }
        
        conn = http.client.HTTPSConnection(cls.API_HOST)
        endpoint = f"/v2/acts/{cls.ACTOR_ID}/run-sync-get-dataset-items"
        
        try:
            conn.request("POST", endpoint, payload, headers)
            res = conn.getresponse()
            data = res.read()
            
            if res.status not in (200, 201):
                raise Exception(f"Apify API error {res.status}: {data.decode('utf-8')}")
                
            decoded_data = data.decode('utf-8')
            print(f"DEBUG: Apify Response: {decoded_data}")
            return json.loads(decoded_data)
        finally:
            conn.close()
