"""
Export Gold Table to CSV
========================

Reads the Gold 'jobs' table from the Delta Lakehouse and exports it to a CSV file.

Usage:
    python scripts/export_gold_to_csv.py
"""
import sys
import polars as pl
from pathlib import Path
from deltalake import DeltaTable

# Add project root to path to import backend.settings
sys.path.append(str(Path(__file__).parent.parent))

from backend.settings import settings


def get_storage_options() -> dict:
    """Get MinIO/S3 storage options."""
    return {
        "AWS_ENDPOINT_URL": f"http://{settings.MINIO_ENDPOINT}",
        "AWS_ACCESS_KEY_ID": settings.MINIO_ACCESS_KEY,
        "AWS_SECRET_ACCESS_KEY": settings.MINIO_SECRET_KEY,
        "AWS_REGION": "us-east-1",
        "AWS_ALLOW_HTTP": "true",
    }


def main():
    print("--- Exporting Gold Table to CSV ---")
    
    # 1. Define paths
    script_dir = Path(__file__).parent
    output_path = script_dir / "gold_jobs.json"
    
    gold_path = f"s3://{settings.DELTA_LAKEHOUSE_BUCKET}/gold/jobs"
    print(f"Reading from: {gold_path}")
    
    try:
        # 2. Connect to Delta Table
        storage_options = get_storage_options()
        dt = DeltaTable(gold_path, storage_options=storage_options)
        
        # 3. Load into Polars
        df = pl.from_arrow(dt.to_pyarrow_table())
        print(f"Loaded {len(df)} rows.")
        
        # 4. Export to JSON
        print(f"Writing to: {output_path}")
        df.write_json(output_path)
        
        print("Done!")
        
    except Exception as e:
        print(f"Error exporting data: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
