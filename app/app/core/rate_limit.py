"""API rate limiter for app protection."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from fastapi.requests import Request

from app.core.dependencies import get_current_user


def get_user_identifier(request: Request) -> str:
    """Get user identifier for rate limiting."""
    


limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
