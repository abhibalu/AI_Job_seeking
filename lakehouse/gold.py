"""
Gold Layer - One Big Table (OBT) for dashboards and LLM

Creates a single wide table with all current job records.
Filters to only is_current = true records from Silver.
"""
import polars as pl
from deltalake import DeltaTable, write_deltalake
import logging
import sys
sys.path.insert(0, '..')
from backend.settings import settings
from backend.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


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
    
    logger.info("Reading Silver table...")
    try:
        silver_df = read_silver_table()
    except Exception as e:
        logger.critical(f"Failed to read silver table: {e}", exc_info=True)
        return

    logger.info(f"Silver table has {len(silver_df)} total records.")
    
    # Filter to current records only
    gold_df = silver_df.filter(pl.col("is_current") == True)
    logger.info(f"Current records: {len(gold_df)}")
    
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
    
    logger.info(f"Writing {len(gold_df)} records to Gold table...")
    
    gold_path = f"s3://{settings.DELTA_LAKEHOUSE_BUCKET}/gold/jobs"
    
    try:
        write_deltalake(
            gold_path,
            gold_df.to_arrow(),
            mode="overwrite",
            schema_mode="overwrite",
            storage_options=storage_options,
        )
        logger.info(f"Successfully wrote Gold OBT with {len(gold_df)} records.")
        logger.debug(f"Delta table location: {gold_path}")
    except Exception as e:
        logger.critical(f"Failed to write Gold table: {e}", exc_info=True)
        return
    
    # Log summary stats
    logger.info("--- Gold Table Summary ---")
    logger.info(f"Total jobs: {len(gold_df)}")
    try:
        unique_companies = gold_df['company_name'].n_unique()
        logger.info(f"Unique companies: {unique_companies}")
        
        if gold_df.height > 0:
            top_companies = (
                gold_df
                .group_by("company_name")
                .count()
                .sort("count", descending=True)
                .head(5)
            )
            logger.info("Top 5 companies by job count:")
            for row in top_companies.iter_rows(named=True):
                logger.info(f"  - {row['company_name']}: {row['count']} jobs")
    except Exception as e:
        logger.warning(f"Failed to calculate summary stats: {e}")

    # 5. Auto-Sync to App Database
    from .app_sync import sync_gold_to_app
    # Note: app_sync already has logging setup, but it might re-run setup_logging if imported.
    # The double setup is harmless usually, or we can check if logger exists. 
    # But since app_sync is usually run standalone often, it has its own logic.
    try:
        sync_gold_to_app()
    except ImportError:
         # Backward compatibility if function name changed or file missing
         logger.warning("sync_gold_to_app not found, skipping auto-sync")
    except Exception as e:
         logger.error(f"Auto-sync failed: {e}", exc_info=True)


if __name__ == "__main__":
    create_gold_table()
