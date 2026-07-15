"""Application configuration using Pydantic Settings."""

from __future__ import annotations

import os
from pathlib import Path
from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Supports development, testing, staging, and production environments.
    All secrets must be set via environment variables or .env file — never hardcoded.
    """

    # ── General ──────────────────────────────────────────────────────
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    APP_NAME: str = "readmission-platform-backend"
    APP_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"

    # ── Server ───────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # ── Database ─────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://app:dev_password@localhost:5432/readmission"
    DATABASE_SYNC_URL: str = "postgresql://app:dev_password@localhost:5432/readmission"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_ECHO: bool = False

    @property
    def database_url_async(self) -> str:
        return self.DATABASE_URL

    @property
    def database_url_sync(self) -> str:
        return self.DATABASE_SYNC_URL

    # ── Redis ────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_ENABLED: bool = True

    # ── JWT ──────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "change-me-in-production-use-a-real-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_PRIVATE_KEY_PATH: str = ""
    JWT_PUBLIC_KEY_PATH: str = ""

    @property
    def jwt_private_key(self) -> str:
        if self.JWT_PRIVATE_KEY_PATH:
            return Path(self.JWT_PRIVATE_KEY_PATH).read_text()
        return self.JWT_SECRET_KEY

    @property
    def jwt_public_key(self) -> str:
        if self.JWT_PUBLIC_KEY_PATH:
            return Path(self.JWT_PUBLIC_KEY_PATH).read_text()
        return self.JWT_SECRET_KEY

    # ── Rate Limiting ───────────────────────────────────────────────
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_AUTH: str = "10/minute"
    RATE_LIMIT_PREDICT: str = "100/minute"
    RATE_LIMIT_TRAINING: str = "5/minute"
    RATE_LIMIT_ADMIN: str = "50/minute"

    # ── Logging ──────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json | console
    LOG_INCLUDE_TRACE: bool = True

    # ── OpenTelemetry ────────────────────────────────────────────────
    OTEL_ENABLED: bool = False
    OTEL_SERVICE_NAME: str = "readmission-api-gateway"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""

    # ── Security ─────────────────────────────────────────────────────
    BCRYPT_ROUNDS: int = 12
    SESSION_MIDDLEWARE_SECRET: str = "change-me-in-production"
    SECURITY_HEADERS_ENABLED: bool = True

    # ── Testing ──────────────────────────────────────────────────────
    TEST_DATABASE_URL: str = "sqlite+aiosqlite:///./test.db"

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

# Environment detection helpers
def is_development() -> bool:
    return settings.ENVIRONMENT == "development"

def is_testing() -> bool:
    return settings.ENVIRONMENT == "testing"

def is_staging() -> bool:
    return settings.ENVIRONMENT == "staging"

def is_production() -> bool:
    return settings.ENVIRONMENT == "production"