"""Базовая конфигурация приложения."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Конфигурация приложения."""
    
    _env_file = ".env"
    _env_file_encoding = "utf-8"
    
    # === Application ===
    APP_NAME: str = "My FastAPI Application"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "A FastAPI application with JWT authentication and PostgreSQL database."
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"
    OPENAPI_URL: str = "/openapi.json"
    API_PREFIX: str = "/api"
    
    # === Database ===
    DATABASE_URL: str

    # === JWT ===
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        

settings = Settings()