"""
Silver Layer - Cleaned and transformed data with SCD Type 2

Transforms Bronze → Silver with:
- Explicit schema (flattened address)
- Type conversions (dates, integers)
- SCD Type 2 for tracking changes
"""
import json
from datetime import datetime

import polars as pl
from deltalake import DeltaTable, write_deltalake

import sys
sys.path.insert(0, '..')
from backend.settings import settings


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


def parse_raw_json(raw_json: str) -> dict:
    """Parse raw JSON string and extract/flatten fields."""
    job = json.loads(raw_json)
    
    # Extract company address (flatten)
    address = job.get("companyAddress", {}) or {}
    
    return {
        # Core identifiers
        "id": job.get("id"),
        "tracking_id": job.get("trackingId"),
        
        # Job details
        "title": job.get("title"),
        "description_text": job.get("descriptionText"),  # Discard HTML
        "seniority_level": job.get("seniorityLevel"),
        "employment_type": job.get("employmentType"),
        "job_function": job.get("jobFunction"),
        "industries": job.get("industries"),
        
        # Company info
        "company_name": job.get("companyName"),
        "company_linkedin_url": job.get("companyLinkedinUrl"),
        "company_logo": job.get("companyLogo"),
        "company_website": job.get("companyWebsite"),
        "company_description": job.get("companyDescription"),
        "company_slogan": job.get("companySlogan"),
        "company_employees_count": job.get("companyEmployeesCount"),
        
        # Flattened address
        "company_street_address": address.get("streetAddress"),
        "company_city": address.get("addressLocality"),
        "company_state": address.get("addressRegion"),
        "company_postal_code": address.get("postalCode"),
        "company_country": address.get("addressCountry"),
        
        # Location & salary
        "location": job.get("location"),
        "salary": job.get("salary"),
        "salary_info": job.get("salaryInfo"),
        
        # Posting info
        "posted_at": job.get("postedAt"),
        "applicants_count": job.get("applicantsCount"),
        
        # URLs
        "link": job.get("link"),
        "apply_url": job.get("applyUrl"),
        "input_url": job.get("inputUrl"),
        
        # Job poster info (optional)
        "job_poster_name": job.get("jobPosterName"),
        "job_poster_title": job.get("jobPosterTitle"),
        "job_poster_profile_url": job.get("jobPosterProfileUrl"),
        
        # Benefits
        "benefits": job.get("benefits"),
    }


def read_bronze_table() -> pl.DataFrame:
    """Read the Bronze Delta table."""
    storage_options = get_storage_options()
    bronze_path = f"s3://{settings.DELTA_LAKEHOUSE_BUCKET}/bronze/jobs"
    
    dt = DeltaTable(bronze_path, storage_options=storage_options)
    return pl.from_arrow(dt.to_pyarrow_table())


def read_silver_table() -> pl.DataFrame | None:
    """Read existing Silver table, or return None if doesn't exist."""
    storage_options = get_storage_options()
    silver_path = f"s3://{settings.DELTA_LAKEHOUSE_BUCKET}/silver/jobs"
    
    try:
        dt = DeltaTable(silver_path, storage_options=storage_options)
        return pl.from_arrow(dt.to_pyarrow_table())
    except Exception:
        return None


def transform_to_silver():
    """
    Transform Bronze to Silver with SCD Type 2.
    
    SCD Type 2 tracks changes by:
    - valid_from: when this version became active
    - valid_to: when this version was superseded (null if current)
    - is_current: boolean flag for easy filtering
    """
    storage_options = get_storage_options()
    
    print("Reading Bronze table...")
    bronze_df = read_bronze_table()
    print(f"Bronze table has {len(bronze_df)} records.")
    
    # Parse raw JSON into structured columns
    print("Parsing and transforming records...")
    parsed_records = []
    
    for row in bronze_df.iter_rows(named=True):
        parsed = parse_raw_json(row["raw_json"])
        parsed["_ingestion_timestamp"] = row["_ingestion_timestamp"]
        parsed["_source_file"] = row["_source_file"]
        parsed["ingestion_date"] = row["ingestion_date"]
        parsed_records.append(parsed)
    
    # Create DataFrame with explicit schema
    new_df = pl.DataFrame(parsed_records)
    
    # Type conversions
    new_df = new_df.with_columns([
        # Convert posted_at to Date
        pl.col("posted_at").str.to_date(format="%Y-%m-%d", strict=False).alias("posted_at"),
        
        # Convert applicants_count to Int
        pl.col("applicants_count").cast(pl.Int64, strict=False).alias("applicants_count"),
        
        # Convert company_employees_count to Int
        pl.col("company_employees_count").cast(pl.Int64, strict=False).alias("company_employees_count"),
    ])
    
    # Read existing Silver table for SCD Type 2 merge
    existing_silver = read_silver_table()
    now = datetime.now()
    
    if existing_silver is None:
        # First run: all records are new
        print("No existing Silver table. Creating initial load...")
        
        silver_df = new_df.with_columns([
            pl.lit(now).alias("valid_from"),
            pl.lit(None).cast(pl.Datetime).alias("valid_to"),
            pl.lit(True).alias("is_current"),
        ])
    else:
        print(f"Existing Silver table has {len(existing_silver)} records.")
        
        # Get unique job IDs from new data
        new_job_ids = set(new_df["id"].to_list())
        
        # Find changed records (same ID, different ingestion)
        # For SCD Type 2: close old records and insert new versions
        
        # Records in existing that are being updated
        updated_existing = existing_silver.filter(
            (pl.col("id").is_in(new_job_ids)) & (pl.col("is_current") == True)
        ).with_columns([
            pl.lit(now).alias("valid_to"),
            pl.lit(False).alias("is_current"),
        ])
        
        # Records in existing that are NOT being updated (keep as-is)
        unchanged_existing = existing_silver.filter(
            ~((pl.col("id").is_in(new_job_ids)) & (pl.col("is_current") == True))
        )
        
        # New records
        new_records = new_df.with_columns([
            pl.lit(now).alias("valid_from"),
            pl.lit(None).cast(pl.Datetime).alias("valid_to"),
            pl.lit(True).alias("is_current"),
        ])
        
        # Combine all
        silver_df = pl.concat([unchanged_existing, updated_existing, new_records], how="diagonal")
    
    print(f"Writing {len(silver_df)} records to Silver table...")
    
    silver_path = f"s3://{settings.DELTA_LAKEHOUSE_BUCKET}/silver/jobs"
    
    write_deltalake(
        silver_path,
        silver_df.to_arrow(),
        mode="overwrite",  # For SCD we rebuild the table
        partition_by=["ingestion_date"],
        storage_options=storage_options,
    )
    
    print(f"Successfully wrote Silver table with SCD Type 2.")
    print(f"  - Current records: {silver_df.filter(pl.col('is_current') == True).height}")
    print(f"  - Historical records: {silver_df.filter(pl.col('is_current') == False).height}")


if __name__ == "__main__":
    transform_to_silver()
