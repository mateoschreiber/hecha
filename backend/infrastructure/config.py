from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    environment: str = "development"
    database_url: str = "postgresql+psycopg://hecha@db:5432/hecha"
    freshness_stale_minutes: int = 45


@lru_cache
def get_settings() -> Settings:
    return Settings()
