# Feature: linkedin_scraping

## 1. Logic (The Mental Model)

Acquiring high-fidelity job data is the foundation of the tailoring process. LinkedIn scraping is treated as a **Managed Data Ingestion** feature. Instead of trying to bypass complex bot-detection locally, the system delegates the extraction to a specialized "Scraping Agent" (External Cloud Provider). 

The mental model is: **URL in, Jobs out**. The system treats LinkedIn not just as a page to view, but as a raw data source that needs to be "mined," "normalized," and "persisted" into the internal Lakehouse for downstream agents.

### System State Transition

| Phase | State |
| :--- | :--- |
| **Pre-Condition** | A user-provided LinkedIn Search URL or specific Job URL is identified for ingestion. |
| **Process** | The "Cloud Scraper" extracts raw HTML/JSON; the "Mapper" translates the foreign schema into a universal LinkedIn "Silver" record. |
| **Post-Condition** | A structured Job record is persisted in the internal database, including a `raw_json` snapshot for potential future re-extraction. |

### Workflow Chain
1. **The Intent Trigger**: A URL is received by the system (via CLI or API).
2. **Delegated Extraction**: The system triggers a remote actor to handle the heavy lifting of browser automation and data extraction.
3. **Synchronous Polling**: The system waits (waits/polls) for the cloud actor to complete its job, ensuring data is ready before proceeding.
4. **Lakehouse Mapping**: The raw, messy data from LinkedIn is mapped to a strict internal schema, including title normalization and description cleaning.

## 2. Architecture & Contracts

### Component Boundaries
The scraping pipeline is designed around a "Gold-Silver-Bronze" Lakehouse pattern to ensure data integrity and re-processability.

1.  **The Extraction Actor (External)**
    - *Responsibility:* Navigating LinkedIn and returning structured raw JSON.
    - *Boundary:* Interfaced via REST API with Polling mechanisms.

2.  **The Scraper Orchestrator (Internal)**
    - *Responsibility:* Managing the lifecycle of a scraping job (Trigger -> Poll -> Fetch).
    - *Boundary:* Consumes a `URL`. Produces a `List[Raw_JSON]`.

3.  **The Data Normalizer (Lakehouse Layer)**
    - *Responsibility:* Mapping foreign LinkedIn schemas (Silver) to Application-ready schemas (Gold).
    - *Boundary:* Pure transformation logic; ensures fields like `company_name` and `description_text` are cleaned and mapped.

### Data Contracts

#### 1. Ingestion Request
The orchestration service expects a URL of a LinkedIn Job or search result.
```json
{
  "url": "https://www.linkedin.com/jobs/view/..."
}
```

#### 2. Internal Job Schema (The "Gold" Record)
The final output stored in the database follows this contract:
```json
{
  "id": "string (LinkedIn ID)",
  "title": "string",
  "company_name": "string",
  "description_text": "string",
  "raw_json": "object (Original Snapshot)"
}
```

### System State Transition
- **Before:** The system has no knowledge of the specific job opportunity referenced by the URL.
- **After:** A highly structured record exists in the `jobs` table, ready for evaluation and tailoring agents to consume.

## 3. Implementation Details

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

### System State Transition
- **Before:** The user provides a URL to the `ScraperService.scrape_and_import()` method.
- **After:** The `jobs` table in Supabase is populated, and a summary payload (count, first_job details) is returned to the caller.
