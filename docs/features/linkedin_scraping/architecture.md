# Level 2 (Architecture): LinkedIn Job Scraping

[Go Up to Level 1 (Logic)](./logic.md)

## Component Boundaries
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

## Data Contracts

### 1. Ingestion Request
The orchestration service expects a URL of a LinkedIn Job or search result.
```json
{
  "url": "https://www.linkedin.com/jobs/view/..."
}
```

### 2. Internal Job Schema (The "Gold" Record)
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

## System State Transition
- **Before:** The system has no knowledge of the specific job opportunity referenced by the URL.
- **After:** A highly structured record exists in the `jobs` table, ready for evaluation and tailoring agents to consume.

## Drill Down
- [Level 3 (Implementation): Apify Integration and Worker Logic](./implementation.md)
