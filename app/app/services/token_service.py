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
        """Создание пары токенов (access и refresh) для пользователя."""
        user_id = int(user_data.get('user_id', 0))
        jti = str(uuid4())
        family_id = str(uuid4())

        refresh_token = self._issue_refresh(user_id, jti, family_id)
        access_token = create_access_token(user_data)

        return access_token, refresh_token

    def rotate(self, old_refresh_token: str) -> tuple[str, str]:
        """Ротация refresh-токена. Проверяет старый токен, создает новый и помечает старый как использованный."""
        old_hash = _hash_token(old_refresh_token)
        raw = self.redis.get(self._key(old_hash))

        if raw is None:
            family_id = self._lookup_tombstone(old_hash)
            if family_id:
                user_id = self._get_family_user_id(family_id)
                self.revoke_family(family_id, user_id)

                logger.warning(
                    "REFRESH REUSE DETECTED: family=%s user=%s revoked",
                    family_id, user_id,
                )

                raise RefreshTokenReused("Refresh token уже был использован.")
            raise RefreshTokenNotFound("Refresh token не найден или истёк.")

        payload = json.loads(raw)
        user_id = int(payload.get("user_id", 0))
        family_id = payload.get("family_id", 0)

        if user_id == 0 or family_id == 0:
            raise RefreshTokenError("Некорректные данные в refresh-токене.")

        self._delete_token(old_hash, family_id, user_id)

        new_jti = str(uuid4())
        new_refresh = self._issue_refresh(user_id, new_jti, family_id)
        access_token = create_access_token({"user_id": user_id})

        return access_token, new_refresh

    def revoke(self, refresh_token: str) -> None:
        """Отзыв refresh-токена. Удаляет токен из Redis и помечает его как использованный."""
        token_hash = _hash_token(refresh_token)

        raw = self.redis.get(self._key(token_hash))
        if raw is None:
            return

        payload = json.loads(raw)

        user_id = int(payload.get("user_id", 0))
        family_id = payload.get("family_id", 0)

        if user_id == 0 or family_id == 0:
            raise RefreshTokenError("Некорректные данные в refresh-токене.")

        self._delete_token(token_hash, family_id, user_id)

    def revoke_family(self, family_id: str, user_id: int | None = None) -> None:
        """Отзыв всех токенов в семье. Удаляет все токены с данным family_id из Redis."""
        family_key = self._family_key(family_id)
        token_hashes = self.redis.smembers(family_key) or set()

        pipe = self.redis.pipeline()
        for token_hash in token_hashes:
            pipe.setex(f"used_refresh:{token_hash}", 300, family_id)
            pipe.delete(self._key(token_hash))

        pipe.delete(family_key)

        if user_id is not None:
            pipe.srem(self._user_families_key(user_id), family_id)

        pipe.execute()

    def revoke_all_for_user(self, user_id: int) -> int:
        """Отзыв всех токенов для пользователя. Удаляет все токены пользователя из Redis."""
        ...

    def list_user_sessions(self, user_id: int) -> list[dict]:
        """Возвращает список всех активных сессий пользователя."""
        ...

    def _issue_refresh(self, user_id: int, jti: str, family_id: str) -> str:
        """Создание нового refresh-токена и сохранение его в Redis."""
        ...

    def _delete_token(self, token_hash: str, family_id: str, user_id: int) -> None:
        """Удаление токена из Redis и пометка его как использованного."""
        ...

    def _get_family_user_id(self, family_id: str) -> int | None:
        """Получение user_id по family_id из Redis."""
        ...

    def _lookup_tombstone(self, token_hash: str) -> str | None:
        """Проверка, был ли токен уже использован (т.е. есть ли "могильная плита" для него в Redis)."""
        ...

    @staticmethod
    def _key(token_hash: str) -> str:
        return f"{settings.REFRESH_TOKEN_PREFIX}{token_hash}"

    @staticmethod
    def _family_key(family_id: str) -> str:
        return f"{settings.REFRESH_FAMILY_PREFIX}{family_id}"

    @staticmethod
    def _user_families_key(user_id: int) -> str:
        return f"{settings.USER_FAMILIES_PREFIX}{user_id}"
 