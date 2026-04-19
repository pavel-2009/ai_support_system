"""E2E сценарии пользовательского цикла и диалогов без AI."""

from uuid import uuid4


def _register_and_login(client, email: str, password: str = "TestPass123!") -> dict[str, str]:
    nickname = f"user_{uuid4().hex[:8]}"
    register_response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "nickname": nickname},
    )
    assert register_response.status_code == 201

    login_response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert login_response.status_code == 200
    return login_response.json()


class TestUsersAndConversationCycleE2E:
    """Проверка пользовательских и conversation-сценариев end-to-end."""

    def test_user_profile_update_cycle(self, client):
        email = f"profile_{uuid4().hex[:8]}@example.com"
        tokens = _register_and_login(client, email)
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        me_response = client.get("/api/users/me", headers=headers)
        assert me_response.status_code == 200
        assert me_response.json()["email"] == email

        update_response = client.patch(
            "/api/users/me",
            headers=headers,
            json={"nickname": "updated_profile_user", "fullname": "Updated Profile User"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["nickname"] == "updated_profile_user"
        assert update_response.json()["fullname"] == "Updated Profile User"

    def test_full_conversation_cycle_without_ai(self, client):
        email = f"conversation_{uuid4().hex[:8]}@example.com"
        tokens = _register_and_login(client, email)
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        create_conversation = client.post(
            "/api/conversations/",
            headers=headers,
            json={"priority": "medium", "channel": "web"},
        )
        assert create_conversation.status_code == 201
        conversation_id = create_conversation.json()["id"]

        first_message = client.post(
            f"/api/conversations/{conversation_id}/messages",
            headers=headers,
            json={"content": "Здравствуйте! Нужна помощь с заказом."},
        )
        assert first_message.status_code == 201

        second_message = client.post(
            f"/api/conversations/{conversation_id}/messages",
            headers=headers,
            json={"content": "Добавляю детали по проблеме."},
        )
        assert second_message.status_code == 201

        get_messages = client.get(f"/api/conversations/{conversation_id}/messages", headers=headers)
        assert get_messages.status_code == 200
        assert len(get_messages.json()) == 2

        close_response = client.post(f"/api/conversations/{conversation_id}/close", headers=headers)
        assert close_response.status_code == 200
        assert close_response.json()["status"] == "closed"

        closed_conversation = client.get(f"/api/conversations/{conversation_id}", headers=headers)
        assert closed_conversation.status_code == 410

        closed_messages = client.get(f"/api/conversations/{conversation_id}/messages", headers=headers)
        assert closed_messages.status_code == 410
