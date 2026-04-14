"""
Конфигурация и фикстуры для тестов.
Базовые фикстуры для работы с TestClient, БД и пользователями.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from main import app
from app.db import Base, get_async_session
from app.core.config import settings
from app.models.user import User, UserRole
from app.core.security import hash_password


# === ТЕСТОВАЯ БД ===
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    """Создание тестового движка БД."""
    return create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture(scope="session")
async def async_session_factory(engine):
    """Фабрика сессий для тестов."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def async_session(async_session_factory):
    """Асинхронная сессия для каждого теста."""
    async with async_session_factory() as session:
        yield session


# === FIXTURES ДЛЯ CLIENT ===
@pytest.fixture
def client(async_session):
    """TestClient для HTTP-запросов."""
    
    def override_get_async_session():
        yield async_session
    
    app.dependency_overrides[get_async_session] = override_get_async_session
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def authenticated_client(client, create_test_user):
    """Авторизованный клиент (обычный пользователь)."""
    user = create_test_user(email="test@example.com", password="TestPass123!")
    
    login_response = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "TestPass123!"
    })
    
    if login_response.status_code == 200:
        token = login_response.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"
    
    return client


@pytest.fixture
def admin_client(client, create_test_user):
    """Клиент с правами администратора."""
    from app.core.security import create_tokens
    
    admin = create_test_user(
        email="admin@example.com",
        password="AdminPass123!",
        role=UserRole.ADMIN
    )
    
    tokens = create_tokens({"user_id": admin.id})
    client.headers["Authorization"] = f"Bearer {tokens.access_token}"
    
    return client


@pytest.fixture
def operator_client(client, create_test_user):
    """Клиент с правами оператора."""
    from app.core.security import create_tokens
    
    operator = create_test_user(
        email="operator@example.com",
        password="OperatorPass123!",
        role=UserRole.OPERATOR
    )
    
    tokens = create_tokens({"user_id": operator.id})
    client.headers["Authorization"] = f"Bearer {tokens.access_token}"
    
    return client


# === FIXTURES ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ===
@pytest.fixture
async def create_test_user(async_session):
    """Фикстура для создания тестовых пользователей."""
    created_users = []
    
    async def _create_user(
        email: str = "test@example.com",
        password: str = "TestPass123!",
        nickname: str = "testuser",
        full_name: str = "Test User",
        role: UserRole = UserRole.USER
    ):
        from sqlalchemy import insert
        
        hashed_pw = hash_password(password)
        
        stmt = insert(User).values(
            email=email,
            nickname=nickname,
            fullname=full_name,
            hashed_password=hashed_pw,
            role=role
        ).returning(User)
        
        result = await async_session.execute(stmt)
        await async_session.commit()
        
        user = result.scalar_one()
        created_users.append(user.id)
        
        return user
    
    yield _create_user
    
    # Cleanup
    for user_id in created_users:
        try:
            from sqlalchemy import delete
            await async_session.execute(delete(User).where(User.id == user_id))
            await async_session.commit()
        except Exception:
            await async_session.rollback()


@pytest.fixture
async def create_test_conversation(async_session, create_test_user):
    """Фикстура для создания тестовых диалогов."""
    created_conversations = []
    
    async def _create_conversation(
        user_id: int = None,
        status: str = "open",
        priority: str = "medium",
        channel: str = "web"
    ):
        from app.models.conversation import Conversation
        
        if user_id is None:
            user = await create_test_user(email=f"conv-{len(created_conversations)}@example.com")
            user_id = user.id
        
        conversation = Conversation(
            user_id=user_id,
            status=status,
            priority=priority,
            channel=channel
        )
        
        async_session.add(conversation)
        await async_session.commit()
        await async_session.refresh(conversation)
        
        created_conversations.append(conversation.id)
        
        return conversation
    
    yield _create_conversation
    
    # Cleanup
    for conv_id in created_conversations:
        try:
            from sqlalchemy import delete
            from app.models.conversation import Conversation
            await async_session.execute(delete(Conversation).where(Conversation.id == conv_id))
            await async_session.commit()
        except Exception:
            await async_session.rollback()


# === PYTEST CONFIGURATION ===
def pytest_configure(config):
    """Настройка pytest."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as an asyncio test."
    )
