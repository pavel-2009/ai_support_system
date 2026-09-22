"""Correlation ID context and HTTP middleware."""

from __future__ import annotations

from contextvars import ContextVar
from time import perf_counter
from uuid import uuid4

from fastapi import Request
from starlette.responses import Response

CORRELATION_ID_HEADER = "X-Correlation-ID"
_CORRELATION_ID: ContextVar[str] = ContextVar("correlation_id", default="-")


def get_correlation_id() -> str:
    """Вернуть correlation ID текущего execution context."""
    return _CORRELATION_ID.get()


def set_correlation_id(correlation_id: str) -> None:
    """Установить correlation ID для текущего execution context."""
    _CORRELATION_ID.set(correlation_id)


def _get_or_create_correlation_id(request: Request) -> str:
    """Получить безопасный входящий ID или создать новый."""
    value = request.headers.get(CORRELATION_ID_HEADER)
    return value.strip() if value and value.strip() else str(uuid4())


async def correlation_middleware(request: Request, call_next) -> Response:
    """Установить correlation ID и записать HTTP request/response."""
    correlation_id = _get_or_create_correlation_id(request)
    token = _CORRELATION_ID.set(correlation_id)
    started = perf_counter()

    try:
        response = await call_next(request)
        duration_ms = round((perf_counter() - started) * 1000, 2)
        from app.core.logging import get_logger

        get_logger("app.http").info(
            "http_request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response
    except Exception:
        duration_ms = round((perf_counter() - started) * 1000, 2)
        from app.core.logging import get_logger

        get_logger("app.http").exception(
            "http_request_failed",
            method=request.method,
            path=request.url.path,
            duration_ms=duration_ms,
        )
        raise
    finally:
        _CORRELATION_ID.reset(token)
