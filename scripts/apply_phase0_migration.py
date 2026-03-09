"""
Apply Phase 0 migration via Supabase RPC (postgres exec).
Falls back to direct psycopg2 if SUPABASE_DB_URL is set.
"""
import sys
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.settings import settings
from agents.supabase_client import get_supabase_client


MIGRATION_FILE = Path(__file__).parent.parent / "supabase_db/migrations/004_phase0_automation.sql"


def apply_via_supabase_rpc():
    """Apply migration by executing each statement individually via Supabase client."""
    client = get_supabase_client()
    sql = MIGRATION_FILE.read_text()

    # Split on statement boundaries, skip empty
    statements = [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--")]

    print(f"Applying {len(statements)} SQL statements...\n")
    for i, stmt in enumerate(statements, 1):
        # Skip pure comment blocks
        lines = [l for l in stmt.splitlines() if not l.strip().startswith("--")]
        clean = "\n".join(lines).strip()
        if not clean:
            continue
        try:
            # Use rpc execute_sql if available, otherwise use postgrest direct call
            # Supabase Python client doesn't expose raw SQL easily, so we use the
            # REST API /rest/v1/rpc/exec_sql or fall back to psycopg2
            result = client.rpc("exec_sql", {"sql": clean}).execute()
            print(f"  [{i}] ✅  {clean[:60].replace(chr(10), ' ')}...")
        except Exception as e:
            err = str(e)
            # "already exists" errors are safe to ignore for idempotent migrations
            if "already exists" in err.lower() or "duplicate" in err.lower():
                print(f"  [{i}] ⚠️   Already exists (skipped): {clean[:60].replace(chr(10), ' ')}...")
            else:
                print(f"  [{i}] ❌  Error: {err}")
                print(f"       SQL: {clean[:120]}")
                return False
    return True


def apply_via_psycopg2():
    """Apply migration using direct DB connection string."""
    import os
    import psycopg2
    db_url = os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        return False
    sql = MIGRATION_FILE.read_text()
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(sql)
    conn.close()
    print("  ✅  Applied via direct psycopg2 connection.")
    return True


if __name__ == "__main__":
    print(f"Phase 0 Migration: {MIGRATION_FILE.name}")
    print("=" * 60)

    if not MIGRATION_FILE.exists():
        print(f"❌ Migration file not found: {MIGRATION_FILE}")
        sys.exit(1)

    # Try psycopg2 first (most reliable for DDL)
    if apply_via_psycopg2():
        print("\n✅ Phase 0 migration complete via direct connection.")
        sys.exit(0)

    # Fallback: Supabase client RPC
    print("No direct DB URL found. Trying Supabase RPC...")
    success = apply_via_supabase_rpc()
    if success:
        print("\n✅ Phase 0 migration complete via Supabase RPC.")
    else:
        print("\n❌ Migration failed. Please run the SQL manually in the Supabase SQL Editor.")
        print(f"   File: {MIGRATION_FILE}")
        sys.exit(1)
