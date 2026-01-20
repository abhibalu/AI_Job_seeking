from apify_client import ApifyClient
from minio import Minio
from minio.error import S3Error
import json
import logging
from datetime import datetime
from io import BytesIO
from settings import settings
from backend.logging import setup_logging

# Setup logging for standalone script
setup_logging()
logger = logging.getLogger(__name__)

# Initialize the ApifyClient with your API token
client = ApifyClient(settings.APIFY_TOKEN)

# Initialize MinIO client
minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE
)

# Ensure bucket exists
bucket_name = settings.MINIO_BUCKET
try:
    if not minio_client.bucket_exists(bucket_name):
        minio_client.make_bucket(bucket_name)
        logger.info(f"Created bucket: {bucket_name}")
    else:
        logger.debug(f"Bucket {bucket_name} already exists")
except S3Error as e:
    logger.critical(f"Error creating bucket: {e}")
    raise

# Prepare the Actor input
run_input = {
    "urls": [settings.LINKEDIN_URL],
    "scrapeCompany": True,
    "count": 100,
}

# Run the Actor and wait for it to finish
logger.info("Starting Apify scrape...")
try:
    run = client.actor("hKByXkMQaC5Qt9UMN").call(run_input=run_input)
except Exception as e:
    logger.critical(f"Apify actor execution failed: {e}", exc_info=True)
    raise

results = []
# Fetch and print Actor results from the run's dataset (if there are any)
for item in client.dataset(run["defaultDatasetId"]).iterate_items():
    results.append(item)

logger.info(f"Scraped {len(results)} jobs from Apify")

# Create date-based partition path (YYYY-MM-DD)
ingestion_date = datetime.now()
partition_path = ingestion_date.strftime("%Y-%m-%d")
timestamp = ingestion_date.strftime("%H%M%S")
object_name = f"{partition_path}/jobs_{timestamp}.json"

# Convert results to JSON bytes
json_data = json.dumps(results, indent=4)
json_bytes = json_data.encode('utf-8')
json_stream = BytesIO(json_bytes)

# Upload to MinIO
try:
    minio_client.put_object(
        bucket_name,
        object_name,
        json_stream,
        length=len(json_bytes),
        content_type="application/json"
    )
    logger.info(f"Successfully uploaded to MinIO: {bucket_name}/{object_name}", extra={"size_bytes": len(json_bytes)})
except S3Error as e:
    logger.error(f"Error uploading to MinIO: {e}", exc_info=True)
    raise

logger.info("Scraping and upload pipeline complete!")