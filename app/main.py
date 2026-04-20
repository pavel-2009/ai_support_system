"""Точка входа в приложение FastAPI."""

from fastapi import Depends, FastAPI
from fastapi.openapi.utils import get_openapi
from redis import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery.celery_app import celery_app
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db import get_async_session
from app.routers.users.conversation import router as conversation_router
from app.routers.users.message import router as message_router
from app.routers.users.user import admin_router, auth_router, users_router
from app.routers.operator.conversation import router as operator_router

configure_logging()
logger = get_logger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    docs_url=settings.DOCS_URL,
    redoc_url=settings.REDOC_URL,
    openapi_url=settings.OPENAPI_URL,
    root_path=settings.API_PREFIX,
)

app.include_router(users_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(conversation_router)
app.include_router(message_router)
app.include_router(operator_router)


@app.get("/health", tags=["Health"], summary="Проверка работоспособности API")
async def health_check(
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, object]:
    """Расширенная проверка состояния приложения и зависимостей."""
    checks: dict[str, object] = {
        "api": "ok",
        "database": "unknown",
        "redis": "unknown",
        "celery": "unknown",
    }

    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        logger.exception("Ошибка health-check: недоступна база данных.")
        checks["database"] = "error"

    try:
        redis_client = Redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=1)
        redis_client.ping()
        redis_client.close()
        checks["redis"] = "ok"
    except Exception:
        logger.exception("Ошибка health-check: недоступен Redis.")
        checks["redis"] = "error"

    try:
        ping_result = celery_app.control.inspect(timeout=1.0).ping()
        checks["celery"] = "ok" if ping_result else "warning"
    except Exception:
        logger.exception("Ошибка health-check: недоступен Celery.")
        checks["celery"] = "error"

    overall_status = "healthy" if all(value == "ok" for value in checks.values()) else "degraded"
    return {
        "status": overall_status,
        "checks": checks,
        "services": {
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "api_prefix": settings.API_PREFIX,
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000, log_level="info")
