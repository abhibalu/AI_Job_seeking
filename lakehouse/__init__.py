"""
TailorAI Lakehouse Module

Medallion architecture for job data:
- Bronze: Raw JSON ingestion
- Silver: Cleaned + SCD Type 2
- Gold: OBT for dashboards and LLM
"""

from .bronze import ingest_to_bronze
from .silver import transform_to_silver
from .gold import create_gold_table

__all__ = ["ingest_to_bronze", "transform_to_silver", "create_gold_table"]
