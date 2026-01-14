# Caching Strategy Design Document

**Status**: Draft
**Date**: 2026-01-14
**Author**: Antigravity (AI Assistant)

## 1. Problem Statement
The current application is experiencing high latency in certain operations. Based on the architecture (FastAPI + Delta Lake + LLMs), the likely bottlenecks are:
1.  **LLM Latency**: Generating evaluations and parsing JDs takes seconds to minutes. Re-running these for the same job is wasteful.
2.  **Data Access Latency**: Reading the Gold Delta table from S3/MinIO for every `list_jobs` request involves I/O and deserialization overhead, especially as the dataset grows.
3.  **Repeated Queries**: Metadata (like resume content) is fetched repeatedly.

## 2. Detailed Data Access Analysis (Audited)

I have audited the `api/routes` and identified the following repeated calls that are prime candidates for caching:

| endpoint / function | Data Source | Frequency | Latency Cost | Cache Strategy |
| :--- | :--- | :--- | :--- | :--- |
| **`GET /api/jobs`** | **Delta Lake (S3/MinIO)** | High | **Medium** (100-500ms)<br>Reads Parquet files on every request. | **Response Cache** (TTL: 5m)<br>Invalidate on pipeline run. |
| **`GET /api/jobs/{id}`** | **Delta Lake (S3/MinIO)** | Medium | **High**<br>Currently loads *entire* table to filter for 1 row. | **Object Cache** (TTL: 1h)<br>Cache individual job dicts. |
| **`POST /api/evaluations/{id}`** | **LLM (OpenRouter)** | Low | **Very High** (10-60s)<br>Expensive API calls. | **Result Cache** (TTL: Infinite)<br>Key: `job_id` + `resume_hash`. |
| **`GET /api/resumes/master`** | **Supabase (Postgres)** | Medium | **Low** (50-100ms)<br>Frequent DB reads. | **Data Cache** (TTL: 1h)<br>Invalidate on update. |
| **`POST /api/resumes/tailor`** | **LLM (OpenRouter)** | Low | **Very High** (30s+)<br>Generating resume content. | **Result Cache**<br>Key: `job_id` + `base_resume_hash`. |

### 2.1. Critical Bottleneck: `load_gold_jobs()`
Located in `api/routes/jobs.py` and `api/routes/evaluations.py`.
```python
def load_gold_jobs():
    dt = DeltaTable(gold_path, ...) # <-- Establishes S3 connection EVERY TIME
    return pl.from_arrow(dt.to_pyarrow_table()) # <-- Reads ENTIRE table into memory
```
**Impact**: As the dataset grows from 100 to 1,000+ jobs, this will paralyze the app.
**Fix**: Cache the `pl.DataFrame` in memory (Valkey) or file-system, or at least cache the serialized API response.

### 2.2. Expensive Compute: `JobEvaluatorAgent.run()`
Located in `api/routes/evaluations.py`.
Even if a user re-evaluates the same job with the same resume, we currently hit the LLM.
**Fix**: Check cache before instantiation:
```python
cache_key = f"eval:{job_id}:{master_resume_version}"
if cache.exists(cache_key): return cache.get(cache_key)
```

## 3. Current Architecture
-   **Backend**: FastAPI
-   **Storage**: 
    -   **Delta Lake (MinIO/S3)**: Primary storage for Jobs (Gold/Silver/Bronze).
    -   **Supabase (PostgreSQL)**: Relational data (User profiles, Resumes, etc.).
    -   **SQLite**: Local dev database (Legacy/Fallback).
-   **Compute**: Local Python environment (Dev).

## 3. Caching Opportunities

### 3.1. LLM Response Caching (High Impact)
**Scenario**: A user clicks "Analyze Match" for Job A. 10 minutes later, they click it again.
**Current**: The system calls OpenRouter API again.
**Proposed**: Cache the `Evaluation` object keyed by `job_id` + `resume_version`.
**Benefit**: Instant response for repeated views; cost savings on API tokens.

### 3.2. Job Feed Caching (Medium Impact)
**Scenario**: `GET /api/jobs` is called frequently.
**Current**: Reads Parquet files from MinIO via DeltaTable.
**Proposed**: Cache the serialized JSON response for page 1 (or the dataframe itself if using Valkey) for X minutes. Invalidate on ingestion events.
**Benefit**: Millisecond response times for the main feed.

### 3.3. Semantic Caching (Advanced)
**Scenario**: User evaluates "Senior Python Engineer" at Company X. Later evaluates "Python Developer" at Company X (very similar JD).
**Proposed**: Vector-based caching to find similar JDs evaluated previously. (Future scope).

## 4. Technology Selection: Valkey vs Redis vs AWS

### 4.1. Valkey (Recommended)
-   **What is it?**: An open-source fork of Redis (created after Redis changed licensing). High performance key-value store.
-   **Pros**: Fully open source (Linux Foundation), drop-in replacement for Redis, high community support.
-   **Cons**: Newer brand (but mature code).

### 4.2. Redis (Standard)
-   **What is it?**: The industry standard for in-memory caching.
-   **Pros**: Ubiquitous, mature, rich ecosystem.
-   **Cons**: Recent licensing changes (RSALv2/SSPL) may concern some commercial users (though typically fine for internal use).

### 4.3. AWS ElastiCache / MemoryDB
-   **What is it?**: Managed Redis/Valkey service.
-   **Pros**: Zero maintenance, auto-scaling, high availability.
-   **Cons**: Cost (hourly billing), requires AWS account setup.

**Recommendation**: Start with a local **Dockerized Valkey/Redis** instance for development. For production, **AWS ElastiCache (Valkey)** is the natural choice if migrating to the cloud.

## 5. Implementation Plan

### Phase 1: Local Docker Setup
1.  Add `compose.yaml` with a Valkey service.
2.  Update `settings.py` to include `CACHE_URL`.

### Phase 2: Backend Integration
1.  **Dependency**: Install `redis-py` (compatible with Valkey).
2.  **Decorator**: Create a `@cache_response(ttl=300)` decorator for FastAPI routes.
3.  **Service Layer**: Wrap expensive functions (like `llm.evaluate_job`) with explicit cache checks:
    ```python
    key = f"eval:{job_id}:{resume_hash}"
    if cached := cache.get(key):
        return json.loads(cached)
    result = llm.evaluate(...)
    cache.set(key, json.dumps(result), ex=86400) # 24h cache
    ```

### Phase 3: Cache Invalidation
1.  When a new resume is set as master, invalidate all evaluation caches (or version them).
2.  When the Gold pipeline runs, invalidate the `list_jobs` cache.

## 6. Draft Dependency Changes
```toml
# requirements.txt
redis>=5.0.0  # Works with Valkey
fastapi-cache2[redis]  # Optional helper
```

## 7. Questions for User
1.  Are you currently running this locally via Docker, or just raw Python/Node processes?
2.  Do you have an AWS account ready for testing, or should we stick to local implementation first?
3.  Is the primary pain point the **List Loading** time or the **Analysis** time?
