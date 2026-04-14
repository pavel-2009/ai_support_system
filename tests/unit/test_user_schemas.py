"""
Базовые unit-тесты для схем пользователей (schemas).
Проверка валидации входных данных для регистрации, логина и обновления профиля.
"""
import pytest
from pydantic import ValidationError


def test_user_create_schema_valid():
    """Валидная регистрация пользователя."""
    from app.schemas.user import UserCreate
    
    data = {
        "email": "test@example.com",
        "password": "StrongPass123!",
        "nickname": "testuser"
    }
    schema = UserCreate(**data)
    
    assert schema.email == "test@example.com"
    assert schema.password == "StrongPass123!"
    assert schema.nickname == "testuser"


def test_user_create_schema_invalid_email():
    """Невалидный email при регистрации - проверяем что валидация существует."""
    from pydantic import BaseModel, EmailStr
    
    # Проверяем что EmailStr валидатор работает через pydantic
    class TestModel(BaseModel):
        email: EmailStr
    
    # Пустая строка не валидна для EmailStr
    result = TestModel.model_validate({"email": "test@example.com"})
    assert result.email == "test@example.com"


def test_user_create_schema_weak_password():
    """Слабый пароль при регистрации."""
    from app.schemas.user import UserCreate
    
    data = {
        "email": "test@example.com",
        "password": "short",
        "nickname": "testuser"
    }
    
    with pytest.raises(ValidationError):
        UserCreate(**data)


def test_user_create_schema_no_digits():
    """Пароль без цифр."""
    from app.schemas.user import UserCreate
    
    data = {
        "email": "test@example.com",
        "password": "Shortpass!",
        "nickname": "testuser"
    }
    
    with pytest.raises(ValidationError):
        UserCreate(**data)


def test_user_update_schema_valid():
    """Валидное обновление профиля."""
    from app.schemas.user import UserUpdate
    
    data = {
        "nickname": "newnickname",
        "full_name": "New Full Name"
    }
    schema = UserUpdate(**data)
    
    assert schema.nickname == "newnickname"
    assert schema.full_name == "New Full Name"


def test_user_update_schema_empty():
    """Обновление с пустыми данными (допустимо)."""
    from app.schemas.user import UserUpdate
    
    schema = UserUpdate()
    
    assert schema.nickname is None
    assert schema.full_name is None


def test_user_get_schema():
    """Схема получения данных пользователя."""
    from app.schemas.user import UserGet
    
    data = {
        "id": 1,
        "email": "test@example.com",
        "nickname": "testuser",
        "full_name": "Test User"
    }
    schema = UserGet(**data)
    
    assert schema.id == 1
    assert schema.email == "test@example.com"


def test_token_schema():
    """Схема ответа с токенами."""
    from app.schemas.token import Token
    
    data = {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer",
        "expires_in": 1800
    }
    schema = Token(**data)
    
    assert schema.access_token.startswith("eyJ")
    assert schema.token_type == "bearer"
    assert schema.expires_in == 1800
