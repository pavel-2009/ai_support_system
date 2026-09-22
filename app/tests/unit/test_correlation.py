"""Тесты correlation ID middleware."""

from app.core.correlation import CORRELATION_ID_HEADER, get_correlation_id


def test_correlation_id_is_generated_and_returned(client):
    response = client.get("/metrics")

    correlation_id = response.headers[CORRELATION_ID_HEADER]
    assert correlation_id
    assert correlation_id != "-"
    assert get_correlation_id() == "-"


def test_incoming_correlation_id_is_preserved(client):
    correlation_id = "test-correlation-123"

    response = client.get(
        "/metrics",
        headers={CORRELATION_ID_HEADER: correlation_id},
    )

    assert response.headers[CORRELATION_ID_HEADER] == correlation_id
    assert get_correlation_id() == "-"
