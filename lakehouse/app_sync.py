
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

        # Map Columns (Enhanced Schema)
        record = {
            "id": job_id,
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
            
            # New Fields
            "job_function": row.get("job_function"), # JSON
            "industries": row.get("industries"), # JSON
            "salary_info": row.get("salary_info"),
            "salary_min": None, # Parsing needed if separate
            "salary_max": None,
            "benefits": row.get("benefits"), # JSON
            
            "company_linkedin_url": row.get("company_linkedin_url"),
            "company_logo": row.get("company_logo"),
            "company_description": row.get("company_description"),
            "company_slogan": row.get("company_slogan"),
            "company_employees_count": row.get("company_employees_count"),
            "company_city": row.get("company_city"),
            "company_state": row.get("company_state"),
            "company_country": row.get("company_country"),
            "company_postal_code": row.get("company_postal_code"),
            "company_street_address": row.get("company_street_address"),
            
            "job_poster_name": row.get("job_poster_name"),
            "job_poster_title": row.get("job_poster_title"),
            "job_poster_profile_url": row.get("job_poster_profile_url"),
            
            "apply_url": row.get("apply_url"),
            "input_url": row.get("input_url"),
            
            "status": "active", # Force to active if not ignored
            "updated_at": datetime.now().isoformat() 
        }
        
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
