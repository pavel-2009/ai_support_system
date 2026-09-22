"""Тесты JSON-структуры структурированных логов."""

import json
import logging

from app.core.logging import get_logger


def test_log_is_valid_json_with_required_fields(caplog):
    logger = get_logger("tests.logging")

    with caplog.at_level(logging.INFO, logger="tests.logging"):
        logger.info("json_structure_test", component="unit")

    record = next(
        record
        for record in reversed(caplog.records)
        if record.name == "tests.logging"
    )
    payload = json.loads(record.getMessage())

    assert payload["event"] == "json_structure_test"
    assert payload["timestamp"]
    assert payload["level"] == "info"
    assert payload["logger"] == "tests.logging"
    assert "correlation_id" in payload
    assert payload["component"] == "unit"
