"""Централизованная настройка структурированного логирования."""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from app.core.correlation import get_correlation_id

_LOGGING_CONFIGURED = False


def _add_correlation_id(
    _logger: Any,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Добавить correlation ID в каждую запись лога."""
    event_dict["correlation_id"] = get_correlation_id()
    return event_dict


def configure_logging() -> None:
    """Настроить JSON-логирование один раз."""
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            timestamper,
            _add_correlation_id,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    for name in ("sqlalchemy.engine", "sqlalchemy.pool", "aiosqlite"):
        logging.getLogger(name).setLevel(logging.WARNING)

    _LOGGING_CONFIGURED = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Получить структурированный логгер по имени модуля."""
    configure_logging()
    return structlog.get_logger(name)
