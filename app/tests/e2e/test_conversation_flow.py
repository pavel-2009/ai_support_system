"""E2E тест для проверки корректности всего цикла диалогов (пока без ИИ)."""

import asyncio

from app.repositories.conversation_state_machine import ConversationStateMachine


class TestConversationFlow:
    """Класс для тестирования полного цикла диалогов."""

    def test_full_conversation_flow(self, authenticated_client, operator_client, async_session):
        """Тестирование полного цикла диалогов."""

        response = authenticated_client.post("/conversations/", json={
            "priority": "medium",
            "channel": "api",
        })
        assert response.status_code == 201

        conversation_id = response.json()["id"]

        response = authenticated_client.get(f"/conversations/{conversation_id}")
        assert response.status_code == 200
        assert response.json()["id"] == conversation_id
        assert response.json()["status"] == "open"

        response = authenticated_client.post(f"/conversations/{conversation_id}/messages/", json={
            "content": "Привет, мне нужна помощь!",
        })
        assert response.status_code == 201

        response = authenticated_client.get("/operator/queue/")
        assert response.status_code == 403

        response = operator_client.get("/operator/queue/")
        assert response.status_code == 200

        # Статусы изменяются только через State Machine.
        state_machine = ConversationStateMachine(async_session)
        asyncio.run(state_machine.escalate(conversation_id))

        response = operator_client.get("/operator/queue/")
        assert response.status_code == 200
        assert conversation_id in [conv["id"] for conv in response.json()]

        response = operator_client.post(f"/operator/assign/{conversation_id}")
        assert response.status_code == 200

        response = operator_client.get("/operator/queue/")
        assert response.status_code == 200
        assert conversation_id not in [conv["id"] for conv in response.json()]

        response = operator_client.get(f"/conversations/{conversation_id}")
        assert response.status_code == 200
        assert response.json()["operator_id"] is not None

        response = operator_client.post(f"/operator/reply/{conversation_id}/", json={
            "message": "Здравствуйте! Я оператор, чем могу помочь?",
        })
        assert response.status_code == 200

        response = authenticated_client.get(f"/conversations/{conversation_id}/messages/")
        assert response.status_code == 200
        messages = response.json()
        assert any(msg["content"] == "Здравствуйте! Я оператор, чем могу помочь?" for msg in messages)

        response = operator_client.post(f"/operator/back_to_ai/{conversation_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "open"

        response = authenticated_client.get(f"/conversations/{conversation_id}")
        assert response.status_code == 200
        assert response.json()["operator_id"] is None

        response = operator_client.get("/operator/queue/")
        assert response.status_code == 200
        assert conversation_id not in [conv["id"] for conv in response.json()]

        response = operator_client.post(f"/operator/close/{conversation_id}/")
        assert response.status_code == 200
        assert response.json()["detail"] == "Диалог успешно закрыт."
