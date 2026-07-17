"""Application configuration via environment variables."""

import json
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_ignore_empty=True,
    )

    API_ENV: Literal["development", "staging", "production"] = "development"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_CORS_ORIGINS: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://localhost:3000",
            "https://lawebcore.vercel.app",
        ]
    )

    @field_validator("API_CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        if isinstance(v, str):
            v = v.strip()
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except (ValueError, json.JSONDecodeError):
                pass
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""

    DATABASE_URL: str = ""
    DATABASE_URL_SYNC: str = ""

    REDIS_URL: str = "redis://localhost:6379/0"
    ARQ_REDIS_URL: str = "redis://localhost:6379/0"

    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEFAULT_LLM_PROVIDER: str = "openai"
    DEFAULT_LLM_MODEL: str = "gpt-4o-mini"

    GOOGLE_SERVICE_ACCOUNT_KEY: str = ""
    GOOGLE_DRIVE_FOLDER_ID: str = ""

    HYPEAUDITOR_API_KEY: str = ""
    CANVA_CLIENT_ID: str = ""
    CANVA_CLIENT_SECRET: str = ""
    GOOGLE_DRIVE_CLIENT_ID: str = ""
    GOOGLE_DRIVE_CLIENT_SECRET: str = ""
    TRELLO_API_KEY: str = ""
    TRELLO_TOKEN: str = ""
    SLACK_WEBHOOK_URL: str = ""

    APIFY_API_KEY: str = ""

    META_APP_ID: str = ""
    META_APP_SECRET: str = ""
    META_ACCESS_TOKEN: str = ""

    TIKTOK_RESEARCH_API_KEY: str = ""

    YOUTUBE_DATA_API_KEY: str = ""

    METRICOOL_CLIENT_ID: str = ""
    METRICOOL_CLIENT_SECRET: str = ""
    METRICOOL_ACCESS_TOKEN: str = ""

    SUPABASE_STORAGE_BUCKET: str = "lawebcore-assets"

    FEATURE_AI_ASSISTANT: bool = True
    FEATURE_KANBAN: bool = True
    FEATURE_WORKFLOWS: bool = True
    FEATURE_REPORTS_AUTO: bool = True
    FEATURE_DISCOVERY: bool = True

    MAX_UPLOAD_SIZE_MB: int = 50
    RATE_LIMIT_PER_MINUTE: int = 300
    RATE_LIMIT_DISCOVERY_PER_MIN: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
