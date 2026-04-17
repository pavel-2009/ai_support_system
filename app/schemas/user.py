"""Pydantic схемы для работы с пользователями."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """Базовая модель пользователя."""

    email: EmailStr
    nickname: str
    full_name: str | None = Field(default=None, alias="fullname")

    model_config = ConfigDict(populate_by_name=True)


class UserCreate(UserBase):
    """Модель для создания пользователя."""

    password: str

    @field_validator("password")
    def validate_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Пароль должен быть не менее 8 символов")
        if not any(char.isdigit() for char in value):
            raise ValueError("Пароль должен содержать хотя бы одну цифру")
        if not any(char.isalpha() for char in value):
            raise ValueError("Пароль должен содержать хотя бы одну букву")
        if not any(char in "!@#$%^&*()-_=+[]{}|;:'\",.<>?/" for char in value):
            raise ValueError("Пароль должен содержать хотя бы один специальный символ")
        return value


class UserGet(UserBase):
    """Модель для получения информации о пользователе."""

    id: int

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class UserUpdate(BaseModel):
    """Модель для обновления информации о пользователе."""

    nickname: str | None = None
    full_name: str | None = Field(default=None, alias="fullname")

    model_config = ConfigDict(populate_by_name=True)


class UserLogin(BaseModel):
    """Модель для аутентификации пользователя."""

    email: EmailStr
    password: str
