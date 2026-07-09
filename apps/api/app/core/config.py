"""Application configuration via environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    API_ENV: Literal["development", "staging", "production"] = "development"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"]
    )

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""

    # Database
    DATABASE_URL: str = ""  # asyncpg
    DATABASE_URL_SYNC: str = ""  # psycopg2 for migrations

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    ARQ_REDIS_URL: str = "redis://localhost:6379/0"

    # AI Providers
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    DEFAULT_LLM_PROVIDER: str = "openai"
    DEFAULT_LLM_MODEL: str = "gpt-4o-mini"

    # Integrations
    HYPEAUDITOR_API_KEY: str = ""
    CANVA_CLIENT_ID: str = ""
    CANVA_CLIENT_SECRET: str = ""
    GOOGLE_DRIVE_CLIENT_ID: str = ""
    GOOGLE_DRIVE_CLIENT_SECRET: str = ""
    TRELLO_API_KEY: str = ""
    TRELLO_TOKEN: str = ""
    SLACK_WEBHOOK_URL: str = ""

    # Storage
    SUPABASE_STORAGE_BUCKET: str = "lawebcore-assets"

    # Feature flags
    FEATURE_AI_ASSISTANT: bool = True
    FEATURE_KANBAN: bool = True
    FEATURE_WORKFLOWS: bool = True
    FEATURE_REPORTS_AUTO: bool = True

    # Limits
    MAX_UPLOAD_SIZE_MB: int = 50
    RATE_LIMIT_PER_MINUTE: int = 300


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()