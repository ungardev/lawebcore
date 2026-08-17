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

    POSTGRES_URL: str = ""
    SUPABASE_URL: str = ""  # deprecated alias for POSTGRES_URL
    POSTGRES_SERVICE_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""  # deprecated alias for POSTGRES_SERVICE_KEY

    DATABASE_URL: str = ""

    ARQ_REDIS_URL: str = "redis://localhost:6379/0"

    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-chat"

    GOOGLE_SERVICE_ACCOUNT_KEY: str = ""
    GOOGLE_DRIVE_FOLDER_ID: str = ""

    HYPEAUDITOR_API_KEY: str = ""
    APIFY_API_KEY: str = ""
    HIKERAPI_API_KEY: str = ""
    INSTAGRAM_SOURCE: str = "hikerapi"

    META_APP_ID: str = ""
    META_APP_SECRET: str = ""
    META_ACCESS_TOKEN: str = ""

    TIKTOK_RESEARCH_API_KEY: str = ""

    YOUTUBE_DATA_API_KEY: str = ""

    METRICOOL_CLIENT_ID: str = ""
    METRICOOL_CLIENT_SECRET: str = ""
    METRICOOL_ACCESS_TOKEN: str = ""

    ADMIN_TOKEN: str = ""

    ENABLE_AI_ANALYZER: bool = False

    MAX_UPLOAD_SIZE_MB: int = 50
    RATE_LIMIT_PER_MINUTE: int = 300
    RATE_LIMIT_DISCOVERY_PER_MIN: int = 30

    # LENS Budget & Cost Controls
    MONTHLY_BUDGET_USD: float = 10.0
    MAX_CALLS_PER_RUN: int = 120
    BUDGET_ALERT_THRESHOLD: float = 0.7
    HIKERAPI_COST_PER_CALL_USD: float = 0.02
    HIKERAPI_5XX_BREAKER_THRESHOLD: int = 5
    HIKERAPI_5XX_BREAKER_TTL_S: int = 300
    RUN_MODE: Literal["live", "replay"] = "live"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
