"""Работа с безопасностью, включая создание и проверку JWT токенов."""

from jwt import encode, decode, PyJWTError
import bcrypt
from uuid import uuid4

from datetime import datetime, timedelta

from app.core.config import settings
from app.schemas.token import Token


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
    
    
def create_refresh_token(data: dict) -> str:
    """Создание JWT токена для обновления с данными."""
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire, "iat": now, "jti": str(uuid4())})
    
    token = encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return token


def verify_refresh_token(token: str) -> dict | None:
    """Проверка JWT токена для обновления и извлечение данных."""
    try:
        payload = decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except PyJWTError:
        return None
    
    expired = payload.get("exp")
    if expired is None or datetime.utcfromtimestamp(expired) < datetime.utcnow():
        return None
    
    return payload
    
    
def create_tokens(data: dict) -> Token:
    """Создание пары токенов доступа и обновления."""
    access_token = create_access_token(data=data)
    refresh_token = create_refresh_token(data=data)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    
def update_access_token_with_refresh_token(refresh_token: str) -> str | None:
    """Обновление access токена с помощью refresh токена."""
    
    payload = verify_refresh_token(refresh_token)
    if payload is None:
        return None
    
    # Оставляем ТОЛЬКО полезные данные пользователя, удаляя ВСЕ системные поля JWT
    # Обычно это 'sub' (subject) или ваш 'user_id'
    user_data = {key: value for key, value in payload.items() 
                 if key not in ("exp", "iat", "nbf", "jti")}
    
    return create_access_token(data=user_data)


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
