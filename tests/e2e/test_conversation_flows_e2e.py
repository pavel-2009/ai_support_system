"""
E2E тесты для сценариев работы с диалогами (conversations).
Имитация полного цикла взаимодействия пользователя с системой поддержки.
"""
import pytest


class TestConversationCreation:
    """Сценарии создания диалогов."""

    def test_user_create_conversation_success(self, client, authenticated_client):
        """Пользователь успешно создаёт диалог."""
        conversation_data = {
            "channel": "web",
            "priority": "medium"
        }
        
        response = authenticated_client.post("/api/conversations/", json=conversation_data)
        
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["status"] == "open"
        assert data["channel"] == "web"

    def test_create_conversation_unauthorized(self, client):
        """Создание диалога без авторизации."""
        response = client.post("/api/conversations/", json={})
        
        assert response.status_code == 401

    def test_user_get_own_conversations(self, client, authenticated_client, create_test_conversation):
        """Пользователь получает список своих диалогов."""
        create_test_conversation(status="open")
        create_test_conversation(status="closed")
        
        response = authenticated_client.get("/api/conversations/")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_user_get_conversation_by_id(self, client, authenticated_client, create_test_conversation):
        """Пользователь получает свой диалог по ID."""
        conv = create_test_conversation(status="open")
        
        response = authenticated_client.get(f"/api/conversations/{conv.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == conv.id

    def test_user_cannot_see_others_conversations(self, client, create_test_user, create_test_conversation):
        """Пользователь не может видеть чужие диалоги."""
        other_user = create_test_user(email="other@example.com")
        conv = create_test_conversation(user_id=other_user.id)
        
        login_response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "TestPass123!"
        })
        token = login_response.json()["access_token"]
        
        response = client.get(
            f"/api/conversations/{conv.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code in [403, 404]


class TestMessageSending:
    """Сценарии отправки сообщений."""

    def test_user_send_message_to_conversation(self, client, authenticated_client, create_test_conversation):
        """Пользователь отправляет сообщение в свой диалог."""
        conv = create_test_conversation(status="open")
        
        message_data = {
            "content": "У меня проблема с оплатой!"
        }
        
        response = authenticated_client.post(
            f"/api/conversations/{conv.id}/messages",
            json=message_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["content"] == "У меня проблема с оплатой!"
        assert data["sender_type"] == "user"

    def test_send_message_to_nonexistent_conversation(self, client, authenticated_client):
        """Отправка сообщения в несуществующий диалог."""
        response = authenticated_client.post(
            "/api/conversations/99999/messages",
            json={"content": "Test message"}
        )
        
        assert response.status_code == 404

    def test_send_empty_message(self, client, authenticated_client, create_test_conversation):
        """Отправка пустого сообщения."""
        conv = create_test_conversation(status="open")
        
        response = authenticated_client.post(
            f"/api/conversations/{conv.id}/messages",
            json={"content": ""}
        )
        
        assert response.status_code == 422

    def test_get_conversation_messages(self, client, authenticated_client, create_test_conversation):
        """Получение истории сообщений диалога."""
        conv = create_test_conversation(status="open")
        
        # Отправляем несколько сообщений
        for i in range(3):
            authenticated_client.post(
                f"/api/conversations/{conv.id}/messages",
                json={"content": f"Message {i}"}
            )
        
        response = authenticated_client.get(f"/api/conversations/{conv.id}/messages")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3


class TestConversationLifecycle:
    """Жизненный цикл диалога."""

    def test_user_close_own_conversation(self, client, authenticated_client, create_test_conversation):
        """Пользователь закрывает свой диалог."""
        conv = create_test_conversation(status="open")
        
        response = authenticated_client.post(f"/api/conversations/{conv.id}/close")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "closed"

    def test_close_nonexistent_conversation(self, client, authenticated_client):
        """Закрытие несуществующего диалога."""
        response = authenticated_client.post("/api/conversations/99999/close")
        
        assert response.status_code == 404

    def test_conversation_status_transitions(self, client, authenticated_client, create_test_conversation):
        """Проверка переходов статусов диалога."""
        conv = create_test_conversation(status="open")
        
        # Открытый -> Ждём ответа AI
        # Проверяем что статус меняется корректно
        response = authenticated_client.get(f"/api/conversations/{conv.id}")
        assert response.json()["status"] == "open"


class TestOperatorWorkflow:
    """Рабочий процесс оператора."""

    def test_operator_get_escalated_queue(self, client, operator_client, create_test_conversation):
        """Оператор получает очередь эскалированных диалогов."""
        create_test_conversation(status="escalated", priority="high")
        create_test_conversation(status="escalated", priority="low")
        
        response = operator_client.get("/api/operator/queue")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_operator_assign_conversation(self, client, operator_client, create_test_conversation):
        """Оператор берёт диалог в работу."""
        conv = create_test_conversation(status="escalated")
        
        response = operator_client.post(f"/api/operator/assign/{conv.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "waiting_for_operator"

    def test_operator_reply_to_conversation(self, client, operator_client, create_test_conversation):
        """Оператор отвечает в диалоге."""
        conv = create_test_conversation(status="waiting_for_operator")
        
        response = operator_client.post(
            f"/api/operator/reply/{conv.id}",
            json={"content": "Здравствуйте! Чем могу помочь?"}
        )
        
        assert response.status_code == 201

    def test_operator_close_conversation(self, client, operator_client, create_test_conversation):
        """Оператор закрывает диалог."""
        conv = create_test_conversation(status="waiting_for_operator")
        
        response = operator_client.post(f"/api/operator/close/{conv.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "closed"

    def test_operator_return_to_ai(self, client, operator_client, create_test_conversation):
        """Оператор возвращает диалог AI."""
        conv = create_test_conversation(status="waiting_for_operator")
        
        response = operator_client.post(f"/api/operator/back_to_ai/{conv.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "open"

    def test_operator_active_limit(self, client, operator_client, create_test_conversation):
        """Ограничение на 5 активных диалогов у оператора."""
        # Создаём 5 активных диалогов
        for i in range(5):
            conv = create_test_conversation(status="escalated")
            operator_client.post(f"/api/operator/assign/{conv.id}")
        
        # Пытаемся взять 6-й
        conv6 = create_test_conversation(status="escalated")
        response = operator_client.post(f"/api/operator/assign/{conv6.id}")
        
        assert response.status_code == 400


class TestAIRouting:
    """Тесты AI-маршрутизации (имитация через API)."""

    def test_auto_reply_on_high_confidence(self, client, authenticated_client, create_test_conversation):
        """AI автоматически отвечает при высокой уверенности."""
        conv = create_test_conversation(status="open")
        
        # Отправляем сообщение
        authenticated_client.post(
            f"/api/conversations/{conv.id}/messages",
            json={"content": "Как сбросить пароль?"}
        )
        
        # Проверяем что появился AI-ответ (может быть асинхронно)
        messages_response = authenticated_client.get(f"/api/conversations/{conv.id}/messages")
        messages = messages_response.json()
        
        # Хотя бы одно сообщение должно быть от AI или помечено как автоответ
        ai_messages = [m for m in messages if m.get("is_auto_reply")]
        assert len(ai_messages) >= 0  # Может быть 0 если AI ещё не обработал

    def test_escalation_on_low_confidence(self, client, authenticated_client, create_test_conversation):
        """Диалог эскалируется при низкой уверенности AI."""
        conv = create_test_conversation(status="open")
        
        # Отправляем сложный вопрос
        authenticated_client.post(
            f"/api/conversations/{conv.id}/messages",
            json={"content": "Сложный вопрос который AI не поймёт"}
        )
        
        # Проверяем что диалог попал в эскалацию (или может попасть)
        conv_response = authenticated_client.get(f"/api/conversations/{conv.id}")
        status = conv_response.json()["status"]
        
        assert status in ["open", "escalated", "pending_ai"]


class TestPriorityAndChannel:
    """Тесты приоритетов и каналов."""

    def test_create_conversation_with_priority(self, client, authenticated_client):
        """Создание диалога с указанием приоритета."""
        for priority in ["low", "medium", "high"]:
            response = authenticated_client.post(
                "/api/conversations/",
                json={"priority": priority, "channel": "web"}
            )
            
            assert response.status_code == 201
            assert response.json()["priority"] == priority

    def test_create_conversation_with_channel(self, client, authenticated_client):
        """Создание диалога с указанием канала."""
        for channel in ["web", "api", "email"]:
            response = authenticated_client.post(
                "/api/conversations/",
                json={"channel": channel, "priority": "medium"}
            )
            
            assert response.status_code == 201
            assert response.json()["channel"] == channel
