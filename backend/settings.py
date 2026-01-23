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
    
    # OpenRouter Configuration
    OPENROUTER_API_KEY: str = Field(default="", env="OPENROUTER_API_KEY")
    OPENROUTER_MODEL: str = Field(default="", env="OPENROUTER_MODEL")
    OPENROUTER_MODEL_BACKUP: str = Field(default="google/gemini-2.0-flash-exp:free", env="OPENROUTER_MODEL_BACKUP")
    OPENROUTER_BASE_URL: str = Field("https://openrouter.ai/api/v1", env="OPENROUTER_BASE_URL")
    
    # Evaluation settings
    EVAL_DELAY_SECONDS: float = Field(1.0, env="EVAL_DELAY_SECONDS")
    EVAL_DB_PATH: str = Field("data/evaluations.db", env="EVAL_DB_PATH")
    CANDIDATE_EXPERIENCE_YEARS: str = Field("8 Years", env="CANDIDATE_EXPERIENCE_YEARS")
    BATCH_EVAL_WORKERS: int = Field(5, env="BATCH_EVAL_WORKERS")
    
    # Supabase Configuration
    SUPABASE_URL: str = Field(default="", env="SUPABASE_URL")
    SUPABASE_SERVICE_KEY: str = Field(default="", env="SUPABASE_SERVICE_KEY")
    USE_SUPABASE: bool = Field(default=False, env="USE_SUPABASE")
    
    # Langfuse Configuration
    LANGFUSE_PUBLIC_KEY: str = Field(default="", env="LANGFUSE_PUBLIC_KEY")
    LANGFUSE_SECRET_KEY: str = Field(default="", env="LANGFUSE_SECRET_KEY")
    LANGFUSE_HOST: str = Field(default="http://localhost:3010", env="LANGFUSE_HOST")
    
    model_config = {
        "env_file": str(ENV_FILE),
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

settings = Settings()




