"""Работа с безопасностью, включая создание и проверку JWT токенов."""

from jwt import encode, decode, PyJWTError
import bcrypt
from uuid import uuid4

from datetime import datetime, timedelta

from app.core.config import settings


SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM


# === JWT ТОКЕНЫ ===
def create_access_token(
    data: dict,
    expires_delta: timedelta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
) -> str:
    """Создание JWT токена с данными и временем истечения."""
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + expires_delta
    
    to_encode.update({"exp": expire, "iat": now, "jti": str(uuid4())})
    
    token = encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return token

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
    
    
# === ПАРОЛИ ===
def hash_password(password: str) -> str:
    """Хеширование пароля (здесь просто возвращаем строку для примера)."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    
    return hashed.decode('utf-8')

def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    """Проверка пароля с хешем."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
