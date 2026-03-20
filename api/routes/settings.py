"""
Settings routes — service kill switches.
"""
from fastapi import APIRouter

from agents.database import get_system_config, set_system_config
from api.schemas import ServiceTogglesResponse, ServiceTogglesUpdate
from backend.service_guard import SERVICE_KEYS

router = APIRouter()


def _read_toggles() -> dict[str, bool]:
    return {
        service: get_system_config(key) != "false"
        for service, key in SERVICE_KEYS.items()
    }


@router.get("/services", response_model=ServiceTogglesResponse)
def get_service_toggles():
    return _read_toggles()


@router.patch("/services", response_model=ServiceTogglesResponse)
def update_service_toggles(body: ServiceTogglesUpdate):
    updates = body.model_dump(exclude_none=True)
    for service, enabled in updates.items():
        key = SERVICE_KEYS[service]
        set_system_config(key, "true" if enabled else "false")
    return _read_toggles()
