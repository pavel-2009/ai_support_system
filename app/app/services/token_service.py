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
 