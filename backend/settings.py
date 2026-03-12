from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path

# Resolve .env path relative to this file's location
ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    APIFY_TOKEN: str = Field(default="", env="APIFY_TOKEN")
    LINKEDIN_URL: str = Field(default="", env="LINKEDIN_URL")
    DEBUG: bool = Field(False, env="DEBUG")

    # OpenRouter Configuration
    OPENROUTER_API_KEY: str = Field(default="", env="OPENROUTER_API_KEY")
    OPENROUTER_MODEL: str = Field(default="", env="OPENROUTER_MODEL")
    OPENROUTER_MODEL_BACKUP: str = Field(default="google/gemini-2.0-flash-exp:free", env="OPENROUTER_MODEL_BACKUP")
    OPENROUTER_BASE_URL: str = Field("https://openrouter.ai/api/v1", env="OPENROUTER_BASE_URL")
    
    # Evaluation settings
    EVAL_DELAY_SECONDS: float = Field(1.0, env="EVAL_DELAY_SECONDS")
    CANDIDATE_EXPERIENCE_YEARS: str = Field("8 Years", env="CANDIDATE_EXPERIENCE_YEARS")
    BATCH_EVAL_WORKERS: int = Field(5, env="BATCH_EVAL_WORKERS")
    EVAL_HIGH_MATCH_THRESHOLD: int = Field(70, env="EVAL_HIGH_MATCH_THRESHOLD")
    EVAL_MAX_JOBS_PER_RUN: int = Field(50, env="EVAL_MAX_JOBS_PER_RUN")
    
    # LinkedIn search URLs (comma-separated for multiple)
    LINKEDIN_SEARCH_URLS: str = Field(default="", env="LINKEDIN_SEARCH_URLS")
    
    # Supabase Configuration
    SUPABASE_URL: str = Field(default="", env="SUPABASE_URL")
    SUPABASE_SERVICE_KEY: str = Field(default="", env="SUPABASE_SERVICE_KEY")
    
    # Langfuse Configuration
    LANGFUSE_PUBLIC_KEY: str = Field(default="", env="LANGFUSE_PUBLIC_KEY")
    LANGFUSE_SECRET_KEY: str = Field(default="", env="LANGFUSE_SECRET_KEY")
    LANGFUSE_BASE_URL: str = Field(default="http://127.0.0.1:3010", env="LANGFUSE_BASE_URL")
    
    # Telegram Notifications
    TELEGRAM_BOT_TOKEN: str = Field(default="", env="TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID: str = Field(default="", env="TELEGRAM_CHAT_ID")

    # Google Drive
    GOOGLE_DRIVE_FOLDER_ID: str = Field(default="", env="GOOGLE_DRIVE_FOLDER_ID")
    
    # Scheduler Configuration
    # Cron expressions take priority over interval hours when set.
    # Format: 'minute hour day month day_of_week'  e.g. '0 */12 * * *' = every 12h
    # Set to empty string to use interval hours instead.
    SCRAPE_CRON: str = Field("", env="SCRAPE_CRON")          # e.g. '0 8,20 * * *'
    EVAL_CRON:   str = Field("", env="EVAL_CRON")            # e.g. '*/30 * * * *'
    SCRAPE_INTERVAL_HOURS: int = Field(12, env="SCRAPE_INTERVAL_HOURS")  # fallback
    EVAL_INTERVAL_HOURS:   int = Field(1,  env="EVAL_INTERVAL_HOURS")    # fallback
    SCHEDULER_ENABLED: bool = Field(True, env="SCHEDULER_ENABLED")
    
    model_config = {
        "env_file": str(ENV_FILE),
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

settings = Settings()




