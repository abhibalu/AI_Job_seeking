
import sys
from datetime import datetime, date
import polars as pl
from deltalake import DeltaTable

# Import settings - assuming running from project root context or path is set up
try:
    from backend.settings import settings
    from agents.supabase_client import get_supabase_client
    from services.job_mapper import map_job_record
except ImportError:
    # Fallback for standalone script execution if needed
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from backend.settings import settings
    from agents.supabase_client import get_supabase_client
    from services.job_mapper import map_job_record

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
    print("\n--- Syncing Silver Jobs (Current) to App Database (Upsert) ---")
    
    if not settings.USE_SUPABASE:
        print("ℹ️  USE_SUPABASE is False. Skipping Sync.")
        return

    # 1. Load Silver Table
    silver_path = f"s3://{settings.DELTA_LAKEHOUSE_BUCKET}/silver/jobs"
    print(f"Reading Silver table from: {silver_path}")
    
    try:
        dt = DeltaTable(silver_path, storage_options=get_storage_options())
        # Filter for current records only
        df = pl.from_arrow(dt.to_pyarrow_table()).filter(pl.col("is_current") == True)
    except Exception as e:
        print(f"❌ Failed to load Silver table: {e}")
        return
        
    total_rows = len(df)
    print(f"Found {total_rows} active records in Silver.")
    
    client = get_supabase_client()
    
    # 2. Get Soft-Deleted Jobs from App DB
    # We must NOT re-insert jobs that the user has marked as 'deleted' or 'archived'
    print("Fetching existing deleted/archived jobs from App DB...")
    ignored_ids = set()
    try:
        # Fetch IDs where status is NOT active
        # Supabase filtering: status.neq.active
        # Page through if necessary, but for now assuming < 100k deleted jobs fits in mem or simple query
        res = client.table("jobs").select("id").neq("status", "active").execute()
        if res.data:
            ignored_ids = {r["id"] for r in res.data}
            print(f"found {len(ignored_ids)} ignored (deleted/archived) jobs.")
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch deleted jobs: {e}")

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
        # app_sync.py iterates rows from Silver which are dicts when iter_rows(named=True) is used
        # We need to ensure 'status' logic is consistent or handled by mapper
        # Mapper defaults status to 'active'. 
        # Sync logic here might have custom needs? 
        # The original code: "status": "active", # Force to active if not ignored
        # The mapper does: "status": "active" if is_active else "archived"
        # So calling map_job_record(row) is sufficient as default is_active=True.
        
        batch.append(record)
        
        if len(batch) >= BATCH_SIZE:
            try:
                # Upsert
                client.table("jobs").upsert(batch, on_conflict="id").execute()
                processed += len(batch)
                print(f"Synced {processed}/{total_rows} records... (Skipped: {skipped})", end="\r")
                batch = []
            except Exception as e:
                print(f"\n❌ Error syncing batch: {e}")
                errors += 1
                batch = []
                
    # Final batch
    if batch:
        try:
            client.table("jobs").upsert(batch, on_conflict="id").execute()
            processed += len(batch)
        except Exception as e:
            print(f"\n❌ Error syncing final batch: {e}")
            errors += 1

    print(f"\n✅ App DB Sync Complete! Processed: {processed}, Skipped: {skipped}, Errors: {errors}")
