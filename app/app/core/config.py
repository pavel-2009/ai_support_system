"""Базовая конфигурация приложения."""

from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Конфигурация приложения."""
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    
    # === Application ===
    APP_NAME: str = "My FastAPI Application"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "A FastAPI application with JWT authentication and PostgreSQL database."
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"
    OPENAPI_URL: str = "/openapi.json"
    API_PREFIX: str = "/api"
    
    # === Database ===
    # Если тесты запускаются в CI, используем SQLite, иначе - PostgreSQL. Это позволяет избежать проблем с настройкой PostgreSQL в CI среде.
    if os.getenv("CI") == "true":
        DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"
    else:
        DATABASE_URL: str = "postgresql+asyncpg://postgres:password@db:5432/mydatabase"

    # === JWT ===
    JWT_SECRET_KEY: str = "change-me-to-a-long-random-secret-key-with-at-least-32-bytes"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # === AI ===
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "qwen/qwen3-coder:free"
    LLM_RETRY_ATTEMPTS: int = 5
    LLM_TIMEOUT: int = 20  # seconds
    LLM_TEMPERATURE: float = 0.7
    LLM_AI_CONFIDENCE_THRESHOLD: float = 0.8
    LLM_ESCALATION_CONFIDENCE_THRESHOLD: float = 0.65
    LLM_TOKEN_LIMIT: int = 4096
    
    # === Celery ===
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    # === Business limits ===
    MAX_OPERATOR_ACTIVE_CONVERSATIONS: int = 5

settings = Settings()
