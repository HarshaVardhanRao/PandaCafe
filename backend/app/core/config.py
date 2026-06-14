"""
Configuration management for PandaCafe application.
Uses environment variables with pydantic settings for validation.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # Application
    APP_NAME: str = "PandaCafe POS"
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = "postgresql://pandacafe:pandacafe_dev@localhost:5432/pandacafe"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # API
    API_V1_STR: str = "/api/v1"
    API_RATE_LIMIT: str = "100/minute"

    # Printer
    PRINTER_TIMEOUT: int = 10
    PRINTER_RETRY_COUNT: int = 3
    ENABLE_PRINTER_SIMULATION: bool = False

    # Email
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@pandacafe.com"
    SMTP_FROM_NAME: str = "Panda Cafe"

    # AWS S3
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_S3_BUCKET: str = "pandacafe-images"
    AWS_REGION: str = "us-east-1"

    # Feature Flags
    ENABLE_OFFLINE_MODE: bool = True
    ENABLE_AUDIT_LOGGING: bool = True
    ENABLE_NOTIFICATIONS: bool = True

    class Config:
        """Pydantic config."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"

settings = Settings()
