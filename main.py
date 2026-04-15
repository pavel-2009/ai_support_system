"""Точка входа в приложение FastAPI."""

from fastapi import FastAPI

from app.core.config import settings
from app.routers.user import admin_router, auth_router, users_router
from app.db import get_async_session

from app.services_init import init_services

from contextlib import asynccontextmanager


# lifespan для инициализации сервисов при старте приложения и их очистки при завершении
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализация сервисов
    async with get_async_session() as session:
        await init_services(session)
    
    yield

    # Очистка ресурсов при завершении будет реализована позже, если потребуется.


app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    docs_url=settings.DOCS_URL,
    redoc_url=settings.REDOC_URL,
    openapi_url=settings.OPENAPI_URL,
    root_path=settings.API_PREFIX,
    lifespan=lifespan,  # Указываем lifespan для управления жизненным циклом приложения
)

app.include_router(users_router)
app.include_router(auth_router)
app.include_router(admin_router)


@app.get("/health", tags=["Health"], summary="Проверка работоспособности API")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000, log_level="info")
