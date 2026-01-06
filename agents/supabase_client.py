"""
Supabase client for TailorAI.

Provides connection to Supabase for storing evaluation results.
"""
from functools import lru_cache

from supabase import create_client, Client

from backend.settings import settings


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Get a cached Supabase client instance."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment"
        )
    
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_KEY
    )


def check_connection() -> bool:
    """Test Supabase connection."""
    try:
        client = get_supabase_client()
        # Try a simple query
        client.table("jobs").select("id").limit(1).execute()
        return True
    except Exception as e:
        print(f"Supabase connection error: {e}")
        return False
