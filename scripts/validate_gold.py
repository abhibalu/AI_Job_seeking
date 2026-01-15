
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from data_validation.engine import ValidationEngine
from data_validation.validators import DataValidator
from backend.settings import settings

def main():
    print("Initializing DuckDB Validation Engine...")
    engine = ValidationEngine()
    validator = DataValidator(engine)
    
    # 1. Register Gold Table (MinIO)
    gold_path = f"s3://{settings.DELTA_LAKEHOUSE_BUCKET}/gold/jobs"
    print(f"Registering Gold Table from: {gold_path}")
    engine.register_gold_table("gold_jobs", gold_path)
    
    # 2. Load App Tables (Postgres/Supabase)
    print("Loading Application Table: jobs")
    engine.load_app_table("jobs", alias="app_jobs")
    
    # 3. Run Checks
    # a. Row Count
    validator.validate_row_counts("gold_jobs", "app_jobs")
    
    # b. Data Loss Check (Gold IDs missing in App)
    # Gold typically uses 'job_id', Postgres 'jobs' table uses 'id' usually.
    validator.check_missing_ids("gold_jobs", "app_jobs", id_col="id", app_id_col="id")
    
    print("\nValidation Complete.")

if __name__ == "__main__":
    main()
