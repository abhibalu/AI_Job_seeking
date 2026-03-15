# Level 1 (Logic): LinkedIn Job Scraping

[Go Up to README](../../README.md)

## The Mental Model
Acquiring high-fidelity job data is the foundation of the tailoring process. LinkedIn scraping is treated as a **Managed Data Ingestion** feature. Instead of trying to bypass complex bot-detection locally, the system delegates the extraction to a specialized "Scraping Agent" (External Cloud Provider). 

The mental model is: **URL in, Jobs out**. The system treats LinkedIn not just as a page to view, but as a raw data source that needs to be "mined," "normalized," and "persisted" into the internal Lakehouse for downstream agents.

## System State Transition

| Phase | State |
| :--- | :--- |
| **Pre-Condition** | A user-provided LinkedIn Search URL or specific Job URL is identified for ingestion. |
| **Process** | The "Cloud Scraper" extracts raw HTML/JSON; the "Mapper" translates the foreign schema into a universal LinkedIn "Silver" record. |
| **Post-Condition** | A structured Job record is persisted in the internal database, including a `raw_json` snapshot for potential future re-extraction. |

## Workflow Chain
1. **The Intent Trigger**: A URL is received by the system (via CLI or API).
2. **Delegated Extraction**: The system triggers a remote actor to handle the heavy lifting of browser automation and data extraction.
3. **Synchronous Polling**: The system waits (waits/polls) for the cloud actor to complete its job, ensuring data is ready before proceeding.
4. **Lakehouse Mapping**: The raw, messy data from LinkedIn is mapped to a strict internal schema, including title normalization and description cleaning.

## Drill Down
- [Level 2 (Architecture): Scraper Boundaries and Data Mapping](./architecture.md)
- [Level 3 (Implementation): Apify Integration and Worker Logic](./implementation.md)
