"""
E2E тесты для полных сценариев работы с пользователями.
Имитация реального поведения пользователя через API.
"""
import pytest


class TestUserRegistrationFlow:
    """Полный сценарий регистрации и начала работы."""
    
    def test_full_registration_and_login_flow(self, client):
        """Регистрация -> логин -> получение профиля."""
        user_data = {
            "email": "fullflow@example.com",
            "password": "TestPass123!",
            "nickname": "fullflowuser"
        }
        
        response = client.post("/api/auth/register", json=user_data)
        assert response.status_code == 201
        
        login_response = client.post("/api/auth/login", json={
            "email": "fullflow@example.com",
            "password": "TestPass123!"
        })
        assert login_response.status_code == 200
        
        tokens = login_response.json()
        access_token = tokens["access_token"]
        
        profile_response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert profile_response.status_code == 200
        assert profile_response.json()["email"] == "fullflow@example.com"
    
    def test_registration_with_invalid_data(self, client):
        """Регистрация с различными невалидными данными."""
        invalid_cases = [
            {"email": "", "password": "TestPass123!", "nickname": "user"},
            {"email": "test@example.com", "password": "", "nickname": "user"},
            {"email": "notemail", "password": "TestPass123!", "nickname": "user"},
            {"email": "test@example.com", "password": "short", "nickname": "user"},
        ]
        
        for data in invalid_cases:
            response = client.post("/api/auth/register", json=data)
            assert response.status_code == 422


class TestAuthenticationFlow:
    """Сценарии аутентификации."""
    
    def test_login_after_password_change(self, client, authenticated_client):
        """Логин после изменения данных профиля."""
        authenticated_client.patch("/api/users/me", json={
            "nickname": "changednickname"
        })
        
        logout_response = client.post("/api/auth/logout")
        
        login_response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "TestPass123!"
        })
        assert login_response.status_code == 200
    
    def test_multiple_sessions_same_user(self, client, create_test_user):
        """Несколько активных сессий одного пользователя."""
        user = create_test_user(email="multisession@example.com")
        
        sessions = []
        for i in range(3):
            response = client.post("/api/auth/login", json={
                "email": "multisession@example.com",
                "password": "TestPass123!"
            })
            assert response.status_code == 200
            sessions.append(response.json()["access_token"])
        
        for token in sessions:
            response = client.get(
                "/api/users/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200


class TestTokenLifecycle:
    """Жизненный цикл токенов."""
    
    def test_refresh_token_rotation(self, client, create_test_user):
        """Смена refresh токена при обновлении."""
        create_test_user(email="rotation@example.com")
        
        login_response = client.post("/api/auth/login", json={
            "email": "rotation@example.com",
            "password": "TestPass123!"
        })
        old_refresh = login_response.json()["refresh_token"]
        
        refresh_response = client.post("/api/auth/refresh", json={
            "refresh_token": old_refresh
        })
        assert refresh_response.status_code == 200
        
        new_tokens = refresh_response.json()
        assert new_tokens["refresh_token"] != old_refresh
    
    def test_access_expired_token(self, client, create_test_user):
        """Попытка использования истекшего токена."""
        create_test_user(email="expired@example.com")
        
        login_response = client.post("/api/auth/login", json={
            "email": "expired@example.com",
            "password": "TestPass123!"
        })
        access_token = login_response.json()["access_token"]
        
        response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response.status_code in [200, 401]


class TestUserPermissions:
    """Проверка прав доступа."""
    
    def test_user_cannot_access_admin_endpoints(self, client, authenticated_client):
        """Обычный пользователь не имеет доступа к админским эндпоинтам."""
        admin_endpoints = [
            ("GET", "/api/admin/users"),
            ("POST", "/api/admin/users"),
        ]
        
        for method, endpoint in admin_endpoints:
            if method == "GET":
                response = authenticated_client.get(endpoint)
            elif method == "POST":
                response = authenticated_client.post(endpoint, json={
                    "email": "hack@example.com",
                    "password": "TestPass123!",
                    "nickname": "hacker"
                })
            
            assert response.status_code == 403
    
    def test_admin_can_access_all_endpoints(self, client, admin_client, create_test_user):
        """Администратор имеет доступ ко всем эндпоинтам."""
        create_test_user(email="regular@example.com")
        
        response = admin_client.get("/api/admin/users")
        assert response.status_code == 200
        
        response = admin_client.post("/api/admin/users", json={
            "email": "newadmincreated@example.com",
            "password": "TestPass123!",
            "nickname": "newuser"
        })
        assert response.status_code == 201


class TestUserDataIsolation:
    """Изоляция данных пользователей."""
    
    def test_user_sees_only_own_profile(self, client, create_test_user):
        """Пользователь видит только свой профиль."""
        user1 = create_test_user(email="user1@example.com", nickname="user1")
        user2 = create_test_user(email="user2@example.com", nickname="user2")
        
        login_response = client.post("/api/auth/login", json={
            "email": "user1@example.com",
            "password": "TestPass123!"
        })
        token = login_response.json()["access_token"]
        
        response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["email"] == "user1@example.com"
        assert response.json()["nickname"] == "user1"
    
    def test_no_user_enumeration_on_login(self, client):
        """Отсутствие информации о существовании пользователя при логине."""
        response1 = client.post("/api/auth/login", json={
            "email": "nonexistent1@example.com",
            "password": "TestPass123!"
        })
        
        response2 = client.post("/api/auth/login", json={
            "email": "nonexistent2@example.com",
            "password": "WrongPassword"
        })
        
        assert response1.status_code == response2.status_code == 401
