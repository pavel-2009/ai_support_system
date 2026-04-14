"""
API тесты для эндпоинтов аутентификации и работы с пользователями.
Тестирование через TestClient (FastAPI) - имитация HTTP-запросов.
"""
import pytest


@pytest.fixture
def test_user_data():
    """Базовые данные тестового пользователя."""
    return {
        "email": "apitest@example.com",
        "password": "TestPass123!",
        "nickname": "apitestuser"
    }


class TestAuthRegistration:
    """Тесты регистрации пользователей."""
    
    def test_register_user_success(self, client, test_user_data):
        """Успешная регистрация нового пользователя."""
        response = client.post("/api/auth/register", json=test_user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert "id" in data
        assert "hashed_password" not in data
    
    def test_register_user_duplicate_email(self, client, test_user_data, create_test_user):
        """Регистрация с уже существующим email."""
        create_test_user(email=test_user_data["email"])
        
        response = client.post("/api/auth/register", json=test_user_data)
        
        assert response.status_code == 400
    
    def test_register_user_invalid_email(self, client):
        """Регистрация с невалидным email."""
        data = {
            "email": "invalid-email",
            "password": "TestPass123!",
            "nickname": "testuser"
        }
        
        response = client.post("/api/auth/register", json=data)
        
        assert response.status_code == 422
    
    def test_register_user_weak_password(self, client):
        """Регистрация со слабым паролем."""
        data = {
            "email": "test@example.com",
            "password": "123",
            "nickname": "testuser"
        }
        
        response = client.post("/api/auth/register", json=data)
        
        assert response.status_code == 422


class TestAuthLogin:
    """Тесты логина пользователей."""
    
    def test_login_success(self, client, create_test_user):
        """Успешный логин."""
        user = create_test_user(email="login@example.com", password="TestPass123!")
        
        response = client.post("/api/auth/login", json={
            "email": "login@example.com",
            "password": "TestPass123!"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_wrong_password(self, client, create_test_user):
        """Логин с неправильным паролем."""
        create_test_user(email="login@example.com", password="CorrectPass123!")
        
        response = client.post("/api/auth/login", json={
            "email": "login@example.com",
            "password": "WrongPass123!"
        })
        
        assert response.status_code == 401
    
    def test_login_nonexistent_user(self, client):
        """Логин несуществующего пользователя."""
        response = client.post("/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "TestPass123!"
        })
        
        assert response.status_code == 401


class TestAuthRefresh:
    """Тесты обновления токена."""
    
    def test_refresh_token_success(self, client, create_test_user):
        """Успешное обновление токена."""
        user = create_test_user(email="refresh@example.com")
        
        login_response = client.post("/api/auth/login", json={
            "email": "refresh@example.com",
            "password": "TestPass123!"
        })
        refresh_token = login_response.json()["refresh_token"]
        
        response = client.post("/api/auth/refresh", json={
            "refresh_token": refresh_token
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
    
    def test_refresh_token_invalid(self, client):
        """Обновление с невалидным refresh токеном."""
        response = client.post("/api/auth/refresh", json={
            "refresh_token": "invalid-token"
        })
        
        assert response.status_code == 401


class TestUserProfile:
    """Тесты профиля пользователя."""
    
    def test_get_own_profile(self, client, authenticated_client, create_test_user):
        """Получение собственного профиля."""
        response = authenticated_client.get("/api/users/me")
        
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "id" in data
        assert "password" not in data
    
    def test_get_profile_unauthorized(self, client):
        """Получение профиля без авторизации."""
        response = client.get("/api/users/me")
        
        assert response.status_code == 401
    
    def test_update_own_profile(self, client, authenticated_client):
        """Обновление собственного профиля."""
        response = authenticated_client.patch("/api/users/me", json={
            "nickname": "newnickname",
            "full_name": "New Full Name"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["nickname"] == "newnickname"
        assert data["full_name"] == "New Full Name"
    
    def test_update_profile_empty_data(self, client, authenticated_client):
        """Обновление профиля с пустыми данными."""
        response = authenticated_client.patch("/api/users/me", json={})
        
        assert response.status_code == 200


class TestUserRoles:
    """Тесты ролей пользователей."""
    
    def test_admin_create_user(self, client, admin_client):
        """Создание пользователя администратором."""
        response = admin_client.post("/api/admin/users", json={
            "email": "newuser@example.com",
            "password": "TestPass123!",
            "nickname": "newuser",
            "role": "user"
        })
        
        assert response.status_code == 201
    
    def test_regular_user_cannot_create_users(self, client, authenticated_client):
        """Обычный пользователь не может создавать пользователей."""
        response = authenticated_client.post("/api/admin/users", json={
            "email": "newuser@example.com",
            "password": "TestPass123!",
            "nickname": "newuser"
        })
        
        assert response.status_code == 403
    
    def test_admin_list_users(self, client, admin_client, create_test_user):
        """Администратор может получать список пользователей."""
        create_test_user(email="user1@example.com")
        create_test_user(email="user2@example.com")
        
        response = admin_client.get("/api/admin/users")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2
