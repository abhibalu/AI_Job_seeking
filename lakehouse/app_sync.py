import sys
import logging
from datetime import datetime, date
import polars as pl
from deltalake import DeltaTable

# Import settings - assuming running from project root context or path is set up
try:
    from backend.settings import settings
    from agents.supabase_client import get_supabase_client
    from services.job_mapper import map_job_record
    from backend.logging import setup_logging
except ImportError:
    # Fallback for standalone script execution if needed
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from backend.settings import settings
    from agents.supabase_client import get_supabase_client
    from services.job_mapper import map_job_record
    from backend.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

BATCH_SIZE = 100

def get_storage_options() -> dict:
    """Get S3 storage options for Delta Lake."""
    return {
        "AWS_ENDPOINT_URL": f"http://{settings.MINIO_ENDPOINT}",
        "AWS_ACCESS_KEY_ID": settings.MINIO_ACCESS_KEY,
        "AWS_SECRET_ACCESS_KEY": settings.MINIO_SECRET_KEY,
        "AWS_REGION": "us-east-1",
        "AWS_ALLOW_HTTP": "true",
    }

def clean_value(val):
    """Clean value for JSON serialization."""
    if val is None:
        return None
    if isinstance(val, (date, datetime)):
        return val.isoformat()
    return val

def sync_silver_to_app():
    logger.info("Starting Sync: Silver Jobs -> App Database (Upsert)")
    
    if not settings.USE_SUPABASE:
        logger.warning("USE_SUPABASE is False. Skipping Sync.")
        return

    # 1. Load Silver Table
    silver_path = f"s3://{settings.DELTA_LAKEHOUSE_BUCKET}/silver/jobs"
    logger.info(f"Reading Silver table from: {silver_path}")
    
    try:
        dt = DeltaTable(silver_path, storage_options=get_storage_options())
        # Filter for current records only
        df = pl.from_arrow(dt.to_pyarrow_table()).filter(pl.col("is_current") == True)
    except Exception as e:
        logger.critical(f"Failed to load Silver table: {e}", exc_info=True)
        return
        
    total_rows = len(df)
    logger.info(f"Found {total_rows} active records in Silver.")
    
    client = get_supabase_client()
    
    # 2. Get Soft-Deleted Jobs from App DB
    # We must NOT re-insert jobs that the user has marked as 'deleted' or 'archived'
    logger.info("Fetching existing deleted/archived jobs from App DB...")
    ignored_ids = set()
    try:
        # Fetch IDs where status is NOT active
        # Supabase filtering: status.neq.active
        # Page through if necessary, but for now assuming < 100k deleted jobs fits in mem or simple query
        res = client.table("jobs").select("id").neq("status", "active").execute()
        if res.data:
            ignored_ids = {r["id"] for r in res.data}
            logger.info(f"Found {len(ignored_ids)} ignored (deleted/archived) jobs.")
    except Exception as e:
        logger.warning(f"Could not fetch deleted jobs: {e}")

    # 3. Process in Batches
    processed = 0
    errors = 0
    skipped = 0
    
    # Convert to Python dicts for easier iteration
    rows = df.iter_rows(named=True)
    
    batch = []
    
    for row in rows:
        job_id = str(row.get("id"))
        
        # SKIP if in ignored list
        if job_id in ignored_ids:
            skipped += 1
            continue

        # Map Columns (Enhanced Schema using Shared Mapper)
        record = map_job_record(row) 
        
        batch.append(record)
        
        if len(batch) >= BATCH_SIZE:
            try:
                # Upsert
                client.table("jobs").upsert(batch, on_conflict="id").execute()
                processed += len(batch)
                # Use debug for per-batch progress to avoid log spam, or info with \r logic if running interactive
                # Since this is likely background, debug or periodic info is better.
                if processed % 500 == 0:
                     logger.info(f"Synced {processed}/{total_rows} records. Skipped: {skipped}")
                batch = []
            except Exception as e:
                logger.error(f"Error syncing batch: {e}", exc_info=True)
                errors += 1
                batch = []
                
    # Final batch
    if batch:
        try:
            client.table("jobs").upsert(batch, on_conflict="id").execute()
            processed += len(batch)
        except Exception as e:
            logger.error(f"Error syncing final batch: {e}", exc_info=True)
            errors += 1

    logger.info(f"App DB Sync Complete! Processed: {processed}, Skipped: {skipped}, Errors: {errors}")
