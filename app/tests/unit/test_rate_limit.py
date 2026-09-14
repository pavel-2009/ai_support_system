"""Tests for API rate limiting."""

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.rate_limit import get_user_identifier
from app.core.security import create_access_token


def make_limited_client() -> TestClient:
    app = FastAPI()
    limiter = Limiter(key_func=get_user_identifier, storage_uri="memory://")
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.get("/limited")
    @limiter.limit("5/minute")
    async def limited_endpoint(request: Request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    return TestClient(app)


def auth_headers(user_id: int) -> dict[str, str]:
    token = create_access_token({"user_id": user_id, "email": f"user{user_id}@example.com"})
    return {"Authorization": f"Bearer {token}"}


class TestUserIdentifier:
    def test_uses_remote_address_without_authentication(self):
        request = Request({
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "client": ("127.0.0.1", 1234),
            "scheme": "http",
            "server": ("testserver", 80),
            "query_string": b"",
        })

        assert get_user_identifier(request) == "127.0.0.1"

    def test_uses_user_id_from_bearer_token(self):
        request = Request({
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(b"authorization", auth_headers(42)["Authorization"].encode())],
            "client": ("127.0.0.1", 1234),
            "scheme": "http",
            "server": ("testserver", 80),
            "query_string": b"",
        })

        assert get_user_identifier(request) == "42"

    def test_invalid_bearer_token_falls_back_to_remote_address(self):
        request = Request({
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(b"authorization", b"Bearer invalid")],
            "client": ("192.0.2.10", 1234),
            "scheme": "http",
            "server": ("testserver", 80),
            "query_string": b"",
        })

        assert get_user_identifier(request) == "192.0.2.10"


class TestRateLimit:
    def test_sixth_request_from_one_user_is_blocked(self):
        client = make_limited_client()

        responses = [client.get("/limited", headers=auth_headers(1)) for _ in range(6)]

        assert [response.status_code for response in responses] == [200, 200, 200, 200, 200, 429]

    def test_eight_requests_from_two_users_do_not_block_both(self):
        client = make_limited_client()

        responses = [
            client.get("/limited", headers=auth_headers(1))
            for _ in range(4)
        ] + [
            client.get("/limited", headers=auth_headers(2))
            for _ in range(4)
        ]

        assert all(response.status_code == 200 for response in responses)
