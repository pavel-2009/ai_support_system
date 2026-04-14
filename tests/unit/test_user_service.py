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
        
        with patch("app.repositories.user_repo.UserRepository.get_by_id", return_value=mock_user):
            result = await UserService.get_user_by_id(mock_session, 1)
            assert result.id == 1
            assert result.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self):
        """Получение несуществующего пользователя."""
        from app.services.user_service import UserService
        
        mock_session = AsyncMock()
        
        with patch("app.repositories.user_repo.UserRepository.get_by_id", return_value=None):
            with pytest.raises(ValueError, match="Пользователь с таким ID не найден"):
                await UserService.get_user_by_id(mock_session, 999)

    @pytest.mark.asyncio
    async def test_delete_user_success(self):
        """Успешное удаление пользователя."""
        from app.services.user_service import UserService
        from app.models.user import UserRole
        
        mock_session = AsyncMock()
        mock_admin = MagicMock()
        mock_admin.role = UserRole.ADMIN
        
        with patch("app.repositories.user_repo.UserRepository.delete", return_value=None):
            with patch("app.services.user_service.UserService.get_user_by_id", return_value=MagicMock()):
                await UserService.delete_user(mock_session, 1, mock_admin)
                # Just verify it doesn't raise an error

    @pytest.mark.asyncio
    async def test_get_user_by_email_success(self):
        """Test getting user by email."""
        from app.services.user_service import UserService
        
        mock_session = AsyncMock()
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        
        with patch("app.repositories.user_repo.UserRepository.get_by_email", return_value=mock_user):
            result = await UserService.get_user_by_email(mock_session, "test@example.com")
            assert result.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self):
        """Test getting non-existent user by email."""
        from app.services.user_service import UserService
        
        mock_session = AsyncMock()
        
        with patch("app.repositories.user_repo.UserRepository.get_by_email", return_value=None):
            with pytest.raises(ValueError, match="Пользователь с таким email не найден"):
                await UserService.get_user_by_email(mock_session, "notfound@example.com")

    @pytest.mark.asyncio
    async def test_get_all_users(self):
        """Test getting all users."""
        from app.services.user_service import UserService
        
        mock_session = AsyncMock()
        mock_users = [MagicMock(id=1), MagicMock(id=2)]
        
        with patch("app.repositories.user_repo.UserRepository.list_all", return_value=mock_users):
            result = await UserService.get_all_users(mock_session)
            assert len(result) == 2

    @pytest.mark.asyncio
    async def test_register_user_success(self):
        """Test user registration."""
        from app.services.user_service import UserService
        from app.schemas.user import UserCreate
        
        mock_session = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = 1
        
        user_data = UserCreate(
            email="newuser@example.com",
            password="Pass123!",
            nickname="newuser",
            full_name="New User"
        )
        
        with patch("app.repositories.user_repo.UserRepository.exists", return_value=False):
            with patch("app.repositories.user_repo.UserRepository.create", return_value=mock_user):
                with patch("app.core.security.hash_password", return_value="hashed"):
                    result = await UserService.register_user(mock_session, user_data)
                    assert result.id == 1

    @pytest.mark.asyncio
    async def test_register_user_email_exists(self):
        """Test registration with existing email."""
        from app.services.user_service import UserService
        from app.schemas.user import UserCreate
        
        mock_session = AsyncMock()
        user_data = UserCreate(
            email="existing@example.com",
            password="Pass123!",
            nickname="existing",
            full_name="Existing User"
        )
        
        with patch("app.repositories.user_repo.UserRepository.exists", return_value=True):
            with pytest.raises(ValueError, match="Пользователь с таким email уже существует"):
                await UserService.register_user(mock_session, user_data)

    @pytest.mark.asyncio
    async def test_login_user_success(self):
        """Test user login."""
        from app.services.user_service import UserService
        from app.schemas.user import UserLogin
        from app.models.user import UserRole
        
        mock_session = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.role = UserRole.USER
        mock_user.hashed_password = "hashed_password"
        
        login_data = UserLogin(email="test@example.com", password="Pass123!")
        
        with patch("app.repositories.user_repo.UserRepository.get_by_email", return_value=mock_user):
            with patch("app.services.user_service.verify_password", return_value=True):
                with patch("app.services.user_service.create_tokens") as mock_tokens:
                    mock_tokens.return_value = MagicMock()
                    result = await UserService.login_user(mock_session, login_data)
                    assert result is not None

    @pytest.mark.asyncio
    async def test_refresh_token(self):
        """Test token refresh."""
        from app.services.user_service import UserService
        from app.models.user import UserRole
        
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.role = UserRole.USER
        
        with patch("app.core.security.create_tokens") as mock_tokens:
            mock_tokens.return_value = MagicMock()
            result = await UserService.refresh_token(mock_user)
            assert result is not None

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
