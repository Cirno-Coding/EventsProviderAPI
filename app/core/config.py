from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="events-aggregator", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")
    debug: bool = Field(default=False, alias="DEBUG")

    database_url: str = Field(alias="DATABASE_URL")

    events_provider_base_url: str = Field(alias="EVENTS_PROVIDER_BASE_URL")
    events_provider_api_key: str = Field(alias="EVENTS_PROVIDER_API_KEY")

    enable_background_sync: bool = Field(default=True, alias="ENABLE_BACKGROUND_SYNC")
    sync_interval_seconds: int = Field(default=86400, alias="SYNC_INTERVAL_SECONDS")
    seats_cache_ttl_seconds: int = Field(default=30, alias="SEATS_CACHE_TTL_SECONDS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()