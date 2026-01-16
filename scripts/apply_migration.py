
import os
import sys
import psycopg2
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

def get_db_url():
    # Use SUPABASE_DB_URL if available (direct connection string)
    # Typically: postgresql://postgres.PROJECT_REF:PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres
    # Ideally should be in .env. If not, we might need to construct it or ask user.
    # For now, let's assume valid DATABASE_URL or SUPABASE_DB_URL is present.
    url = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
    if not url:
        print("Error: SUPABASE_DB_URL or DATABASE_URL not found in .env")
        sys.exit(1)
    return url

def apply_migration():
    migration_file = "supabase_db/migrations/002_enhance_jobs_schema.sql"
    
    if not os.path.exists(migration_file):
        print(f"Error: Migration file {migration_file} not found.")
        sys.exit(1)
        
    print(f"Applying migration: {migration_file}")
    
    try:
        with open(migration_file, 'r') as f:
            sql = f.read()
            
        conn = psycopg2.connect(get_db_url())
        conn.autocommit = True 
        cursor = conn.cursor()
        
        cursor.execute(sql)
        
        print("Migration applied successfully!")
        
        conn.close()
        
    except Exception as e:
        print(f"Error applying migration: {e}")
        sys.exit(1)

if __name__ == "__main__":
    apply_migration()
