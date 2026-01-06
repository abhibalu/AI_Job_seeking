# TailorAI Data Quality & Reliability Strategy

This document outlines strategies to improve data quality, consistency, and reliability across the TailorAI pipeline.

## 1. Upstream Data Quality (Scraping Layer)

**Problem**: The Apify actor may retrieve jobs from incorrect locations (e.g., US instead of Ireland) or include duplicate/stale listings.

**Strategies**:
- **Strict Location Filtering**:
  - **In-Scraper**: Ensure the Apify run input strictly specifies `location: "Ireland"` (or target region).
  - **Post-Scrape Validation**: Before saving to Bronze/Silver, check the `location` field. Drop records that don't match the allowlist.
- **Deduplication**:
  - **Content Hashing**: Create a hash (SHA256) of `title + company + description_text[0:100]`. Store this as a unique key to prevent re-scraping the same job.
  - **Upsert Logic**: When sinking to Delta Lake, use `merge` operations based on `job_id` or the content hash to update existing records rather than appending duplicates.
- **Staleness**:
  - Add a `scraped_at` timestamp.
  - Filter out jobs older than 30 days during the ingestion process.

## 2. Lakehouse Quality (Bronze/Silver/Gold)

**Problem**: Weak schema enforcement can lead to "garbage in, garbage out" for the LLM.

**Strategies**:
- **Schema Validation (Silver Layer)**:
  - Enforce non-null constraints on critical fields: `title`, `company`, `description`.
  - Filter out descriptions that are too short (< 100 chars) as these are likely parsing errors or "See more" buttons.
- **Partitioning**: Partition the Delta tables by `date` or `region` to make querying efficient and easier to debug.

## 3. Evaluation Quality (LLM Layer)

**Problem**: LLMs can hallucinate or be swayed by prompt wording (e.g., giving a "Strong Match" for a US job when you need Ireland).

**Strategies**:
- **Explicit Constraints**:
  - Modify `JobEvaluatorAgent` system prompt to include "Knockout Rules".
  - *Example*: "If location is NOT Ireland/Remote, Verdict MUST be Weak Match (Score 0)."
- **Structured Output Validation**:
  - Use libraries like `instructor` or Pydantic validation to ensure the LLM returns well-formed JSON every time.
  - Retry logic for malformed JSON (already partially implemented).
- **Confidence Scoring**: Ask the LLM to output a `confidence_score` (0-1) for its evaluation. Flag low-confidence evaluations for manual review.

## 4. Application Logic (API/Backend)

**Problem**: Operations on stale data or "ghost" jobs.

**Strategies**:
- **Soft Deletes**:
  - Implement `is_archived` flag in `job_evaluations`.
  - Do NOT delete from Delta Lake (preserves history).
  - API filters out archived jobs by default.
- **Feedback Loop**:
  - Add a "Report Issue" or "Bad Data" button in the UI.
  - If a user marks a job as "Not a Data Scientist role", save this feedback and use it to fine-tune the scraper or evaluator prompts.

## 5. UI/UX Consistency

**Problem**: Loading states or missing data can confuse users.

**Strategies**:
- **Fallbacks**: Always display "Unknown Company" or placeholders if data is missing, rather than crashing.
- **Stale Data Warning**: If a job was evaluated > 30 days ago, show a warning badge ("Evaluation may be outdated").

## Recommended Next Steps

1.  **Implement Location Check** in `JobEvaluatorAgent` (easiest high-impact win).
2.  **Add Soft Delete** endpoint to clean up the UI.
3.  **Enhance Scraper Config** to be stricter about regions.
