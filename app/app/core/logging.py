"""Централизованная настройка структурированного логирования."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
from typing import Any

import structlog

from app.core.config import settings
from app.core.correlation import get_correlation_id

_LOGGING_CONFIGURED = False


class _ExactLevelFilter(logging.Filter):
    """Пропускает записи только одного уровня."""

    def __init__(self, level: int) -> None:
        super().__init__()
        self.level = level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno == self.level


class _LevelRangeFilter(logging.Filter):
    """Пропускает записи в заданном диапазоне уровней."""

    def __init__(self, minimum: int, maximum: int) -> None:
        super().__init__()
        self.minimum = minimum
        self.maximum = maximum

    def filter(self, record: logging.LogRecord) -> bool:
        return self.minimum <= record.levelno <= self.maximum


def _add_correlation_id(
    _logger: Any,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Добавить correlation ID в каждую запись лога."""
    event_dict["correlation_id"] = get_correlation_id()
    return event_dict


def _make_file_handler(
    path: Path,
    minimum: int,
    maximum: int,
) -> RotatingFileHandler:
    """Создать ротируемый handler для отдельного диапазона уровней."""
    handler = RotatingFileHandler(
        path,
        maxBytes=settings.LOG_MAX_BYTES,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.addFilter(_LevelRangeFilter(minimum, maximum))
    return handler


def configure_logging() -> None:
    """Настроить JSON-логирование в консоль и отдельные файлы по уровням."""
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _add_correlation_id,
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=[
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _add_correlation_id,
        ],
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.addFilter(_ExactLevelFilter(logging.INFO))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    handlers = {
        "debug.log": _make_file_handler(
            log_dir / "debug.log", logging.DEBUG, logging.DEBUG
        ),
        "info.log": _make_file_handler(
            log_dir / "info.log", logging.INFO, logging.INFO
        ),
        "warning.log": _make_file_handler(
            log_dir / "warning.log", logging.WARNING, logging.WARNING
        ),
        "error.log": _make_file_handler(
            log_dir / "error.log", logging.ERROR, logging.CRITICAL
        ),
    }
    for handler in handlers.values():
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    for name in ("sqlalchemy.engine", "sqlalchemy.pool", "aiosqlite"):
        logging.getLogger(name).setLevel(logging.WARNING)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
        logger.setLevel(logging.INFO)

    _LOGGING_CONFIGURED = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Получить структурированный логгер по имени модуля."""
    configure_logging()
    return structlog.get_logger(name)
