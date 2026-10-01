"""Работа с безопасностью, включая создание и проверку JWT токенов."""

from datetime import datetime, timedelta
from uuid import uuid4

import anyio
import bcrypt
from jwt import PyJWTError, decode, encode

from app.core.config import settings


SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM


def create_access_token(
    data: dict,
    expires_delta: timedelta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
) -> str:
    """Создание JWT токена с данными и временем истечения."""
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + expires_delta
    to_encode.update({"exp": expire, "iat": now, "jti": str(uuid4())})
    return encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_access_token(token: str) -> dict | None:
    """Проверка JWT токена и извлечение данных."""
    try:
        payload = decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except PyJWTError:
        return None

    expired = payload.get("exp")
    if expired is None or datetime.utcfromtimestamp(expired) < datetime.utcnow():
        return None

    return payload


def _hash_password_sync(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def _verify_password_sync(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def hash_password(password: str) -> str:
    """Хеширование пароля."""
    return _hash_password_sync(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля с хешем."""
    return _verify_password_sync(plain_password, hashed_password)


async def hash_password_async(password: str) -> str:
    """Хешировать пароль вне event loop."""
    return await anyio.to_thread.run_sync(_hash_password_sync, password)


async def verify_password_async(plain_password: str, hashed_password: str) -> bool:
    """Проверить пароль вне event loop."""
    return await anyio.to_thread.run_sync(
        _verify_password_sync,
        plain_password,
        hashed_password,
    )
