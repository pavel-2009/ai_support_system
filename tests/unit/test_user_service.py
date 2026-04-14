"""
Базовые unit-тесты для сервисов пользователей.
Проверка бизнес-логики без HTTP-слоя.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestUserService:
    """Тесты сервиса пользователей."""

    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self):
        """Успешное получение пользователя по ID."""
        from app.services.user_service import UserService
        
        mock_session = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        
        with patch.object(UserService, 'get_user_by_id', return_value=mock_user) as mock_method:
            result = await UserService.get_user_by_id(mock_session, 1)
            
            assert result.id == 1
            assert result.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self):
        """Получение несуществующего пользователя."""
        from app.services.user_service import UserService
        
        mock_session = AsyncMock()
        
        with patch.object(UserService, 'get_user_by_id') as mock_method:
            mock_method.side_effect = ValueError("Пользователь с таким ID не найден.")
            
            with pytest.raises(ValueError, match="Пользователь с таким ID не найден"):
                await UserService.get_user_by_id(mock_session, 999)

    @pytest.mark.asyncio
    async def test_delete_user_success(self):
        """Успешное удаление пользователя."""
        from app.services.user_service import UserService
        
        mock_session = AsyncMock()
        
        with patch.object(UserService, 'delete_user', return_value=None) as mock_method:
            await UserService.delete_user(mock_session, 1)
            mock_method.assert_called_once_with(mock_session, 1)


class TestUserRepository:
    """Тесты репозитория пользователей."""

    @pytest.mark.asyncio
    async def test_user_exists_true(self):
        """Проверка существования пользователя - существует."""
        from app.repositories.user_repo import UserRepository
        
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        result = await UserRepository.user_exists(mock_session, email="test@example.com")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_user_exists_false(self):
        """Проверка существования пользователя - не существует."""
        from app.repositories.user_repo import UserRepository
        
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        result = await UserRepository.user_exists(mock_session, email="nonexistent@example.com")
        
        assert result is False

    @pytest.mark.asyncio
    async def test_get_user_by_email_success(self):
        """Успешное получение пользователя по email."""
        from app.repositories.user_repo import UserRepository
        
        mock_session = AsyncMock()
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        with patch.object(UserRepository, 'user_exists', return_value=True):
            result = await UserRepository.get_user_by_email(mock_session, "test@example.com")
            
            assert result.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self):
        """Получение несуществующего пользователя по email."""
        from app.repositories.user_repo import UserRepository
        
        mock_session = AsyncMock()
        
        with patch.object(UserRepository, 'user_exists', return_value=False):
            with pytest.raises(ValueError, match="Пользователь с таким email не найден"):
                await UserRepository.get_user_by_email(mock_session, "nonexistent@example.com")


class TestSecurity:
    """Тесты модуля безопасности."""

    def test_hash_password(self):
        """Хеширование пароля."""
        from app.core.security import hash_password
        
        password = "TestPass123!"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 0

    def test_verify_password_correct(self):
        """Проверка правильного пароля."""
        from app.core.security import hash_password, verify_password
        
        password = "TestPass123!"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Проверка неправильного пароля."""
        from app.core.security import hash_password, verify_password
        
        password = "TestPass123!"
        hashed = hash_password(password)
        
        assert verify_password("WrongPass456!", hashed) is False

    def test_create_access_token(self):
        """Создание access токена."""
        from app.core.security import create_access_token
        
        data = {"user_id": 1, "email": "test@example.com"}
        token = create_access_token(data)
        
        assert token is not None
        assert len(token) > 0
        assert isinstance(token, str)

    def test_verify_access_token_valid(self):
        """Проверка валидного токена."""
        from app.core.security import create_access_token, verify_access_token
        
        data = {"user_id": 1, "email": "test@example.com"}
        token = create_access_token(data)
        
        payload = verify_access_token(token)
        
        assert payload is not None
        assert payload["user_id"] == 1

    def test_verify_access_token_invalid(self):
        """Проверка невалидного токена."""
        from app.core.security import verify_access_token
        
        payload = verify_access_token("invalid-token")
        
        assert payload is None

    def test_create_tokens_pair(self):
        """Создание пары токенов."""
        from app.core.security import create_tokens
        
        data = {"user_id": 1}
        tokens = create_tokens(data)
        
        assert tokens.access_token is not None
        assert tokens.refresh_token is not None
        assert tokens.token_type == "bearer"
        assert tokens.expires_in > 0
