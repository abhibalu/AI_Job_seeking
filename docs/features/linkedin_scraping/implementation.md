# Level 3 (Implementation): LinkedIn Job Scraping

[Go Up to Level 2 (Architecture)](./architecture.md)

## Technical Deep-Dive

### 1. External Service Integration (`services/scraper_service.py`)
The implementation uses **Apify** as the external scraping engine. Due to the long-running nature of browser automation, the service implements an asynchronous polling pattern.

**Implementation Details:**
- **Actor ID:** `hKByXkMQaC5Qt9UMN` (Specific LinkedIn Scraper).
- **Polling Loop:** Retries up to 60 times with a 5-second interval (5-minute timeout).
- **Endpoint:** Uses `POST /v2/acts/{actorId}/runs` to start and `GET /v2/actor-runs/{run_id}` to check status.

### 2. Data Mapping & Persistence
Once data is fetched, it passes through a multi-stage transformation:
1.  **Silver Mapping (`lakehouse/silver.py`)**: Sanitizes the raw Apify output.
2.  **Gold Mapping (`services/job_mapper.py`)**: Transforms the record into the final database-ready format.
3.  **Upsert Logic**: Uses Supabase `on_conflict="id"` to prevent duplicate job records while updating existing ones.

> [!NOTE]
> **Production Status:** The *parsing logic* (Silver/Gold functions) is **Active** and used for immediate DB ingestion. However, the Delta Lakehouse infrastructure (`DeltaTable` writes in `silver.py` and `gold.py`) appears to be **Deprecated / Not in Use** in the current production pipeline.

### 3. CLI Helper (`scripts/scrape_jobs.py`)
A standalone script exists for batch processing. It uses a different "Sync" API endpoint for immediate results when dealing with smaller batches.

> [!NOTE]
> **Production Status:** **Active** (Experimental). Used primarily for technical verification and batch seeds.

## System State Transition
- **Before:** The user provides a URL to the `ScraperService.scrape_and_import()` method.
- **After:** The `jobs` table in Supabase is populated, and a summary payload (count, first_job details) is returned to the caller.

## Drill Down
*This is the terminal layer of the Documentation Engine.*
