
import polars as pl
from deltalake import DeltaTable
from backend.settings import settings

def check_gold_data():
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
        
        print(f"Columns: {df.columns}")
        
        if "description_html" in df.columns:
            print("\ndescription_html column FOUND.")
            # Check for non-null values
            non_null = df.filter(pl.col("description_html").is_not_null())
            print(f"Rows with non-null description_html: {non_null.height} / {df.height}")
            
            if non_null.height > 0:
                print("\nSample description_html (first 100 chars):")
                print(non_null["description_html"][0][:100])
            else:
                print("\nWARNING: description_html column exists but all values are null!")
        else:
            print("\nERROR: description_html column NOT found in Gold table.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_gold_data()
