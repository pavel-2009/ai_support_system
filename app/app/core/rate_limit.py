"""API rate limiter for app protection."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from fastapi.exceptions import RequestValidationError


limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
