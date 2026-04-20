"""
Конфигурация и фикстуры для тестов.
Базовые фикстуры для работы с TestClient, БД и пользователями.
"""
import pytest
import asyncio
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from main import app
from app.db import Base, get_async_session
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


def _create_authenticated_client(async_session, user_email: str, user_role: UserRole = UserRole.USER):
    """Helper для создания независимого авторизованного клиента."""
    from app.core.security import create_tokens
    
    def override_get_async_session():
        yield async_session
    
    app.dependency_overrides[get_async_session] = override_get_async_session
    
    test_client = TestClient(app)
    
    # Создаём пользователя в БД
    loop = asyncio.new_event_loop()
    
    async def create_user_in_db():
        from sqlalchemy import delete, insert
        await async_session.execute(delete(User).where(User.email == user_email))
        await async_session.commit()
        
        hashed_pw = hash_password("TestPass123!")
        stmt = insert(User).values(
            email=user_email,
            nickname=user_email.split("@")[0],
            fullname=f"{user_email.split('@')[0]} full",
            hashed_password=hashed_pw,
            role=user_role
        ).returning(User)
        
        result = await async_session.execute(stmt)
        user = result.scalar_one()
        await async_session.commit()
        return user
    
    user = loop.run_until_complete(create_user_in_db())
    loop.close()
    
    # Создаём токены
    tokens = create_tokens({"user_id": user.id, "email": user.email, "role": user.role.value})
    test_client.headers["Authorization"] = f"Bearer {tokens.access_token}"
    
    return test_client


@pytest.fixture
def authenticated_client(async_session):
    """Авторизованный клиент (обычный пользователь)."""
    email = "test@example.com"
    test_client = _create_authenticated_client(async_session, email, UserRole.USER)
    
    yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def admin_client(async_session):
    """Клиент с правами администратора."""
    email = f"admin-{uuid4().hex[:8]}@example.com"
    test_client = _create_authenticated_client(async_session, email, UserRole.ADMIN)
    
    yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def operator_client(async_session):
    """Клиент с правами оператора."""
    email = f"operator-{uuid4().hex[:8]}@example.com"
    test_client = _create_authenticated_client(async_session, email, UserRole.OPERATOR)
    
    yield test_client
    
    app.dependency_overrides.clear()


# === FIXTURES ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ===
@pytest.fixture
def create_test_user(async_session):
    """Фикстура для создания тестовых пользователей."""
    loop = asyncio.new_event_loop()

    async def _create_user_async(
        email: str = "test@example.com",
        password: str = "TestPass123!",
        nickname: str | None = None,
        full_name: str | None = None,
        role: UserRole = UserRole.USER
    ):
        from sqlalchemy import delete, insert

        nickname = nickname or email.split("@", maxsplit=1)[0]
        full_name = full_name or f"{nickname} full"
        await async_session.execute(delete(User).where(User.email == email))
        await async_session.execute(delete(User).where(User.nickname == nickname))
        await async_session.execute(delete(User).where(User.fullname == full_name))
        await async_session.commit()
        
        hashed_pw = hash_password(password)
        
        stmt = insert(User).values(
            email=email,
            nickname=nickname,
            fullname=full_name,
            hashed_password=hashed_pw,
            role=role
        ).returning(User)
        
        result = await async_session.execute(stmt)
        
        user = result.scalar_one()
        await async_session.commit()
        
        return user

    def _create_user(**kwargs):
        return asyncio.run(_create_user_async(**kwargs))

    yield _create_user


# === PYTEST CONFIGURATION ===
def pytest_configure(config):
    """Настройка pytest."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as an asyncio test."
    )
