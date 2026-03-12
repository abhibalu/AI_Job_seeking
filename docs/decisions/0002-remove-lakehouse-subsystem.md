# ADR-0002: Remove Lakehouse Subsystem

**Date:** 2026-03-12
**Status:** Accepted

## Problem

A full Bronze-Silver-Gold data pipeline existed (MinIO object storage, Delta Lake tables, 5 lakehouse modules, 5+ scripts, a Streamlit dashboard) but was never called at runtime. Jobs flow directly from Apify to Supabase via `scraper_service.py`. The lakehouse was aspirational infrastructure that added complexity, dependencies, and a Docker container (MinIO) without providing value.

## Analysis

- Traced `scraper_service.py` — it upserts directly to Supabase with `raw_json` preserved in the jobs table
- The `raw_json` column effectively serves as the "Bronze layer" (raw data preservation for reprocessing)
- `parse_raw_json()` was the only function from the lakehouse modules that was actually called at runtime
- MinIO, Delta Lake, and Streamlit added significant dependency weight

## Decision

Delete `lakehouse/`, MinIO docker-compose, the Streamlit dashboard, legacy scraper script, and gold-layer scripts. Move `parse_raw_json()` to `services/job_mapper.py` where it logically belongs alongside `map_job_record()`. Refactor the CLI entrypoint to read from Supabase instead of Delta Lake tables.

## Consequences

- 22 files changed, ~1305 lines removed
- Removed `minio`, `deltalake`, `streamlit` dependencies
- No MinIO container needed in development or production
- `raw_json` column in Supabase serves the data preservation role that Bronze layer was intended for
- If a lakehouse is needed in the future, it should be built as a separate service consuming Supabase change events
