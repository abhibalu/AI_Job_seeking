from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path

# Resolve .env path relative to this file's location
ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    APIFY_TOKEN: str = Field(default="", env="APIFY_TOKEN")
    LINKEDIN_URL: str = Field(default="", env="LINKEDIN_URL")
    DEBUG: bool = Field(False, env="DEBUG")
    
    # MinIO Configuration
    MINIO_ENDPOINT: str = Field("localhost:9000", env="MINIO_ENDPOINT")
    MINIO_ACCESS_KEY: str = Field("minioadmin", env="MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY: str = Field("minioadmin", env="MINIO_SECRET_KEY")
    MINIO_BUCKET: str = Field("scraped-jobs", env="MINIO_BUCKET")
    MINIO_SECURE: bool = Field(False, env="MINIO_SECURE")
    DELTA_LAKEHOUSE_BUCKET: str = Field("delta-lakehouse", env="DELTA_LAKEHOUSE_BUCKET")

    model_config = {
        "env_file": str(ENV_FILE),
        "env_file_encoding": "utf-8"
    }

settings = Settings()




