import os
import sys
import types
import importlib.metadata as importlib_metadata

# Минимальные переменные окружения для инициализации Settings в тестах.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_app.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")

# Заглушка для email_validator, чтобы pydantic EmailStr корректно импортировался.
if "email_validator" not in sys.modules:
    email_validator = types.ModuleType("email_validator")

    class EmailNotValidError(ValueError):
        pass

    def validate_email(email, check_deliverability=False):
        return types.SimpleNamespace(email=email)

    email_validator.EmailNotValidError = EmailNotValidError
    email_validator.validate_email = validate_email
    email_validator.__version__ = "2.0.0"
    sys.modules["email_validator"] = email_validator

_original_version = importlib_metadata.version


def _patched_version(name: str) -> str:
    if name == "email-validator":
        return "2.0.0"
    return _original_version(name)


importlib_metadata.version = _patched_version
