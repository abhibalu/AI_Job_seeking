"""
Bronze Layer - Raw JSON ingestion to Delta Lake

Ingests raw JSON files from MinIO (scraped-jobs bucket) into a Delta table.
No transformation, schema-less approach to handle evolving JSON structures.
"""
import json
from datetime import datetime
from io import BytesIO

import polars as pl
from deltalake import DeltaTable, write_deltalake
from minio import Minio

import sys
sys.path.insert(0, '..')
from backend.settings import settings


def get_minio_client() -> Minio:
    """Initialize MinIO client."""
    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )


def get_storage_options() -> dict:
    """Get S3 storage options for Delta Lake."""
    return {
        "AWS_ENDPOINT_URL": f"http://{settings.MINIO_ENDPOINT}",
        "AWS_ACCESS_KEY_ID": settings.MINIO_ACCESS_KEY,
        "AWS_SECRET_ACCESS_KEY": settings.MINIO_SECRET_KEY,
        "AWS_REGION": "us-east-1",
        "AWS_ALLOW_HTTP": "true",
        "AWS_S3_ALLOW_UNSAFE_RENAME": "true",
    }


def list_json_files(client: Minio, bucket: str, prefix: str = "") -> list[str]:
    """List all JSON files in the bucket."""
    objects = client.list_objects(bucket, prefix=prefix, recursive=True)
    return [obj.object_name for obj in objects if obj.object_name.endswith('.json')]


def read_json_from_minio(client: Minio, bucket: str, object_name: str) -> list[dict]:
    """Read JSON file from MinIO and return as list of dicts."""
    response = client.get_object(bucket, object_name)
    data = json.loads(response.read().decode('utf-8'))
    response.close()
    response.release_conn()
    return data if isinstance(data, list) else [data]


def ingest_to_bronze(source_file: str | None = None):
    """
    Ingest raw JSON files from MinIO into Bronze Delta table.
    
    Args:
        source_file: Optional specific file to ingest. If None, ingests all files.
    """
    client = get_minio_client()
    storage_options = get_storage_options()
    
    # Ensure delta-lakehouse bucket exists
    if not client.bucket_exists(settings.DELTA_LAKEHOUSE_BUCKET):
        client.make_bucket(settings.DELTA_LAKEHOUSE_BUCKET)
        print(f"Created bucket: {settings.DELTA_LAKEHOUSE_BUCKET}")
    
    # List JSON files to process
    if source_file:
        json_files = [source_file]
    else:
        json_files = list_json_files(client, settings.MINIO_BUCKET)
    
    if not json_files:
        print("No JSON files found to ingest.")
        return
    
    print(f"Found {len(json_files)} JSON file(s) to ingest.")
    
    all_records = []
    ingestion_timestamp = datetime.now()
    
    for file_path in json_files:
        print(f"Processing: {file_path}")
        
        # Extract ingestion date from file path (e.g., "2025-12-06/jobs_220624.json")
        try:
            date_part = file_path.split('/')[0]  # "2025-12-06"
            ingestion_date = datetime.strptime(date_part, "%Y-%m-%d").date()
        except (IndexError, ValueError):
            ingestion_date = ingestion_timestamp.date()
        
        # Read JSON data
        jobs = read_json_from_minio(client, settings.MINIO_BUCKET, file_path)
        
        # Add metadata to each record
        for job in jobs:
            all_records.append({
                "raw_json": json.dumps(job),  # Store as JSON string (schema-less)
                "_ingestion_timestamp": ingestion_timestamp,
                "_source_file": file_path,
                "ingestion_date": str(ingestion_date),  # Partition column
            })
    
    if not all_records:
        print("No records to ingest.")
        return
    
    # Create Polars DataFrame
    df = pl.DataFrame(all_records)
    
    print(f"Ingesting {len(df)} records to Bronze layer...")
    
    # Write to Delta table
    delta_path = f"s3://{settings.DELTA_LAKEHOUSE_BUCKET}/bronze/jobs"
    
    write_deltalake(
        delta_path,
        df.to_arrow(),
        mode="append",
        partition_by=["ingestion_date"],
        storage_options=storage_options,
    )
    
    print(f"Successfully ingested {len(df)} records to Bronze layer.")
    print(f"Delta table location: {delta_path}")


if __name__ == "__main__":
    ingest_to_bronze()
