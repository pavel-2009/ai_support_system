"""Refresh-tokens handling with Redis"""

import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from redis import Redis

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import create_access_token

logger = get_logger(__name__)


class RefreshTokenError(Exception): ...

class RefreshTokenNotFound(RefreshTokenError): ...

class RefreshTokenReused(RefreshTokenError): ...

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

@dataclass
class RefreshTokenData:
    user_id: int
    jti: str
    family_id: str


class TokenService:
    """Service for token handling with redis"""

    def __init__(self, redis: Redis):
        self.redis = redis


    def issue_pair(self, user_data: dict) -> tuple[str, str]:
        ...

    def rotate(self, old_refresh_token: str) -> tuple[str, str]:
        ...

    def revoke(self, refresh_token: str) -> None:
        ...

    def revoke_family(self, family_id: str, user_id: int | None = None) -> None:
        ...

    def revoke_all_for_user(self, user_id: int) -> int:
        ...

    def list_user_sessions(self, user_id: int) -> list[dict]:
        ...

    def _issue_refresh(self, user_id: int, jti: str, family_id: str) -> str:
        ...

    def _delete_token(self, token_hash: str, family_id: str, user_id: int) -> None:
        ...

    def _get_family_user_id(self, family_id: str) -> int | None:
        ...

    def _lookup_tombstone(self, token_hash: str) -> str | None:
        ...
 