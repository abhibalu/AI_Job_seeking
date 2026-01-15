
import sys
from datetime import datetime, date
import polars as pl
from deltalake import DeltaTable

# Import settings - assuming running from project root context or path is set up
try:
    from backend.settings import settings
    from agents.supabase_client import get_supabase_client
except ImportError:
    # Fallback for standalone script execution if needed
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from backend.settings import settings
    from agents.supabase_client import get_supabase_client

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

def sync_gold_to_app():
    print("\n--- Syncing Gold Jobs to App Database (Upsert) ---")
    
    if not settings.USE_SUPABASE:
        print("ℹ️  USE_SUPABASE is False. Skipping Sync.")
        return

    # 1. Load Gold Table
    gold_path = f"s3://{settings.DELTA_LAKEHOUSE_BUCKET}/gold/jobs"
    print(f"Reading Gold table from: {gold_path}")
    
    try:
        dt = DeltaTable(gold_path, storage_options=get_storage_options())
        df = pl.from_arrow(dt.to_pyarrow_table())
    except Exception as e:
        print(f"❌ Failed to load Gold table: {e}")
        return
        
    total_rows = len(df)
    print(f"Found {total_rows} records in Gold.")
    
    client = get_supabase_client()
    
    # 2. Process in Batches
    processed = 0
    errors = 0
    
    # Convert to Python dicts for easier iteration
    rows = df.iter_rows(named=True)
    
    batch = []
    
    for row in rows:
        # Map Columns
        record = {
            "id": str(row.get("id")),
            "company_name": row.get("company_name"),
            "title": row.get("title"),
            "location": row.get("location"),
            "description_text": row.get("description_text"),
            "job_url": row.get("link") or row.get("job_url"),
            "posted_at": clean_value(row.get("posted_at")),
            "seniority_level": row.get("seniority_level"),
            "employment_type": row.get("employment_type"),
            "applicants_count": row.get("applicants_count"),
            "company_website": row.get("company_website"),
            "updated_at": datetime.now().isoformat() 
        }
        
        batch.append(record)
        
        if len(batch) >= BATCH_SIZE:
            try:
                client.table("jobs").upsert(batch, on_conflict="id").execute()
                processed += len(batch)
                print(f"Synced {processed}/{total_rows} records...", end="\r")
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

    print(f"\n✅ App DB Sync Complete! Processed: {processed}, Errors: {errors}")
