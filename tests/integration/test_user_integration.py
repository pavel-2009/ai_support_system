"""
Интеграционные тесты для взаимодействия компонентов системы.
Тестирование связки репозиторий + сервис + API.
"""
import pytest


class TestUserRegistrationIntegration:
    """Интеграционные тесты регистрации пользователей."""

    @pytest.mark.asyncio
    async def test_full_registration_flow_db(self, async_session):
        """Полный цикл регистрации с записью в БД."""
        from app.repositories.user_repo import UserRepository
        from app.schemas.user import UserCreate
        
        user_data = UserCreate(
            email="integration@example.com",
            password="TestPass123!",
            nickname="integration"
        )
        
        # Создаём через репозиторий
        user = await UserRepository.register_user(
            async_session,
            name=user_data.nickname,
            email=user_data.email
        )
        
        assert user is not None
        assert user.email == "integration@example.com"
        
        # Проверяем что пользователь существует
        exists = await UserRepository.user_exists(async_session, email="integration@example.com")
        assert exists is True

    @pytest.mark.asyncio
    async def test_duplicate_registration_prevention(self, async_session, create_test_user):
        """Предотвращение дублирования при регистрации."""
        from app.repositories.user_repo import UserRepository
        
        existing_user = create_test_user(email="duplicate-integration@example.com")
        
        with pytest.raises(ValueError, match="Пользователь с таким email уже существует"):
            await UserRepository.register_user(
                async_session,
                name="duplicate",
                email="duplicate-integration@example.com"
            )


class TestAuthenticationIntegration:
    """Интеграционные тесты аутентификации."""

    @pytest.mark.asyncio
    async def test_token_creation_and_verification(self, async_session, create_test_user):
        """Создание и проверка токенов."""
        from app.repositories.user_repo import UserRepository
        from app.core.security import verify_access_token, verify_refresh_token
        
        user = create_test_user(email="token-test@example.com")
        
        tokens = await UserRepository.create_tokens_for_user(async_session, user.id)
        
        assert tokens.access_token is not None
        assert tokens.refresh_token is not None
        
        # Проверяем что токены валидны
        access_payload = verify_access_token(tokens.access_token)
        assert access_payload is not None
        assert access_payload["user_id"] == user.id
        
        refresh_payload = verify_refresh_token(tokens.refresh_token)
        assert refresh_payload is not None

    @pytest.mark.asyncio
    async def test_password_hashing_and_verification(self, async_session):
        """Хеширование и проверка паролей."""
        from app.core.security import hash_password, verify_password
        
        password = "SecurePassword123!"
        hashed = hash_password(password)
        
        # Проверяем что хеш не равен паролю
        assert hashed != password
        
        # Проверяем что правильный пароль проходит
        assert verify_password(password, hashed) is True
        
        # Проверяем что неправильный пароль не проходит
        assert verify_password("WrongPassword!", hashed) is False


class TestConversationIntegration:
    """Интеграционные тесты диалогов."""

    @pytest.mark.asyncio
    async def test_conversation_creation_with_messages(self, async_session, create_test_user):
        """Создание диалога с сообщениями."""
        from app.models.conversation import Conversation, Message, ConversationStatus
        from sqlalchemy import select
        
        user = create_test_user(email="conv-integration@example.com")
        
        # Создаём диалог
        conversation = Conversation(
            user_id=user.id,
            status=ConversationStatus.OPEN,
            channel="web"
        )
        async_session.add(conversation)
        await async_session.commit()
        await async_session.refresh(conversation)
        
        assert conversation.id is not None
        assert conversation.status == ConversationStatus.OPEN
        
        # Добавляем сообщение
        message = Message(
            conversation_id=conversation.id,
            sender_type="user",
            content="Привет! У меня вопрос."
        )
        async_session.add(message)
        await async_session.commit()
        
        # Проверяем что сообщение сохранилось
        result = await async_session.execute(
            select(Message).where(Message.conversation_id == conversation.id)
        )
        messages = result.scalars().all()
        
        assert len(messages) == 1
        assert messages[0].content == "Привет! У меня вопрос."


class TestRBACIntegration:
    """Интеграционные тесты ролевой модели."""

    @pytest.mark.asyncio
    async def test_user_role_assignment(self, async_session):
        """Назначение ролей пользователям."""
        from app.models.user import User, UserRole
        from app.core.security import hash_password
        
        # Создаём пользователя с ролью operator
        user = User(
            nickname="operator_user",
            fullname="Operator User",
            email="operator@example.com",
            hashed_password=hash_password("TestPass123!"),
            role=UserRole.OPERATOR
        )
        async_session.add(user)
        await async_session.commit()
        
        assert user.role == UserRole.OPERATOR
        
        # Создаём админа
        admin = User(
            nickname="admin_user",
            fullname="Admin User",
            email="admin@example.com",
            hashed_password=hash_password("TestPass123!"),
            role=UserRole.ADMIN
        )
        async_session.add(admin)
        await async_session.commit()
        
        assert admin.role == UserRole.ADMIN

    def test_role_enum_values(self):
        """Проверка значений enum ролей."""
        from app.models.user import UserRole
        
        assert UserRole.USER.value == "user"
        assert UserRole.OPERATOR.value == "operator"
        assert UserRole.ADMIN.value == "admin"


class TestAuditLogIntegration:
    """Интеграционные тесты аудита."""

    @pytest.mark.asyncio
    async def test_audit_log_creation(self, async_session, create_test_user):
        """Создание записей audit log."""
        from app.models.audit_log import AuditLog
        
        user = create_test_user(email="audit-test@example.com")
        
        # Создаём запись аудита
        audit_entry = AuditLog(
            user_id=user.id,
            action="USER_UPDATED",
            entity_type="User",
            entity_id=user.id,
            metadata={"changed_fields": ["nickname"]}
        )
        async_session.add(audit_entry)
        await async_session.commit()
        
        assert audit_entry.id is not None
        assert audit_entry.action == "USER_UPDATED"
