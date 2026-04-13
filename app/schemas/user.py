"""Pydantic схемы для работы с пользователями."""

from pydantic import BaseModel, EmailStr, field_validator


class UserBase(BaseModel):
    """Базовая модель пользователя."""

    email: EmailStr
    nickname: str
    full_name: str | None = None


class UserCreate(UserBase):
    """Модель для создания пользователя."""

    password: str
    
    @field_validator("password")
    def validate_password(cls, value):
        # Проверка сложности пароля (пример: минимум 8 символов)
        if len(value) < 8:
            raise ValueError("Пароль должен быть не менее 8 символов")
        
        # Проверка на наличие цифр и букв
        if not any(char.isdigit() for char in value):
            raise ValueError("Пароль должен содержать хотя бы одну цифру")
        if not any(char.isalpha() for char in value):
            raise ValueError("Пароль должен содержать хотя бы одну букву")
        
        # Проверка на наличие специальных символов
        if not any(char in "!@#$%^&*()-_=+[]{}|;:'\",.<>?/" for char in value):
            raise ValueError("Пароль должен содержать хотя бы один специальный символ")
        
        return value
    

class UserGet(UserBase):
    """Модель для получения информации о пользователе."""

    id: int

    class Config:
        orm_mode = True
        
        
class UserUpdate(BaseModel):
    """Модель для обновления информации о пользователе."""

    nickname: str | None = None
    full_name: str | None = None
