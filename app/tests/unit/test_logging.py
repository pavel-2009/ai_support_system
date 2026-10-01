"""Тесты централизованного структурированного логирования."""

import json
import logging

import app.core.logging as logging_config
from app.core.config import settings
from app.core.logging import get_logger
from sqlalchemy.exc import SQLAlchemyError


def _payload(record: logging.LogRecord) -> dict:
    """Извлечь JSON payload как из обработанного, так и из исходного record."""
    message = record.getMessage()
    try:
        return json.loads(message)
    except json.JSONDecodeError:
        if isinstance(record.msg, dict):
            return record.msg
        raise


def test_log_is_valid_json_with_required_fields(caplog):
    logger = get_logger("tests.logging")

    with caplog.at_level(logging.INFO, logger="tests.logging"):
        logger.info("json_structure_test", component="unit")

    record = next(
        record
        for record in reversed(caplog.records)
        if record.name == "tests.logging"
    )
    payload = _payload(record)

    assert payload["event"] == "json_structure_test"
    assert payload["timestamp"]
    assert payload["level"] == "info"
    assert payload["logger"] == "tests.logging"
    assert "correlation_id" in payload
    assert payload["component"] == "unit"


def test_message_error_file_contains_database_errors_only(tmp_path, monkeypatch):
    root_logger = logging.getLogger()
    message_logger = logging.getLogger("app.message_errors")
    previous_root_handlers = root_logger.handlers[:]
    previous_message_handlers = message_logger.handlers[:]
    previous_message_propagate = message_logger.propagate
    previous_message_level = message_logger.level
    previous_configured = logging_config._LOGGING_CONFIGURED

    try:
        monkeypatch.setattr(settings, "LOG_DIR", str(tmp_path))
        monkeypatch.setattr(logging_config, "_LOGGING_CONFIGURED", False)
        logging_config.configure_logging()

        get_logger("app.services.message_service").error("service_failure")
        log_path = tmp_path / "message_errors.log"
        for handler in message_logger.handlers:
            handler.flush()
        assert log_path.read_text(encoding="utf-8") == ""

        try:
            raise SQLAlchemyError("insert failed")
        except SQLAlchemyError as exc:
            logging_config.log_database_message_error(
                "repository",
                exc,
                conversation_id=42,
            )

        for handler in message_logger.handlers:
            handler.flush()

        payload = json.loads(log_path.read_text(encoding="utf-8"))
        assert payload["event"] == "message_creation_error"
        assert payload["stage"] == "repository"
        assert payload["conversation_id"] == 42
        assert "SQLAlchemyError: insert failed" in payload["exception"]
    finally:
        previous_handlers = previous_root_handlers + previous_message_handlers
        for handler in root_logger.handlers + message_logger.handlers:
            if handler not in previous_handlers:
                handler.close()
        root_logger.handlers.clear()
        root_logger.handlers.extend(previous_root_handlers)
        message_logger.handlers.clear()
        message_logger.handlers.extend(previous_message_handlers)
        message_logger.propagate = previous_message_propagate
        message_logger.setLevel(previous_message_level)
        logging_config._LOGGING_CONFIGURED = previous_configured
