"""API rate limiter for app protection."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from fastapi.requests import Request

from app.core.dependencies import get_current_user


def get_user_identifier(request: Request) -> str:
    """Get user identifier for rate limiting."""

    token = request.json().get("token")
    if token:
        user = get_current_user(token)
        if user:
            return str(user.id)

        else:
            return get_remote_address(request)

    return get_remote_address(request)
    


limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
