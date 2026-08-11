from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    environment: str = "development"
    database_url: str = "postgresql+psycopg://hecha:hecha@db:5432/hecha"
    redis_url: str = "redis://redis:6379/0"
    silpy_base_url: str = "https://datos.congreso.gov.py/opendata/api"
    silpy_page_size: int = 50
    silpy_partial_pages: int = 3
    silpy_timeout_seconds: float = 12.0
    silpy_max_attempts: int = 3
    silpy_concurrency: int = 5
    freshness_stale_minutes: int = 45


@lru_cache
def get_settings() -> Settings:
    return Settings()
