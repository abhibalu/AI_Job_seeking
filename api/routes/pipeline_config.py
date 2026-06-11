"""
Per-stage pipeline mode (OotoCV) — GET/PATCH /api/pipeline/config.

Three modes (`scrape_mode`, `evaluate_mode`, `tailor_mode` ∈ {auto, manual})
plus `auto_send_threshold` (0..4). Distinct from kill switches (ADR-0019):
modes are user-facing operating toggles; kill switches are operator-facing
safety. See ADR-0024.
"""
import logging
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.database import get_pipeline_config, set_pipeline_config

logger = logging.getLogger(__name__)
router = APIRouter()


_Mode = Literal["auto", "manual"]


class PipelineConfigUpdate(BaseModel):
    scrape_mode:         Optional[_Mode] = None
    evaluate_mode:       Optional[_Mode] = None
    tailor_mode:         Optional[_Mode] = None
    auto_send_threshold: Optional[int]   = Field(default=None, ge=0, le=4)


@router.get("/config")
def read_pipeline_config():
    return get_pipeline_config()


@router.patch("/config")
def update_pipeline_config(body: PipelineConfigUpdate):
    payload = {k: v for k, v in body.model_dump().items() if v is not None}
    if not payload:
        return get_pipeline_config()
    try:
        return set_pipeline_config(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
