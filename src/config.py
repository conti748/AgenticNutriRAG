"""Application configuration loaded and validated from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = Field(min_length=1)
    usda_api_key: str = Field(min_length=1)

    elasticsearch_url: str = Field(min_length=1)

    postgres_host: str = Field(min_length=1)
    postgres_port: int = 5432
    postgres_db: str = Field(min_length=1)
    postgres_user: str = Field(min_length=1)
    postgres_password: str = Field(min_length=1)

    grafana_port: int = 3000
    grafana_admin_user: str = Field(min_length=1)
    grafana_admin_password: str = Field(min_length=1)


@lru_cache
def get_settings() -> Settings:
    """Load settings once and fail fast if required environment variables are missing."""
    return Settings()  # type: ignore[call-arg]
