from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ARQ_REDIS_URL: str = "redis://localhost:6379/0"
    ENV: str = "development"
    API_ENV: str = "development"

    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    APIFY_API_KEY: str = ""


settings = Settings()