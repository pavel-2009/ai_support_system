"""Pydantic схемы для работы с пользователями."""

import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,32}$")


def validate_username(value: str) -> str:
    """Проверить username/nickname по безопасному формату."""
    value = value.strip()
    if not USERNAME_PATTERN.fullmatch(value):
        raise ValueError(
            "Username должен содержать 3-32 символа: латинские буквы, цифры, _ или -"
        )
    return value


class UserBase(BaseModel):
    """Базовая модель пользователя."""

    email: EmailStr
    nickname: str = Field(..., min_length=3, max_length=32)
    full_name: str | None = Field(default=None, alias="fullname")

    model_config = ConfigDict(populate_by_name=True)

    _validate_nickname = field_validator("nickname")(validate_username)


class UserCreate(UserBase):
    """Модель для создания пользователя."""

    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not any(char.islower() for char in value):
            raise ValueError("Пароль должен содержать хотя бы одну строчную букву")
        if not any(char.isupper() for char in value):
            raise ValueError("Пароль должен содержать хотя бы одну заглавную букву")
        if not any(char.isdigit() for char in value):
            raise ValueError("Пароль должен содержать хотя бы одну цифру")
        if not any(char in "!@#$%^&*()-_=+[]{}|;:'\",.<>?/" for char in value):
            raise ValueError("Пароль должен содержать хотя бы один специальный символ")
        return value


class UserGet(UserBase):
    """Модель для получения информации о пользователе."""

    id: int
    role: str = "user"

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class UserUpdate(BaseModel):
    """Модель для обновления информации о пользователе."""

    nickname: str | None = Field(default=None, min_length=3, max_length=32)
    full_name: str | None = Field(default=None, alias="fullname")

    model_config = ConfigDict(populate_by_name=True)

    _validate_nickname = field_validator("nickname")(validate_username)


class UserLogin(BaseModel):
    """Модель для аутентификации пользователя."""

    email: EmailStr
    password: str
