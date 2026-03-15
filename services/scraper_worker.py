"""
Scraper Worker — runs on a schedule to discover new jobs.

Flow:
  1. For each configured LinkedIn search URL → call Apify via ScraperService
  2. Upsert jobs to Supabase (including raw_json)
  3. Log run status to pipeline_runs
  4. Send Telegram alert
"""
import json
import logging
from datetime import datetime, timezone

from backend.settings import settings
from services.scraper_service import ScraperService
from services.pipeline_runs import start_run, finish_run
from services.telegram_notifier import (
    notify_scrape_complete,
    notify_scrape_failed,
)
from agents.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


def _get_search_urls() -> list[str]:
    """
    Return the list of LinkedIn search URLs to scrape.
    Priority:
      1. LINKEDIN_SEARCH_URLS env var (comma-separated, for multiple searches)
      2. LINKEDIN_URL env var (single URL, legacy)
    """
    multi = getattr(settings, "LINKEDIN_SEARCH_URLS", "")
    if multi:
        return [u.strip() for u in multi.split(",") if u.strip()]
    single = getattr(settings, "LINKEDIN_URL", "")
    if single:
        return [single]
    # Default fallback: Data Engineer jobs in Ireland from last 7 days
    return [
        "https://ie.linkedin.com/jobs/search?keywords=Data%20Engineer"
        "&location=Ireland&geoId=104738515&f_TPR=r604800"
    ]


def _get_existing_ids() -> set[str]:
    """Fetch all existing active job IDs from Supabase to calculate 'truly new' count."""
    try:
        client = get_supabase_client()
        result = client.table("jobs").select("id").eq("status", "active").execute()
        return {r["id"] for r in (result.data or [])}
    except Exception as e:
        logger.warning(f"[ScrapeWorker] Could not fetch existing IDs: {e}")
        return set()


def run_scrape_worker() -> None:
    """
    Main entry point called by APScheduler every N hours.
    Runs all configured search URLs sequentially.
    """
    urls = _get_search_urls()
    logger.info(f"[ScrapeWorker] Starting scrape job for {len(urls)} URL(s)")

    run_id = start_run("scrape", metadata={"urls": urls, "url_count": len(urls)})

    total_found = 0
    total_new = 0
    errors = []

    for url in urls:
        try:
            existing_ids_before = _get_existing_ids()
            result = ScraperService.scrape_and_import(url)
            found = result.get("count", 0)
            total_found += found

            # Determine genuinely new jobs (not previously in DB)
            new_ids = set(result.get("ids", [])) - existing_ids_before
            total_new += len(new_ids)

            logger.info(f"[ScrapeWorker] URL done: found={found}, new={len(new_ids)}, url={url[:60]}")
            notify_scrape_complete(found, len(new_ids), url)

        except Exception as e:
            msg = str(e)
            logger.error(f"[ScrapeWorker] Failed for URL {url[:60]}: {msg}", exc_info=True)
            errors.append(msg)
            notify_scrape_failed(msg, url)

    if errors:
        finish_run(
            run_id,
            status="failed" if total_found == 0 else "completed",
            jobs_found=total_found,
            jobs_processed=total_found,
            error_detail="; ".join(errors[:3]),
            metadata={"urls": urls, "new_jobs": total_new},
        )
    else:
        finish_run(
            run_id,
            status="completed",
            jobs_found=total_found,
            jobs_processed=total_found,
            metadata={"urls": urls, "new_jobs": total_new},
        )

    logger.info(f"[ScrapeWorker] Finished. total_found={total_found}, truly_new={total_new}, errors={len(errors)}")
