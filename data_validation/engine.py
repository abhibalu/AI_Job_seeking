
import duckdb
from backend.settings import settings

class ValidationEngine:
    def __init__(self):
        """Initialize DuckDB engine with S3 and Postgres capabilities."""
        self.conn = duckdb.connect()
        self._setup_extensions()
        self._configure_s3()
        # Postgres setup is on-demand via attach, or we can do it here

    def _setup_extensions(self):
        """Install and load necessary extensions."""
        # httpfs for S3 access
        self.conn.install_extension("httpfs")
        self.conn.load_extension("httpfs")
        # postgres for direct DB query
        self.conn.install_extension("postgres")
        self.conn.load_extension("postgres")

    def _configure_s3(self):
        """Configure S3 credentials for MinIO access."""
        # DuckDB requires specific s3 config
        self.conn.execute(f"""
            SET s3_endpoint='{settings.MINIO_ENDPOINT}';
            SET s3_access_key_id='{settings.MINIO_ACCESS_KEY}';
            SET s3_secret_access_key='{settings.MINIO_SECRET_KEY}';
            SET s3_use_ssl='false';
            SET s3_url_style='path';
        """)

    def load_app_table(self, table_name: str, alias: str = None):
        """Load an Application Database table into DuckDB (as alias)."""
        target_name = alias or table_name
        
        if settings.USE_SUPABASE:
            # Hybrid approach: Fetch data via API -> Arrow -> DuckDB
            try:
                from agents.supabase_client import get_supabase_client
                client = get_supabase_client()
                
                # Fetch all rows (warning: large tables might need pagination)
                # Using csv export from supabase might be faster, but API is easiest
                response = client.table(table_name).select("*").execute()
                
                if response.data:
                    import polars as pl
                    df = pl.DataFrame(response.data)
                    # Register as virtual table
                    self.conn.register(target_name, df)
                    print(f"Registered Supabase table '{table_name}' as '{target_name}' via API ({len(df)} rows)")
                else:
                    print(f"Warning: Table '{table_name}' is empty or not found.")
            except Exception as e:
                print(f"Error loading Supabase table: {e}")
        else:
            # SQLite approach: Attach DB file directly
            db_path = settings.EVAL_DB_PATH
            try:
                # Install sqlite extension if not present - duckdb usually builds it in
                self.conn.install_extension("sqlite") 
                self.conn.load_extension("sqlite")
                
                # Attach ONLY once
                try:
                    self.conn.sql(f"ATTACH '{db_path}' AS app_db (TYPE SQLITE)")
                except duckdb.BinderException:
                    pass # Already attached
                
                # Create view/alias to simplify access
                self.conn.sql(f"CREATE OR REPLACE VIEW {target_name} AS SELECT * FROM app_db.{table_name}")
                print(f"Attached SQLite table '{table_name}' as '{target_name}'")
            except Exception as e:
                 print(f"Error attaching SQLite DB: {e}")

    def register_gold_table(self, table_name: str, s3_path: str):
        """Register a Delta Table from S3 as a view."""
        # DuckDB's native Delta Lake reader or Parquet reader
        # If it's a Delta Table, we might need delta extension or read parquet files directly.
        # For simplicity, if we use 'delta' extension:
        # self.conn.install_extension("delta")
        # self.conn.load_extension("delta")
        # self.conn.execute(f"CREATE OR REPLACE VIEW {table_name} AS SELECT * FROM delta_scan('{s3_path}')")
        
        # Using parquet glob as fallback (works for non-transactional reads of latest state often)
        # But 'delta_scan' is safer.
        try:
             self.conn.install_extension("delta")
             self.conn.load_extension("delta")
             self.conn.execute(f"CREATE OR REPLACE VIEW {table_name} AS SELECT * FROM delta_scan('{s3_path}')")
        except Exception as e:
             print(f"Delta extension warning: {e}. Fallback to parquet glob (risky for transactional tables).")
             # Fallback logic if needed
             pass

    def query(self, sql: str):
        """Execute a SQL query and return a Polars DataFrame."""
        return self.conn.sql(sql).pl()
