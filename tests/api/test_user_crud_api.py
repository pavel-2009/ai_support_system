"""
API тесты для CRUD операций с пользователями.
Тестирование через TestClient (FastAPI) - имитация HTTP-запросов.
"""
import pytest


class TestUserCRUD:
    """Тесты CRUD операций с пользователями."""

    def test_get_user_by_id_success(self, client, create_test_user):
        """Успешное получение пользователя по ID."""
        user = create_test_user(email="getuser@example.com", nickname="getuser")
        
        response = client.get(f"/api/users/{user.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "getuser@example.com"
        assert data["nickname"] == "getuser"
        assert "id" in data

    def test_get_user_by_id_not_found(self, client):
        """Получение несуществующего пользователя."""
        response = client.get("/api/users/99999")
        
        assert response.status_code == 404

    def test_create_user_success(self, client, authenticated_client):
        """Успешное создание пользователя (только для авторизованных)."""
        user_data = {
            "email": "newcreated@example.com",
            "password": "TestPass123!",
            "nickname": "newcreated"
        }
        
        response = authenticated_client.post("/api/users/", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["nickname"] == user_data["nickname"]
        assert "id" in data

    def test_create_user_unauthorized(self, client):
        """Создание пользователя без авторизации."""
        user_data = {
            "email": "unauth@example.com",
            "password": "TestPass123!",
            "nickname": "unauth"
        }
        
        response = client.post("/api/users/", json=user_data)
        
        assert response.status_code == 401

    def test_update_user_success(self, client, authenticated_client):
        """Успешное обновление пользователя."""
        update_data = {
            "nickname": "updatednickname",
            "full_name": "Updated Full Name"
        }
        
        response = authenticated_client.patch("/api/users/me", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["nickname"] == "updatednickname"
        assert data["full_name"] == "Updated Full Name"

    def test_delete_user_success(self, client, admin_client, create_test_user):
        """Успешное удаление пользователя администратором."""
        user = create_test_user(email="deleteuser@example.com")
        
        response = admin_client.delete(f"/api/users/{user.id}")
        
        assert response.status_code == 204

    def test_delete_user_not_found(self, client, admin_client):
        """Удаление несуществующего пользователя."""
        response = admin_client.delete("/api/users/99999")
        
        assert response.status_code == 404


class TestUserValidation:
    """Тесты валидации данных пользователей."""

    def test_create_user_duplicate_email(self, client, authenticated_client, create_test_user):
        """Создание пользователя с дублирующимся email."""
        existing_user = create_test_user(email="duplicate@example.com")
        
        user_data = {
            "email": "duplicate@example.com",
            "password": "TestPass123!",
            "nickname": "duplicate"
        }
        
        response = authenticated_client.post("/api/users/", json=user_data)
        
        assert response.status_code == 400

    def test_create_user_invalid_email_format(self, client, authenticated_client):
        """Создание пользователя с невалидным форматом email."""
        user_data = {
            "email": "not-an-email",
            "password": "TestPass123!",
            "nickname": "invalidemail"
        }
        
        response = authenticated_client.post("/api/users/", json=user_data)
        
        assert response.status_code == 422

    def test_create_user_short_password(self, client, authenticated_client):
        """Создание пользователя с коротким паролем."""
        user_data = {
            "email": "shortpass@example.com",
            "password": "short",
            "nickname": "shortpass"
        }
        
        response = authenticated_client.post("/api/users/", json=user_data)
        
        assert response.status_code == 422

    def test_create_user_password_no_digits(self, client, authenticated_client):
        """Создание пользователя с паролем без цифр."""
        user_data = {
            "email": "nodigits@example.com",
            "password": "PasswordNoDigits!",
            "nickname": "nodigits"
        }
        
        response = authenticated_client.post("/api/users/", json=user_data)
        
        assert response.status_code == 422

    def test_create_user_password_no_special_chars(self, client, authenticated_client):
        """Создание пользователя с паролем без спецсимволов."""
        user_data = {
            "email": "nospecial@example.com",
            "password": "Password123456",
            "nickname": "nospecial"
        }
        
        response = authenticated_client.post("/api/users/", json=user_data)
        
        assert response.status_code == 422


class TestUserAccessControl:
    """Тесты контроля доступа к пользователям."""

    def test_regular_user_cannot_delete_users(self, client, authenticated_client, create_test_user):
        """Обычный пользователь не может удалять пользователей."""
        user = create_test_user(email="cannotdelete@example.com")
        
        response = authenticated_client.delete(f"/api/users/{user.id}")
        
        assert response.status_code == 403

    def test_user_can_only_update_own_profile(self, client, create_test_user):
        """Пользователь может обновлять только свой профиль."""
        user1 = create_test_user(email="user1update@example.com", nickname="user1")
        user2 = create_test_user(email="user2update@example.com", nickname="user2")
        
        login_response = client.post("/api/auth/login", json={
            "email": "user1update@example.com",
            "password": "TestPass123!"
        })
        token = login_response.json()["access_token"]
        
        # Пытаемся обновить профиль user2 от имени user1
        response = client.patch(
            f"/api/users/{user2.id}",
            json={"nickname": "hacked"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code in [403, 404]

    def test_admin_can_update_any_user(self, client, admin_client, create_test_user):
        """Администратор может обновлять любого пользователя."""
        user = create_test_user(email="adminupdate@example.com", nickname="original")
        
        response = admin_client.put(
            f"/api/users/{user.id}",
            json={"nickname": "adminupdated", "email": "adminupdated@example.com"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["nickname"] == "adminupdated"


class TestUserListAndSearch:
    """Тесты списков и поиска пользователей."""

    def test_admin_list_all_users(self, client, admin_client, create_test_user):
        """Администратор может получать список всех пользователей."""
        create_test_user(email="listuser1@example.com")
        create_test_user(email="listuser2@example.com")
        
        response = admin_client.get("/api/admin/users")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_regular_user_cannot_list_all_users(self, client, authenticated_client):
        """Обычный пользователь не может получать список всех пользователей."""
        response = authenticated_client.get("/api/admin/users")
        
        assert response.status_code == 403
