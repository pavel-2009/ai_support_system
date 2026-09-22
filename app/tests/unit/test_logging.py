"""Тесты JSON-структуры структурированных логов."""

import json

from app.core.logging import get_logger


def test_log_is_valid_json_with_required_fields(capsys):
    logger = get_logger("tests.logging")
    logger.info("json_structure_test", component="unit")

    line = capsys.readouterr().out.strip().splitlines()[-1]
    payload = json.loads(line)

    assert payload["event"] == "json_structure_test"
    assert payload["timestamp"]
    assert payload["level"] == "info"
    assert payload["logger"] == "tests.logging"
    assert "correlation_id" in payload
    assert payload["component"] == "unit"
