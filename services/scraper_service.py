import json
import logging
from typing import Optional, Dict, Any, List
import httpx
from backend.settings import settings
from services.job_mapper import map_job_record, parse_raw_json
from agents.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class ScraperService:
    ACTOR_ID = "hKByXkMQaC5Qt9UMN"
    API_HOST = "api.apify.com"

    @classmethod
    def scrape_and_import(cls, url: str, run_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Scrape a single LinkedIn job URL (or search URL) using Apify.
        Maps and upserts all found jobs to Supabase.
        Returns a summary of the operation.

        If `run_id` is provided, every imported job row is stamped with
        `run_id` so the OotoCV feed can group jobs under their scrape run
        (ADR-0025). Manual single-URL imports from the UI omit it; the
        corresponding `jobs.run_id` stays NULL and the UI buckets it under
        "Pre-runs".

        Raises HTTPException(503) if Apify service is disabled.
        """
        from backend.service_guard import require_service
        require_service("apify")
        logger.info(f"Scraping URL: {url}")
        
        # 1. Scrape via Apify
        raw_data = cls._run_apify_sync(url)
        if not raw_data:
            logger.error("Failed to scrape data from Apify via synchronous run")
            raise Exception("Failed to scrape data from Apify.")
            
        logger.info(f"Scrape successful. Found {len(raw_data)} items.")
        
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

                # Persist raw_json alongside the mapped record (Bronze-layer safety net)
                # Allows future reprocessing without re-scraping
                app_record["raw_json"] = job_item

                # Stamp the producing pipeline_runs id for OotoCV feed grouping.
                # Only set when present so manual imports keep run_id NULL
                # (and do not violate the FK with a fake id).
                if run_id:
                    app_record["run_id"] = run_id

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
                logger.error(f"Failed to import a job item: {e}", exc_info=True)
                continue

        if not imported_ids:
             logger.warning("No valid jobs imported from scrape result")
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
            logger.warning("Running in MOCK MODE for scraper")
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
            logger.critical("APIFY_TOKEN not configured")
            raise Exception("APIFY_TOKEN not configured.")

        # Always use polling instead of run-sync to avoid RemoteDisconnected timeouts
        url_run = f"https://{cls.API_HOST}/v2/acts/{cls.ACTOR_ID}/runs"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {settings.APIFY_TOKEN}",
        }
        payload = {
            "urls": [url],
            "scrapeCompany": True,
            "count": 100,
        }

        import time
        try:
            with httpx.Client(timeout=30.0) as client:
                # 1. Start the run
                resp = client.post(url_run, json=payload, headers=headers)
                if resp.status_code not in (200, 201):
                    logger.error(f"Apify start error {resp.status_code}: {resp.text[:300]}")
                    raise Exception(f"Apify start error {resp.status_code}: {resp.text[:300]}")

                run_data = resp.json()["data"]
                run_id = run_data["id"]
                dataset_id = run_data["defaultDatasetId"]
                logger.info(f"Apify async run started: {run_id}. Polling for completion...")

                # 2. Poll for completion
                max_polls = 60 # 60 * 5s = 5 mins timeout
                url_status = f"https://{cls.API_HOST}/v2/actor-runs/{run_id}"
                
                for _ in range(max_polls):
                    time.sleep(5)
                    poll_resp = client.get(url_status, headers=headers)
                    if poll_resp.status_code == 200:
                        status = poll_resp.json()["data"]["status"]
                        if status == "SUCCEEDED":
                            break
                        elif status in ("FAILED", "ABORTED", "TIMED-OUT"):
                            raise Exception(f"Apify run {run_id} failed with status: {status}")
                    else:
                        logger.warning(f"Apify poll error: {poll_resp.status_code}")
                else:
                    raise Exception(f"Apify run {run_id} timed out after 5 minutes of polling.")

                # 3. Fetch the results
                logger.info(f"Apify run {run_id} succeeded. Fetching dataset...")
                url_items = f"https://{cls.API_HOST}/v2/datasets/{dataset_id}/items"
                ds_resp = client.get(url_items, headers=headers)
                
                if ds_resp.status_code != 200:
                    raise Exception(f"Failed to fetch Apify dataset: {ds_resp.status_code}")
                
                items = ds_resp.json()
                logger.debug(f"Apify dataset fetched: {len(items)} items")
                return items

        except httpx.RequestError as e:
            raise Exception(f"Apify connection error during polling: {e}") from e
