from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="events-aggregator", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")
    debug: bool = Field(default=False, alias="DEBUG")

    database_url_env: str | None = Field(default=None, alias="DATABASE_URL")
    postgres_connection_string: str | None = Field(
        default=None,
        alias="POSTGRES_CONNECTION_STRING",
    )

    events_provider_base_url: str = Field(
        alias="EVENTS_PROVIDER_BASE_URL",
    )
    events_provider_api_key: str = Field(
        alias="EVENTS_PROVIDER_API_KEY",
    )

    enable_background_sync: bool = Field(default=False, alias="ENABLE_BACKGROUND_SYNC")
    sync_interval_seconds: int = Field(default=86400, alias="SYNC_INTERVAL_SECONDS")
    seats_cache_ttl_seconds: int = Field(default=30, alias="SEATS_CACHE_TTL_SECONDS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    capashino_base_url: str | None = Field(
        default=None,
        alias="CAPASHINO_BASE_URL",
    )
    capashino_api_key: str | None = Field(
        default=None,
        alias="CAPASHINO_API_KEY",
    )

    outbox_poll_interval_seconds: int = Field(
        default=10,
        ge=1,
        alias="OUTBOX_POLL_INTERVAL_SECONDS",
    )
    outbox_batch_size: int = Field(
        default=100,
        ge=1,
        le=1000,
        alias="OUTBOX_BATCH_SIZE",
    )
    outbox_sent_retention_days: int = Field(
        default=7,
        ge=1,
        alias="OUTBOX_SENT_RETENTION_DAYS",
    )

    idempotency_key_ttl_seconds: int = Field(
        default=86400,
        ge=1,
        alias="IDEMPOTENCY_KEY_TTL_SECONDS",
    )

    glitchtip_dsn: str | None = Field(
        default=None,
        alias="GLITCHTIP_DSN",
    )

    @field_validator(
        "capashino_base_url",
        "capashino_api_key",
        "glitchtip_dsn",
        mode="before",
    )
    @classmethod
    def normalize_optional_strings(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            return value.strip() or None
        return value

    @property
    def database_url(self) -> str:
        raw_url = self.database_url_env or self.postgres_connection_string

        if raw_url is None:
            raise RuntimeError(
                "DATABASE_URL or POSTGRES_CONNECTION_STRING is required",
            )

        if raw_url.startswith("postgresql+asyncpg://"):
            return raw_url

        if raw_url.startswith("postgresql://"):
            return raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        if raw_url.startswith("postgres://"):
            return raw_url.replace("postgres://", "postgresql+asyncpg://", 1)

        return raw_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
