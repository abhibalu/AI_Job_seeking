"""
Service kill switches — fail-fast guard for external API calls.

Usage:
    from backend.service_guard import require_service
    require_service("openrouter")  # raises 503 if disabled
"""
from fastapi import HTTPException
from agents.database import get_system_config

SERVICE_KEYS = {
    "openrouter": "service_openrouter_enabled",
    "apify": "service_apify_enabled",
    "google_docs": "service_google_docs_enabled",
}


def require_service(service: str) -> None:
    """Raise 503 if service is disabled in system_config. Default: enabled."""
    key = SERVICE_KEYS[service]
    val = get_system_config(key)
    if val == "false":
        raise HTTPException(status_code=503, detail=f"{service} is disabled in settings")


def is_service_enabled(service: str) -> bool:
    """Check if a service is enabled without raising. For use in cron workers."""
    key = SERVICE_KEYS[service]
    val = get_system_config(key)
    return val != "false"
