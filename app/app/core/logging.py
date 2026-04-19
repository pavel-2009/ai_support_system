"""Централизованная настройка логирования приложения."""

import logging
from logging.config import dictConfig


_LOGGING_CONFIGURED = False


def configure_logging() -> None:
    """Настроить базовый логгер приложения один раз."""
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "level": "INFO",
                }
            },
            "root": {
                "handlers": ["console"],
                "level": "INFO",
            },
        }
    )
    _LOGGING_CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Получить настроенный логгер по имени модуля."""
    configure_logging()
    return logging.getLogger(name)
