
import polars as pl
from deltalake import DeltaTable
from backend.settings import settings
import os

def check_schema():
    print(f"Checking Gold schema from bucket: {settings.DELTA_LAKEHOUSE_BUCKET}")
    
    storage_options = {
        "AWS_ENDPOINT_URL": f"http://{settings.MINIO_ENDPOINT}",
        "AWS_ACCESS_KEY_ID": settings.MINIO_ACCESS_KEY,
        "AWS_SECRET_ACCESS_KEY": settings.MINIO_SECRET_KEY,
        "AWS_REGION": "us-east-1",
        "AWS_ALLOW_HTTP": "true",
    }
    
    gold_path = f"s3://{settings.DELTA_LAKEHOUSE_BUCKET}/gold/jobs"
    
    try:
        dt = DeltaTable(gold_path, storage_options=storage_options)
        df = pl.from_arrow(dt.to_pyarrow_table())
        print("Columns found in Gold table:")
        print(df.columns)
        print("\nFirst row sample:")
        print(df.head(1))
    except Exception as e:
        print(f"Error reading Gold table: {e}")

if __name__ == "__main__":
    check_schema()
