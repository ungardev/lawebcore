from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ARQ_REDIS_URL: str = "redis://localhost:6379/0"
    ENV: str = "development"


settings = Settings()
