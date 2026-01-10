
from data_validation.engine import ValidationEngine

class DataValidator:
    def __init__(self, engine: ValidationEngine):
        self.engine = engine

    def validate_row_counts(self, gold_table: str, app_table: str):
        """Compare row counts between Gold and App tables."""
        print(f"\n--- Validate Row Counts: {gold_table} vs {app_table} ---")
        
        query = f"""
        WITH counts AS (
            SELECT 
                (SELECT COUNT(*) FROM {gold_table}) as gold_count,
                (SELECT COUNT(*) FROM {app_table}) as app_count
        )
        SELECT gold_count, app_count, (gold_count - app_count) as diff FROM counts
        """
        
        df = self.engine.query(query)
        res = df.row(0)
        gold_c, app_c, diff = res
        
        print(f"Gold Count: {gold_c}")
        print(f"App Count:  {app_c}")
        print(f"Difference: {diff}")
        
        if diff == 0:
            print("✅ Row counts match perfectly.")
        else:
            print("❌ Row count mismatch!")
            
        return diff == 0

    def check_missing_ids(self, gold_table: str, app_table: str, id_col: str = "job_id", app_id_col: str = None):
        """Find IDs present in Gold but missing in App."""
        print(f"\n--- Check Missing IDs ({id_col}) ---")
        
        target_app_col = app_id_col or id_col
        
        query = f"""
        SELECT {id_col} FROM {gold_table}
        EXCEPT
        SELECT {target_app_col} FROM {app_table}
        LIMIT 5
        """
        
        df = self.engine.query(query)
        
        if df.height == 0:
            print("✅ All Gold IDs are present in App DB.")
            return True
        else:
            print(f"❌ Found {df.height}+ missing IDs in App DB. Examples:")
            print(df)
            return False
