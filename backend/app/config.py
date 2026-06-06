"""
QuantFlow application configuration.
Loaded from environment variables / .env file via Pydantic Settings.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_SECRET_KEY: str = Field(min_length=32)
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    APP_VERSION: str = "1.0.0"

    # --- Database ---
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "quantflow"
    POSTGRES_USER: str = "quantflow"
    POSTGRES_PASSWORD: str

    DATABASE_URL: str = ""          # built in validator if empty
    DATABASE_URL_SYNC: str = ""

    @model_validator(mode="after")
    def build_db_urls(self) -> "Settings":
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        if not self.DATABASE_URL_SYNC:
            self.DATABASE_URL_SYNC = (
                f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        return self

    # --- Redis ---
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_URL: str = ""

    @model_validator(mode="after")
    def build_redis_url(self) -> "Settings":
        if not self.REDIS_URL:
            auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
            self.REDIS_URL = f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return self

    # --- RabbitMQ ---
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "quantflow"
    RABBITMQ_PASSWORD: str = ""
    RABBITMQ_URL: str = ""

    @model_validator(mode="after")
    def build_rabbitmq_url(self) -> "Settings":
        if not self.RABBITMQ_URL:
            self.RABBITMQ_URL = (
                f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}"
                f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"
            )
        return self

    # --- JWT ---
    JWT_PRIVATE_KEY_PATH: str = "/run/secrets/jwt_private_key"
    JWT_PUBLIC_KEY_PATH: str = "/run/secrets/jwt_public_key"
    JWT_ACCESS_TOKEN_TTL_MINUTES: int = 15
    JWT_REFRESH_TOKEN_TTL_DAYS: int = 7
    JWT_ALGORITHM: str = "RS256"

    # --- Celery ---
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    @model_validator(mode="after")
    def build_celery_urls(self) -> "Settings":
        if not self.CELERY_BROKER_URL:
            self.CELERY_BROKER_URL = self.RABBITMQ_URL
        if not self.CELERY_RESULT_BACKEND:
            auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
            self.CELERY_RESULT_BACKEND = f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/1"
        return self

    # --- Market Data ---
    POLYGON_API_KEY: str = ""
    POLYGON_WS_URL: str = "wss://socket.polygon.io/options"
    ALPACA_API_KEY: str = ""
    ALPACA_SECRET_KEY: str = ""
    FRED_API_KEY: str = ""
    IB_HOST: str = "127.0.0.1"
    IB_PORT: int = 7497
    IB_CLIENT_ID: int = 1

    # --- CORS ---
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",")]
        return v

    # --- Feature Flags ---
    ENABLE_AI_REPORTS: bool = True
    ENABLE_BACKTESTING: bool = True
    ENABLE_FUTURES_FLOW: bool = True

    # --- DB Pool ---
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    DB_POOL_TIMEOUT: int = 30
    DB_ECHO: bool = False

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
