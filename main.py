"""Точка входа в приложение FastAPI."""

from fastapi import FastAPI

from app.core.config import settings


app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    docs_url=settings.DOCS_URL,
    redoc_url=settings.REDOC_URL,
    openapi_url=settings.OPENAPI_URL,
)


# Регистрируем маршруты и обработчики здесь
pass


# Базовый маршрут для проверки работоспособности
@app.get("/health", tags=["Health"], summary="Проверка работоспособности API")
def health_check():
    return {"status": "healthy"}


# Запуск приложения
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="localhost",
        port=8000,
        log_level="info",
    )