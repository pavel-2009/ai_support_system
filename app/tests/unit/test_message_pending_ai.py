"""Регрессионные тесты для конфликтов при отправке сообщений."""

from uuid import uuid4


def test_send_message_while_ai_is_processing_returns_409(client, create_test_user):
    email = f"msg_pending_ai_{uuid4().hex[:8]}@example.com"
    create_test_user(
        email=email,
        password="TestPass123!",
        nickname=f"msg_pending_ai_{uuid4().hex[:8]}",
    )

    login = client.post(
        "/api/auth/login",
        json={"email": email, "password": "TestPass123!"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    conversation = client.post(
        "/api/conversations/",
        headers=headers,
        json={"priority": "low", "channel": "web"},
    )
    assert conversation.status_code == 201
    conversation_id = conversation.json()["id"]

    first = client.post(
        f"/api/conversations/{conversation_id}/messages",
        headers=headers,
        json={"content": "Первый вопрос"},
    )
    assert first.status_code == 201

    second = client.post(
        f"/api/conversations/{conversation_id}/messages",
        headers=headers,
        json={"content": "Второй вопрос до ответа AI"},
    )

    assert second.status_code == 409
    assert second.json()["detail"] == "Диалог сейчас не принимает сообщения пользователя."
