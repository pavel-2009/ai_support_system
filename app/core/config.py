"""Базовая конфигурация приложения."""

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"

    # === JWT ===
    JWT_SECRET_KEY: str = "change-me-to-a-long-random-secret-key-with-at-least-32-bytes"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # === AI ===
    LLM_API_KEY: str = "your-llm-api-key"
    LLM_MODEL: str = "gpt-4o"
    LLM_RETRY_ATTEMPTS: int = 5
    LLM_TIMEOUT: int = 10  # seconds
    LLM_TEMPERATURE: float = 0.7
    LLM_AI_CONFIDENCE_THRESHOLD: float = 0.8
    LLM_TOKEN_LIMIT: int = 4096
    
    # === Celery ===
    CELERY_BROKER_URL: str = "redis://redis:6380/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6380/0"

settings = Settings()
