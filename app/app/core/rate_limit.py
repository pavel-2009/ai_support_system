"""API rate limiter for app protection."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from fastapi import Request

from app.core.security import verify_access_token


def get_user_identifier(request: Request) -> str:
    """Get user identifier for rate limiting."""

    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token:
        payload = verify_access_token(token)
        user_id = payload.get("user_id") if payload else None
        if user_id is not None:
            return str(user_id)

    return get_remote_address(request)


limiter = Limiter(key_func=get_user_identifier, default_limits=["100/minute"])
