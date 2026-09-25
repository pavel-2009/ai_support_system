"""Точка входа в приложение FastAPI."""

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
@app.middleware("http")
async def prometheus_metrics_middleware(request: Request, call_next):
    return await prometheus_middleware(request, call_next)


@app.get("/metrics", include_in_schema=False)
async def metrics(session: AsyncSession = Depends(get_async_session)):
    return await metrics_response(session)
CONTENT_TYPE_LATEST)


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
