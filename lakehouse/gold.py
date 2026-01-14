"""
Gold Layer - One Big Table (OBT) for dashboards and LLM

Creates a single wide table with all current job records.
Filters to only is_current = true records from Silver.
"""
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


def read_silver_table() -> pl.DataFrame:
    """Read the Silver Delta table."""
    storage_options = get_storage_options()
    silver_path = f"s3://{settings.DELTA_LAKEHOUSE_BUCKET}/silver/jobs"
    
    dt = DeltaTable(silver_path, storage_options=storage_options)
    return pl.from_arrow(dt.to_pyarrow_table())


def create_gold_table():
    """
    Create Gold OBT from Silver.
    
    Gold table contains only current records (is_current = true)
    and all columns needed for dashboards and LLM consumption.
    """
    storage_options = get_storage_options()
    
    print("Reading Silver table...")
    silver_df = read_silver_table()
    print(f"Silver table has {len(silver_df)} total records.")
    
    # Filter to current records only
    gold_df = silver_df.filter(pl.col("is_current") == True)
    print(f"Current records: {len(gold_df)}")
    
    # Select columns for Gold OBT
    # All Silver columns are useful, just reorder for clarity
    gold_df = gold_df.select([
        # Primary identifiers
        "id",
        "title",
        "company_name",
        
        # Job details
        "description_text",
        "description_html",
        "seniority_level",
        "employment_type",
        "job_function",
        "industries",
        
        # Location
        "location",
        "company_city",
        "company_state",
        "company_country",
        
        # Salary
        "salary",
        "salary_info",
        
        # Posting metrics
        "posted_at",
        "applicants_count",
        
        # Company info
        "company_linkedin_url",
        "company_website",
        "company_description",
        "company_employees_count",
        
        # URLs
        "link",
        "apply_url",
        
        # Job poster
        "job_poster_name",
        "job_poster_title",
        
        # Benefits
        "benefits",
        
        # Metadata
        "_ingestion_timestamp",
        "_source_file",
        "ingestion_date",
        "valid_from",
    ])
    
    print(f"Writing {len(gold_df)} records to Gold table...")
    
    gold_path = f"s3://{settings.DELTA_LAKEHOUSE_BUCKET}/gold/jobs"
    
    write_deltalake(
        gold_path,
        gold_df.to_arrow(),
        mode="overwrite",
        schema_mode="overwrite",
        storage_options=storage_options,
    )
    
    print(f"Successfully wrote Gold OBT with {len(gold_df)} records.")
    print(f"Delta table location: {gold_path}")
    
    # Print summary stats
    print("\n--- Gold Table Summary ---")
    print(f"Total jobs: {len(gold_df)}")
    print(f"Unique companies: {gold_df['company_name'].n_unique()}")
    
    if gold_df.height > 0:
        top_companies = (
            gold_df
            .group_by("company_name")
            .count()
            .sort("count", descending=True)
            .head(5)
        )
        print("\nTop 5 companies by job count:")
        for row in top_companies.iter_rows(named=True):
            print(f"  - {row['company_name']}: {row['count']} jobs")

    # 5. Auto-Sync to App Database
    from .app_sync import sync_gold_to_app
    sync_gold_to_app()


if __name__ == "__main__":
    create_gold_table()
