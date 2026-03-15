
import duckdb
from backend.settings import settings

class ValidationEngine:
    def __init__(self):
        """Initialize DuckDB engine with Postgres capabilities."""
        self.conn = duckdb.connect()
        self._setup_extensions()

    def _setup_extensions(self):
        """Install and load necessary extensions."""
        # postgres for direct DB query
        self.conn.install_extension("postgres")
        self.conn.load_extension("postgres")

    def load_app_table(self, table_name: str, alias: str = None):
        """Load an Application Database table into DuckDB (as alias)."""
        target_name = alias or table_name

        # Fetch data via Supabase API -> Polars -> DuckDB
        try:
            from agents.supabase_client import get_supabase_client
            client = get_supabase_client()

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

    def query(self, sql: str):
        """Execute a SQL query and return a Polars DataFrame."""
        return self.conn.sql(sql).pl()
